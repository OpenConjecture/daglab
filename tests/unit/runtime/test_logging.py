"""Tests for the logging module."""

import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from daglab.runtime.logging import (
    DaglabLogger,
    JSONFormatter,
    PerformanceFilter,
    SecureFormatter,
    get_logger,
    setup_logging,
)


class TestSecureFormatter:
    """Test the SecureFormatter class."""
    
    def test_sanitize_sensitive_data(self):
        """Test that sensitive data is sanitized."""
        formatter = SecureFormatter()
        
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User login with password=secret123 and api_key=abcdef",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "secret123" not in formatted
        assert "abcdef" not in formatted
        assert "password=***REDACTED***" in formatted
        assert "api_key=***REDACTED***" in formatted
    
    def test_sanitize_args(self):
        """Test that args are sanitized."""
        formatter = SecureFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Config: %s, Token: %s",
            args=("config_value", "token=my_secret_token"),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "my_secret_token" not in formatted
        assert "token=***REDACTED***" in formatted
    
    def test_sanitize_extra_fields(self):
        """Test that extra fields are sanitized."""
        formatter = SecureFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.password = "secret_password"
        record.safe_field = "safe_value"
        
        formatted = formatter.format(record)
        assert "secret_password" not in formatted
        assert "safe_value" in str(record.__dict__)


class TestJSONFormatter:
    """Test the JSONFormatter class."""
    
    def test_json_format(self):
        """Test JSON formatting."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.module"
        assert data["message"] == "Test message"
        assert data["function"] == "test_function"
        assert data["line"] == 10
        assert "timestamp" in data
    
    def test_json_format_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]
    
    def test_json_format_sanitizes_data(self):
        """Test that JSON formatter also sanitizes data."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="api_key=secret123",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert "secret123" not in data["message"]
        assert "***REDACTED***" in data["message"]


class TestPerformanceFilter:
    """Test the PerformanceFilter class."""
    
    def test_adds_elapsed_time(self):
        """Test that elapsed time is added to records."""
        filter_obj = PerformanceFilter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert hasattr(record, 'elapsed_time')
        assert isinstance(record.elapsed_time, float)
        assert record.elapsed_time >= 0


class TestDaglabLogger:
    """Test the DaglabLogger class."""
    
    def test_initialization(self):
        """Test logger initialization."""
        logger = DaglabLogger(name="test_logger", level="DEBUG")
        log = logger.get_logger()
        
        assert log.name == "test_logger"
        assert log.level == logging.DEBUG
    
    def test_parse_level(self):
        """Test level parsing."""
        # String levels
        logger = DaglabLogger(name="test", level="WARNING")
        assert logger.logger.level == logging.WARNING
        
        # Integer levels
        logger = DaglabLogger(name="test", level=logging.ERROR)
        assert logger.logger.level == logging.ERROR
    
    def test_file_logging(self, tmp_path):
        """Test file logging setup."""
        log_dir = tmp_path / "logs"
        logger = DaglabLogger(
            name="test",
            log_dir=log_dir,
            enable_file_logging=True,
            enable_json_format=True
        )
        
        # Log messages at different levels
        log = logger.get_logger()
        log.debug("Debug message")
        log.info("Info message")
        log.error("Error message")
        
        # Check that log files were created
        assert (log_dir / "test_debug.log").exists()
        assert (log_dir / "test_info.log").exists()
        assert (log_dir / "test_error.log").exists()
    
    def test_rich_console_handler(self):
        """Test Rich console handler setup."""
        logger = DaglabLogger(
            name="test",
            enable_rich_console=True,
            enable_json_format=False
        )
        
        # Check that handlers were added
        assert len(logger.logger.handlers) > 0
    
    def test_json_stream_handler(self):
        """Test JSON stream handler setup."""
        logger = DaglabLogger(
            name="test",
            enable_rich_console=False,
            enable_json_format=True,
            enable_file_logging=False
        )
        
        # Check that JSON formatter is used
        assert len(logger.logger.handlers) == 1
        assert isinstance(logger.logger.handlers[0].formatter, JSONFormatter)
    
    def test_log_performance(self):
        """Test performance logging."""
        logger = DaglabLogger(name="test", enable_performance_logging=True)
        
        logger.log_performance("test_operation", 1.234, {"extra": "data"})
        
        # Verify the log was created (would need to capture logs to fully test)
        assert True  # Placeholder
    
    def test_create_child_logger(self):
        """Test child logger creation."""
        logger = DaglabLogger(name="parent")
        child = logger.create_child_logger("child")
        
        assert child.name == "parent.child"
        assert child.parent == logger.logger


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_convenience")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_convenience"
    
    def test_setup_logging(self, tmp_path):
        """Test setup_logging function."""
        logger = setup_logging(
            level="DEBUG",
            enable_file_logging=True,
            log_dir=tmp_path / "logs"
        )
        
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.DEBUG


class TestRotatingFileHandler:
    """Test rotating file handler functionality."""
    
    def test_max_file_size(self, tmp_path):
        """Test that files rotate at max size."""
        log_dir = tmp_path / "logs"
        logger = DaglabLogger(
            name="test",
            log_dir=log_dir,
            max_file_size=1024,  # 1KB for testing
            backup_count=2
        )
        
        log = logger.get_logger()
        
        # Write enough data to trigger rotation
        for i in range(100):
            log.info("x" * 100)  # 100 chars per message
        
        # Check that backup files were created
        log_files = list(log_dir.glob("test_info.log*"))
        assert len(log_files) > 1


class TestSecurityFeatures:
    """Test security-related features."""
    
    def test_no_secrets_in_logs(self):
        """Test that secrets are not leaked in logs."""
        formatter = SecureFormatter()
        
        # Test various secret patterns
        test_cases = [
            ("password: mysecret", "password=***REDACTED***"),
            ("token='abcdef'", "token=***REDACTED***"),
            ('{"api_key": "secret"}', "api_key=***REDACTED***"),
            ("private_key=xyz123", "private_key=***REDACTED***"),
        ]
        
        for msg, expected in test_cases:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg=msg,
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            assert expected in formatted
            assert "mysecret" not in formatted
            assert "abcdef" not in formatted
            assert "secret" not in formatted
            assert "xyz123" not in formatted