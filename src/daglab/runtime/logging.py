"""Structured logging system for daglab.

Provides JSON-formatted logging with rotation, security-conscious filtering,
and integration with the daglab runtime.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from daglab.config import settings


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs."""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'api_key', 'private_key',
        'credentials', 'authorization', 'auth', 'key', 'pwd'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize sensitive data from log records."""
        if hasattr(record, 'args') and isinstance(record.args, dict):
            record.args = self._sanitize_dict(record.args.copy())
        
        # Sanitize the message itself
        if any(key in record.getMessage().lower() for key in self.SENSITIVE_KEYS):
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    record.msg = record.msg.replace(
                        record.msg[record.msg.lower().index(key):],
                        f"{key}=<REDACTED>"
                    )
        
        return True
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        for key in list(data.keys()):
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                data[key] = "<REDACTED>"
            elif isinstance(data[key], dict):
                data[key] = self._sanitize_dict(data[key])
            elif isinstance(data[key], list):
                data[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in data[key]
                ]
        return data


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process': os.getpid(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add custom fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread',
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class DaglabLogger:
    """Main logger class for daglab."""
    
    _instance: Optional['DaglabLogger'] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls) -> 'DaglabLogger':
        """Singleton pattern for logger."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the logging system."""
        self.log_dir = Path(settings.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root = logging.getLogger()
        root.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Remove existing handlers
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        # Add security filter to root logger
        security_filter = SecurityFilter()
        root.addFilter(security_filter)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name in self._loggers:
            return self._loggers[name]
        
        logger = logging.getLogger(name)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if settings.log_format == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        logger.addHandler(console_handler)
        
        # File handler with rotation
        if settings.log_to_file:
            file_path = self.log_dir / f"{name.replace('.', '_')}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count
            )
            if settings.log_format == 'json':
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                )
            logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
        
        self._loggers[name] = logger
        return logger
    
    def log_event(
        self,
        logger_name: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        level: str = 'INFO'
    ) -> None:
        """Log a structured event."""
        logger = self.get_logger(logger_name)
        log_method = getattr(logger, level.lower())
        
        extra = {'event_type': event_type}
        if data:
            extra.update(data)
        
        log_method(f"Event: {event_type}", extra=extra)
    
    def log_metric(
        self,
        logger_name: str,
        metric_name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Log a metric value."""
        logger = self.get_logger(logger_name)
        
        extra = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_type': 'gauge'
        }
        
        if unit:
            extra['metric_unit'] = unit
        
        if tags:
            extra['metric_tags'] = tags
        
        logger.info(f"Metric: {metric_name}={value}", extra=extra)
    
    def log_duration(
        self,
        logger_name: str,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log operation duration."""
        logger = self.get_logger(logger_name)
        
        extra = {
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success
        }
        
        if metadata:
            extra.update(metadata)
        
        level = 'info' if success else 'warning'
        log_method = getattr(logger, level)
        log_method(
            f"Operation '{operation}' completed in {duration_ms}ms",
            extra=extra
        )


# Module-level convenience functions
_logger_instance = DaglabLogger()

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return _logger_instance.get_logger(name)

def log_event(logger_name: str, event_type: str, data: Optional[Dict[str, Any]] = None, level: str = 'INFO'):
    """Log a structured event."""
    _logger_instance.log_event(logger_name, event_type, data, level)

def log_metric(logger_name: str, metric_name: str, value: Union[int, float], unit: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Log a metric value."""
    _logger_instance.log_metric(logger_name, metric_name, value, unit, tags)

def log_duration(logger_name: str, operation: str, duration_ms: float, success: bool = True, metadata: Optional[Dict[str, Any]] = None):
    """Log operation duration."""
    _logger_instance.log_duration(logger_name, operation, duration_ms, success, metadata)