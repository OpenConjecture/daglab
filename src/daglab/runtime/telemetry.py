"""Basic telemetry client stub for performance metrics and usage tracking."""

import json
import os
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from daglab.runtime.logging import get_logger


@dataclass
class Metric:
    """Represents a single metric measurement."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """Represents a telemetry event."""
    name: str
    timestamp: float = field(default_factory=time.time)
    properties: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class TelemetryClient:
    """Basic telemetry client for metrics collection and usage tracking."""
    
    def __init__(
        self,
        enabled: bool = True,
        opt_in: bool = False,
        service_name: str = "daglab",
        buffer_size: int = 1000,
        flush_interval: float = 60.0,
        storage_path: Optional[Path] = None
    ):
        self.enabled = enabled and opt_in
        self.service_name = service_name
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.storage_path = storage_path or Path.home() / ".daglab" / "telemetry"
        
        self.logger = get_logger(f"{service_name}.telemetry")
        self.session_id = str(uuid4())
        self.start_time = time.time()
        
        # Buffers for metrics and events
        self._metrics_buffer: List[Metric] = []
        self._events_buffer: List[Event] = []
        self._timers: Dict[str, float] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Create storage directory if enabled
        if self.enabled and self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
        self.logger.info(
            f"Telemetry client initialized (enabled={self.enabled}, opt_in={opt_in})"
        )
    
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.enabled
    
    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a single metric."""
        if not self.enabled:
            return
        
        metric = Metric(
            name=name,
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self._metrics_buffer.append(metric)
        
        # Flush if buffer is full
        if len(self._metrics_buffer) >= self.buffer_size:
            self.flush_metrics()
    
    def record_event(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Record a telemetry event."""
        if not self.enabled:
            return
        
        event = Event(
            name=name,
            properties=properties or {},
            user_id=user_id,
            session_id=self.session_id
        )
        
        self._events_buffer.append(event)
        
        # Flush if buffer is full
        if len(self._events_buffer) >= self.buffer_size:
            self.flush_events()
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        if not self.enabled:
            return
        
        self._counters[name] += value
        self.record_metric(f"counter.{name}", self._counters[name])
    
    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        
        try:
            yield
        finally:
            if self.enabled:
                duration = time.time() - start_time
                self.record_metric(
                    f"timer.{name}",
                    duration,
                    tags=tags,
                    metadata={"unit": "seconds"}
                )
    
    def start_timer(self, name: str) -> None:
        """Start a named timer."""
        if self.enabled:
            self._timers[name] = time.time()
    
    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a named timer and record the duration."""
        if not self.enabled or name not in self._timers:
            return None
        
        duration = time.time() - self._timers.pop(name)
        self.record_metric(
            f"timer.{name}",
            duration,
            metadata={"unit": "seconds"}
        )
        return duration
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric (point-in-time value)."""
        if self.enabled:
            self.record_metric(f"gauge.{name}", value, tags=tags)
    
    def histogram(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram metric."""
        if not self.enabled:
            return
        
        metadata = {}
        if buckets:
            # Calculate which bucket the value falls into
            bucket_index = len([b for b in buckets if value > b])
            metadata["bucket"] = bucket_index
            metadata["buckets"] = buckets
        
        self.record_metric(f"histogram.{name}", value, tags=tags, metadata=metadata)
    
    def flush_metrics(self) -> None:
        """Flush metrics buffer to storage."""
        if not self.enabled or not self._metrics_buffer:
            return
        
        try:
            # Write metrics to file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            metrics_file = self.storage_path / f"metrics_{timestamp}.json"
            
            with open(metrics_file, 'w') as f:
                json.dump(
                    [self._serialize_metric(m) for m in self._metrics_buffer],
                    f,
                    indent=2
                )
            
            self.logger.debug(f"Flushed {len(self._metrics_buffer)} metrics to {metrics_file}")
            self._metrics_buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to flush metrics: {e}")
    
    def flush_events(self) -> None:
        """Flush events buffer to storage."""
        if not self.enabled or not self._events_buffer:
            return
        
        try:
            # Write events to file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            events_file = self.storage_path / f"events_{timestamp}.json"
            
            with open(events_file, 'w') as f:
                json.dump(
                    [self._serialize_event(e) for e in self._events_buffer],
                    f,
                    indent=2
                )
            
            self.logger.debug(f"Flushed {len(self._events_buffer)} events to {events_file}")
            self._events_buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to flush events: {e}")
    
    def flush_all(self) -> None:
        """Flush all buffers."""
        self.flush_metrics()
        self.flush_events()
    
    def _serialize_metric(self, metric: Metric) -> Dict[str, Any]:
        """Serialize a metric for storage."""
        return {
            "name": metric.name,
            "value": metric.value,
            "timestamp": metric.timestamp,
            "tags": metric.tags,
            "metadata": metric.metadata,
            "service": self.service_name,
            "session_id": self.session_id
        }
    
    def _serialize_event(self, event: Event) -> Dict[str, Any]:
        """Serialize an event for storage."""
        return {
            "name": event.name,
            "timestamp": event.timestamp,
            "properties": event.properties,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "service": self.service_name
        }
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current session."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time,
            "metrics_count": len(self._metrics_buffer),
            "events_count": len(self._events_buffer),
            "counters": dict(self._counters),
            "active_timers": list(self._timers.keys())
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush all data."""
        self.flush_all()


class PerformanceTracker:
    """High-level performance tracking utilities."""
    
    def __init__(self, telemetry_client: Optional[TelemetryClient] = None):
        self.client = telemetry_client or TelemetryClient(enabled=False)
    
    @contextmanager
    def track_operation(
        self,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track a complete operation with timing and status."""
        start_time = time.time()
        success = False
        error = None
        
        try:
            self.client.record_event(f"{operation}.start", properties=metadata)
            yield
            success = True
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration = time.time() - start_time
            
            # Record completion event
            self.client.record_event(
                f"{operation}.complete",
                properties={
                    "duration": duration,
                    "success": success,
                    "error": error,
                    **(metadata or {})
                }
            )
            
            # Record timing metric
            self.client.record_metric(
                f"operation.{operation}.duration",
                duration,
                tags={"success": str(success).lower()}
            )
    
    def track_resource_usage(self) -> Dict[str, float]:
        """Track current resource usage."""
        try:
            import psutil
            
            process = psutil.Process()
            
            usage = {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
                "memory_vms_mb": process.memory_info().vms / 1024 / 1024,
                "num_threads": process.num_threads(),
            }
            
            # Record as gauges
            for metric, value in usage.items():
                self.client.gauge(f"resource.{metric}", value)
            
            return usage
            
        except ImportError:
            self.client.logger.debug("psutil not available for resource tracking")
            return {}


# Global telemetry client instance
_global_telemetry_client: Optional[TelemetryClient] = None


def get_telemetry_client() -> TelemetryClient:
    """Get the global telemetry client instance."""
    global _global_telemetry_client
    
    if _global_telemetry_client is None:
        # Check environment for opt-in
        opt_in = os.environ.get("DAGLAB_TELEMETRY_OPT_IN", "false").lower() == "true"
        _global_telemetry_client = TelemetryClient(opt_in=opt_in)
    
    return _global_telemetry_client


def setup_telemetry(
    enabled: bool = True,
    opt_in: bool = False,
    **kwargs
) -> TelemetryClient:
    """Setup and configure the global telemetry client."""
    global _global_telemetry_client
    
    _global_telemetry_client = TelemetryClient(
        enabled=enabled,
        opt_in=opt_in,
        **kwargs
    )
    
    return _global_telemetry_client