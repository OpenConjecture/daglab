"""Basic telemetry client for daglab runtime monitoring.

Provides lightweight telemetry collection for performance monitoring,
usage tracking, and error reporting.
"""

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from collections import defaultdict
import threading

from daglab.runtime.logging import get_logger
from daglab.config import settings


class TelemetryLevel(Enum):
    """Telemetry collection levels."""
    DISABLED = "disabled"
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"


class MetricType(Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TelemetryEvent:
    """Represents a telemetry event."""
    event_id: str
    event_type: str
    timestamp: float
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


@dataclass
class Metric:
    """Represents a metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float
    tags: Optional[Dict[str, str]] = None
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


class TelemetryClient:
    """Lightweight telemetry client for daglab."""
    
    def __init__(self):
        """Initialize the telemetry client."""
        self.logger = get_logger('daglab.telemetry')
        self.enabled = self._check_enabled()
        self.level = self._get_telemetry_level()
        self.session_id = str(uuid.uuid4())
        self.start_time = time.time()
        
        # In-memory storage for metrics
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._events: List[TelemetryEvent] = []
        self._lock = threading.Lock()
        
        # Initialize storage
        if self.enabled:
            self._init_storage()
        
        self.logger.info(
            f"Telemetry initialized",
            extra={
                'session_id': self.session_id,
                'enabled': self.enabled,
                'level': self.level.value
            }
        )
    
    def _check_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        # Check environment variable
        env_disabled = os.environ.get('DAGLAB_TELEMETRY_DISABLED', '').lower() == 'true'
        if env_disabled:
            return False
        
        # Check settings
        return getattr(settings, 'telemetry_enabled', True)
    
    def _get_telemetry_level(self) -> TelemetryLevel:
        """Get the telemetry level from configuration."""
        level_str = getattr(settings, 'telemetry_level', 'standard').lower()
        try:
            return TelemetryLevel(level_str)
        except ValueError:
            self.logger.warning(f"Invalid telemetry level: {level_str}, using standard")
            return TelemetryLevel.STANDARD
    
    def _init_storage(self) -> None:
        """Initialize telemetry storage."""
        telemetry_dir = Path(settings.data_dir) / 'telemetry'
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_file = telemetry_dir / f"session_{self.session_id}.jsonl"
    
    def _should_collect(self, level: TelemetryLevel) -> bool:
        """Check if data should be collected based on current level."""
        if not self.enabled:
            return False
        
        level_order = {
            TelemetryLevel.DISABLED: 0,
            TelemetryLevel.MINIMAL: 1,
            TelemetryLevel.STANDARD: 2,
            TelemetryLevel.DETAILED: 3
        }
        
        return level_order[self.level] >= level_order[level]
    
    def track_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        level: TelemetryLevel = TelemetryLevel.STANDARD
    ) -> str:
        """Track a telemetry event."""
        if not self._should_collect(level):
            return ""
        
        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=time.time(),
            metadata=metadata
        )
        
        with self._lock:
            self._events.append(event)
        
        # Log if detailed
        if self.level == TelemetryLevel.DETAILED:
            self.logger.debug(f"Telemetry event: {event_type}", extra=event.to_dict())
        
        # Write to file if enabled
        if hasattr(self, 'telemetry_file'):
            self._write_event(event)
        
        return event.event_id
    
    @contextmanager
    def track_operation(
        self,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        level: TelemetryLevel = TelemetryLevel.STANDARD
    ):
        """Context manager to track operation duration."""
        if not self._should_collect(level):
            yield
            return
        
        start_time = time.time()
        event_id = self.track_event(f"{operation_name}_started", metadata, level)
        
        try:
            yield
            # Success
            duration_ms = (time.time() - start_time) * 1000
            self.track_event(
                f"{operation_name}_completed",
                {
                    **(metadata or {}),
                    'duration_ms': duration_ms,
                    'success': True,
                    'start_event_id': event_id
                },
                level
            )
            self.record_metric(
                f"{operation_name}_duration",
                duration_ms,
                MetricType.TIMER,
                unit='ms'
            )
        except Exception as e:
            # Failure
            duration_ms = (time.time() - start_time) * 1000
            self.track_event(
                f"{operation_name}_failed",
                {
                    **(metadata or {}),
                    'duration_ms': duration_ms,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'start_event_id': event_id
                },
                level
            )
            self.record_metric(
                f"{operation_name}_failures",
                1,
                MetricType.COUNTER
            )
            raise
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None,
        level: TelemetryLevel = TelemetryLevel.STANDARD
    ) -> None:
        """Record a metric value."""
        if not self._should_collect(level):
            return
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=time.time(),
            tags=tags,
            unit=unit
        )
        
        with self._lock:
            self._metrics[name].append(value)
        
        # Log metric via logging system
        self.logger.info(
            f"Metric: {name}",
            extra=metric.to_dict()
        )
    
    def increment_counter(
        self,
        name: str,
        value: float = 1,
        tags: Optional[Dict[str, str]] = None,
        level: TelemetryLevel = TelemetryLevel.STANDARD
    ) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, tags, level=level)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None,
        level: TelemetryLevel = TelemetryLevel.STANDARD
    ) -> None:
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, tags, unit, level)
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None,
        level: TelemetryLevel = TelemetryLevel.DETAILED
    ) -> None:
        """Record a histogram metric."""
        self.record_metric(name, value, MetricType.HISTOGRAM, tags, unit, level)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        with self._lock:
            summary = {}
            for name, values in self._metrics.items():
                if values:
                    summary[name] = {
                        'count': len(values),
                        'sum': sum(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }
            return summary
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        uptime_seconds = time.time() - self.start_time
        return {
            'session_id': self.session_id,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'uptime_seconds': uptime_seconds,
            'uptime_human': self._format_duration(uptime_seconds),
            'telemetry_enabled': self.enabled,
            'telemetry_level': self.level.value,
            'events_tracked': len(self._events),
            'metrics_tracked': len(self._metrics)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _write_event(self, event: TelemetryEvent) -> None:
        """Write event to telemetry file."""
        try:
            with open(self.telemetry_file, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write telemetry event: {e}")
    
    def flush(self) -> None:
        """Flush any pending telemetry data."""
        if not self.enabled:
            return
        
        # Log session summary
        self.logger.info(
            "Telemetry session summary",
            extra=self.get_session_info()
        )
        
        # Log metrics summary if detailed
        if self.level == TelemetryLevel.DETAILED:
            self.logger.info(
                "Metrics summary",
                extra={'metrics': self.get_metrics_summary()}
            )
    
    def shutdown(self) -> None:
        """Shutdown telemetry client and flush data."""
        self.track_event('session_ended', {'session_duration': time.time() - self.start_time})
        self.flush()
        self.logger.info("Telemetry client shutdown")


# Global telemetry client instance
_telemetry_client: Optional[TelemetryClient] = None


def get_telemetry_client() -> TelemetryClient:
    """Get the global telemetry client instance."""
    global _telemetry_client
    if _telemetry_client is None:
        _telemetry_client = TelemetryClient()
    return _telemetry_client


# Convenience functions
def track_event(event_type: str, metadata: Optional[Dict[str, Any]] = None, level: TelemetryLevel = TelemetryLevel.STANDARD) -> str:
    """Track a telemetry event."""
    return get_telemetry_client().track_event(event_type, metadata, level)


def track_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None, level: TelemetryLevel = TelemetryLevel.STANDARD):
    """Context manager to track operation duration."""
    return get_telemetry_client().track_operation(operation_name, metadata, level)


def record_metric(name: str, value: float, metric_type: MetricType = MetricType.GAUGE, tags: Optional[Dict[str, str]] = None, unit: Optional[str] = None, level: TelemetryLevel = TelemetryLevel.STANDARD):
    """Record a metric value."""
    get_telemetry_client().record_metric(name, value, metric_type, tags, unit, level)


def increment_counter(name: str, value: float = 1, tags: Optional[Dict[str, str]] = None):
    """Increment a counter metric."""
    get_telemetry_client().increment_counter(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None, unit: Optional[str] = None):
    """Set a gauge metric."""
    get_telemetry_client().set_gauge(name, value, tags, unit)