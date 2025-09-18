"""Structured logging with JSON format option and security features."""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


class SecureFormatter(logging.Formatter):
    """Security-conscious log formatter that removes sensitive information."""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'secret', 'key', 'auth', 'credential',
        'private', 'api_key', 'access_token', 'refresh_token'
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        # Create a copy of the record to avoid modifying the original
        record = logging.makeLogRecord(record.__dict__)
        
        # Sanitize message
        if hasattr(record, 'msg'):
            record.msg = self._sanitize_string(str(record.msg))
        
        # Sanitize args
        if hasattr(record, 'args') and record.args:
            record.args = tuple(self._sanitize_value(arg) for arg in record.args)
        
        # Sanitize extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'stack_info', 'thread', 'threadName']:
                record.__dict__[key] = self._sanitize_value(value)
        
        return super().format(record)
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize sensitive information from strings."""
        lower_text = text.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in lower_text:
                # Find and replace sensitive data patterns
                import re
                # Match common patterns like key=value, "key": "value", etc.
                patterns = [
                    rf'{pattern}["\']?\s*[:=]\s*["\']?([^"\'\s,}}]+)',
                    rf'{pattern}_?[a-z]*["\']?\s*[:=]\s*["\']?([^"\'\s,}}]+)'
                ]
                for p in patterns:
                    text = re.sub(p, f'{pattern}=***REDACTED***', text, flags=re.IGNORECASE)
        return text
    
    def _sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize values."""
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(self._sanitize_value(item) for item in value)
        return value


class JSONFormatter(SecureFormatter):
    """JSON log formatter with security features."""
    
    def format(self, record: logging.LogRecord) -> str:
        # First apply security sanitization
        super().format(record)
        
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'process': record.processName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'stack_info', 'thread', 'threadName', 'exc_info', 'exc_text']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class PerformanceFilter(logging.Filter):
    """Add performance metrics to log records."""
    
    def __init__(self):
        super().__init__()
        self._start_time = datetime.utcnow()
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add performance metrics
        record.elapsed_time = (datetime.utcnow() - self._start_time).total_seconds()
        return True


class DaglabLogger:
    """Main logger configuration for Daglab."""
    
    def __init__(
        self,
        name: str = "daglab",
        level: Union[str, int] = "INFO",
        log_dir: Optional[Path] = None,
        enable_file_logging: bool = True,
        enable_json_format: bool = False,
        enable_rich_console: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_performance_logging: bool = False
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self._parse_level(level))
        self.logger.handlers.clear()
        
        # Add performance filter if enabled
        if enable_performance_logging:
            self.logger.addFilter(PerformanceFilter())
        
        # Configure handlers
        if enable_rich_console and not enable_json_format:
            self._setup_rich_console()
        else:
            self._setup_stream_handler(enable_json_format)
        
        if enable_file_logging:
            self._setup_file_handler(
                log_dir or Path.home() / ".daglab" / "logs",
                enable_json_format,
                max_file_size,
                backup_count
            )
    
    def _parse_level(self, level: Union[str, int]) -> int:
        """Parse log level from string or int."""
        if isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        return level
    
    def _setup_rich_console(self):
        """Setup Rich console handler for pretty output."""
        console = Console(stderr=True)
        handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=True
        )
        handler.setFormatter(SecureFormatter())
        self.logger.addHandler(handler)
    
    def _setup_stream_handler(self, use_json: bool = False):
        """Setup stream handler with optional JSON formatting."""
        handler = logging.StreamHandler(sys.stderr)
        if use_json:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(SecureFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        self.logger.addHandler(handler)
    
    def _setup_file_handler(
        self,
        log_dir: Path,
        use_json: bool,
        max_file_size: int,
        backup_count: int
    ):
        """Setup rotating file handler."""
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create separate files for different log levels
        levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'error': logging.ERROR
        }
        
        for level_name, level in levels.items():
            file_path = log_dir / f"{self.name}_{level_name}.log"
            handler = RotatingFileHandler(
                file_path,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            handler.setLevel(level)
            
            if use_json:
                handler.setFormatter(JSONFormatter())
            else:
                handler.setFormatter(SecureFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            
            self.logger.addHandler(handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger
    
    def log_performance(self, operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics."""
        self.logger.info(
            f"Performance: {operation}",
            extra={
                'operation': operation,
                'duration_ms': duration * 1000,
                'performance_metric': True,
                **(metadata or {})
            }
        )
    
    def create_child_logger(self, name: str) -> logging.Logger:
        """Create a child logger with the same configuration."""
        return logging.getLogger(f"{self.name}.{name}")


# Convenience functions
def get_logger(name: str = "daglab", **kwargs) -> logging.Logger:
    """Get or create a logger with the specified configuration."""
    daglab_logger = DaglabLogger(name=name, **kwargs)
    return daglab_logger.get_logger()


def setup_logging(
    level: Union[str, int] = "INFO",
    enable_file_logging: bool = True,
    enable_json_format: bool = False,
    log_dir: Optional[Path] = None
) -> logging.Logger:
    """Setup default logging configuration for Daglab."""
    return get_logger(
        level=level,
        enable_file_logging=enable_file_logging,
        enable_json_format=enable_json_format,
        log_dir=log_dir
    )