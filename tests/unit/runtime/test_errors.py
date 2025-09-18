"""Tests for the errors module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from daglab.runtime.errors import (
    AuthenticationError,
    AuthorizationError,
    ComputeError,
    ConfigurationError,
    DaglabError,
    DependencyError,
    ErrorContext,
    ErrorHandler,
    ExitCode,
    IntegrationError,
    NetworkError,
    ResourceError,
    RuntimeError as DaglabRuntimeError,
    SchedulingError,
    SecurityError,
    StorageError,
    TimeoutError,
    ValidationError,
    graceful_degradation,
)


class TestExitCode:
    """Test ExitCode enum."""
    
    def test_standard_codes(self):
        """Test standard exit codes."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.MISUSE == 2
        assert ExitCode.CANNOT_EXECUTE == 126
        assert ExitCode.COMMAND_NOT_FOUND == 127
    
    def test_custom_codes(self):
        """Test custom Daglab exit codes."""
        assert ExitCode.CONFIGURATION_ERROR == 130
        assert ExitCode.VALIDATION_ERROR == 131
        assert ExitCode.SECURITY_ERROR == 132
        assert all(code >= 128 for code in ExitCode if code >= 128)


class TestErrorContext:
    """Test ErrorContext class."""
    
    def test_initialization(self):
        """Test context initialization."""
        context = ErrorContext(
            operation="test_op",
            resource="test_resource",
            details={"key": "value"},
            suggestions=["Try this", "Or that"]
        )
        
        assert context.operation == "test_op"
        assert context.resource == "test_resource"
        assert context.details == {"key": "value"}
        assert context.suggestions == ["Try this", "Or that"]
    
    def test_defaults(self):
        """Test default values."""
        context = ErrorContext()
        
        assert context.operation is None
        assert context.resource is None
        assert context.details == {}
        assert context.suggestions == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        context = ErrorContext(
            operation="test",
            resource="resource",
            details={"a": 1},
            suggestions=["fix"]
        )
        
        data = context.to_dict()
        assert data == {
            'operation': 'test',
            'resource': 'resource',
            'details': {'a': 1},
            'suggestions': ['fix']
        }


class TestDaglabError:
    """Test base DaglabError class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = DaglabError("Test error")
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.exit_code == ExitCode.GENERAL_ERROR
    
    def test_error_with_context(self):
        """Test error with context."""
        context = ErrorContext(
            operation="test_op",
            resource="test_res",
            details={"info": "data"}
        )
        error = DaglabError("Error message", context=context)
        
        error_str = str(error)
        assert "Error message" in error_str
        assert "Operation: test_op" in error_str
        assert "Resource: test_res" in error_str
        assert "Details: {'info': 'data'}" in error_str
    
    def test_error_with_cause(self):
        """Test error with cause."""
        cause = ValueError("Original error")
        error = DaglabError("Wrapped error", cause=cause)
        
        error_str = str(error)
        assert "Wrapped error" in error_str
        assert "Caused by: ValueError: Original error" in error_str
    
    def test_error_with_suggestions(self):
        """Test error with suggestions."""
        context = ErrorContext(suggestions=["Fix this", "Try that"])
        error = DaglabError("Error", context=context)
        
        error_str = str(error)
        assert "Suggestions:" in error_str
        assert "  - Fix this" in error_str
        assert "  - Try that" in error_str
    
    def test_with_suggestions_classmethod(self):
        """Test with_suggestions class method."""
        error = DaglabError.with_suggestions(
            "Test error",
            "First suggestion",
            "Second suggestion"
        )
        
        error_str = str(error)
        assert "First suggestion" in error_str
        assert "Second suggestion" in error_str
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        context = ErrorContext(operation="test")
        error = DaglabError("Test", context=context)
        
        data = error.to_dict()
        assert data['error_type'] == 'DaglabError'
        assert data['message'] == 'Test'
        assert data['exit_code'] == ExitCode.GENERAL_ERROR.value
        assert data['context']['operation'] == 'test'
        assert data['cause'] is None
    
    def test_default_message(self):
        """Test default message is used when none provided."""
        error = DaglabError()
        assert error.message == "An error occurred in Daglab"


class TestSpecificErrors:
    """Test specific error types."""
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config failed")
        assert error.exit_code == ExitCode.CONFIGURATION_ERROR
        assert isinstance(error, DaglabError)
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input")
        assert error.exit_code == ExitCode.VALIDATION_ERROR
    
    def test_security_error(self):
        """Test SecurityError."""
        error = SecurityError("Security breach")
        assert error.exit_code == ExitCode.SECURITY_ERROR
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection failed")
        assert error.exit_code == ExitCode.NETWORK_ERROR
    
    def test_storage_error(self):
        """Test StorageError."""
        error = StorageError("Storage full")
        assert error.exit_code == ExitCode.STORAGE_ERROR
    
    def test_compute_error(self):
        """Test ComputeError."""
        error = ComputeError("Compute failed")
        assert error.exit_code == ExitCode.COMPUTE_ERROR
    
    def test_scheduling_error(self):
        """Test SchedulingError."""
        error = SchedulingError("Schedule conflict")
        assert error.exit_code == ExitCode.SCHEDULING_ERROR
    
    def test_runtime_error(self):
        """Test RuntimeError."""
        error = DaglabRuntimeError("Runtime issue")
        assert error.exit_code == ExitCode.RUNTIME_ERROR
    
    def test_dependency_error(self):
        """Test DependencyError."""
        error = DependencyError("Missing dependency")
        assert error.exit_code == ExitCode.DEPENDENCY_ERROR
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed")
        assert error.exit_code == ExitCode.AUTHENTICATION_ERROR
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        error = AuthorizationError("Not authorized")
        assert error.exit_code == ExitCode.AUTHORIZATION_ERROR
    
    def test_resource_error(self):
        """Test ResourceError."""
        error = ResourceError("Resource exhausted")
        assert error.exit_code == ExitCode.RESOURCE_ERROR
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Operation timeout")
        assert error.exit_code == ExitCode.TIMEOUT_ERROR
    
    def test_integration_error(self):
        """Test IntegrationError."""
        error = IntegrationError("API failed")
        assert error.exit_code == ExitCode.INTEGRATION_ERROR


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    @patch('sys.exit')
    @patch('logging.getLogger')
    def test_handle_daglab_error(self, mock_logger, mock_exit):
        """Test handling DaglabError."""
        logger = MagicMock()
        mock_logger.return_value = logger
        
        error = ValidationError("Test validation error")
        ErrorHandler.handle_error(error, exit_on_error=True)
        
        # Check logging
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "ValidationError: Test validation error" in call_args[0][0]
        
        # Check exit
        mock_exit.assert_called_once_with(ExitCode.VALIDATION_ERROR)
    
    @patch('sys.exit')
    @patch('logging.getLogger')
    def test_handle_standard_error(self, mock_logger, mock_exit):
        """Test handling standard Python error."""
        logger = MagicMock()
        mock_logger.return_value = logger
        
        error = ValueError("Standard error")
        ErrorHandler.handle_error(error, exit_on_error=True)
        
        # Check logging
        logger.error.assert_called_once()
        assert "Unexpected error: ValueError: Standard error" in logger.error.call_args[0][0]
        
        # Check exit
        mock_exit.assert_called_once_with(ExitCode.GENERAL_ERROR)
    
    @patch('logging.getLogger')
    def test_handle_error_no_exit(self, mock_logger):
        """Test handling error without exiting."""
        logger = MagicMock()
        mock_logger.return_value = logger
        
        error = NetworkError("Network issue")
        exit_code = ErrorHandler.handle_error(error, exit_on_error=False)
        
        assert exit_code == ExitCode.NETWORK_ERROR
        logger.error.assert_called_once()
    
    @patch('sys.exit')
    def test_handle_error_no_logging(self, mock_exit):
        """Test handling error without logging."""
        error = SecurityError("Security issue")
        ErrorHandler.handle_error(error, exit_on_error=True, log_error=False)
        
        mock_exit.assert_called_once_with(ExitCode.SECURITY_ERROR)
    
    def test_wrap_error(self):
        """Test wrapping standard exceptions."""
        # Wrap a standard exception
        original = ValueError("Original error")
        wrapped = ErrorHandler.wrap_error(
            original,
            error_class=ComputeError,
            message="Computation failed",
            context=ErrorContext(operation="compute")
        )
        
        assert isinstance(wrapped, ComputeError)
        assert wrapped.message == "Computation failed"
        assert wrapped.cause == original
        assert wrapped.context.operation == "compute"
    
    def test_wrap_daglab_error(self):
        """Test that DaglabError is not re-wrapped."""
        original = NetworkError("Network error")
        wrapped = ErrorHandler.wrap_error(original)
        
        assert wrapped is original
    
    def test_wrap_error_default_message(self):
        """Test wrap_error with default message."""
        original = RuntimeError("Runtime issue")
        wrapped = ErrorHandler.wrap_error(original)
        
        assert wrapped.message == "RuntimeError: Runtime issue"


class TestGracefulDegradation:
    """Test graceful_degradation decorator."""
    
    def test_successful_execution(self):
        """Test that decorator doesn't interfere with success."""
        @graceful_degradation
        def successful_func(x):
            return x * 2
        
        result = successful_func(5)
        assert result == 10
    
    def test_fallback_value(self):
        """Test fallback to static value."""
        @graceful_degradation(fallback=42)
        def failing_func():
            raise ValueError("Fail")
        
        result = failing_func()
        assert result == 42
    
    def test_fallback_function(self):
        """Test fallback to function."""
        def fallback_handler(*args, **kwargs):
            return "fallback_result"
        
        @graceful_degradation(fallback=fallback_handler)
        def failing_func():
            raise RuntimeError("Fail")
        
        result = failing_func()
        assert result == "fallback_result"
    
    @patch('logging.getLogger')
    def test_logging(self, mock_logger):
        """Test that failures are logged."""
        logger = MagicMock()
        mock_logger.return_value = logger
        
        @graceful_degradation(fallback=None, log_error=True)
        def failing_func():
            raise Exception("Test error")
        
        result = failing_func()
        assert result is None
        logger.warning.assert_called_once()
        assert "Graceful degradation triggered" in logger.warning.call_args[0][0]
    
    def test_no_logging(self):
        """Test disabling logging."""
        @graceful_degradation(fallback="default", log_error=False)
        def failing_func():
            raise Exception("Error")
        
        result = failing_func()
        assert result == "default"
        # No assertion for logging since it should be disabled
    
    def test_preserves_args_and_kwargs(self):
        """Test that args and kwargs are passed correctly."""
        def fallback_func(x, y, z=None):
            return f"fallback: x={x}, y={y}, z={z}"
        
        @graceful_degradation(fallback=fallback_func)
        def failing_func(x, y, z=None):
            raise Exception("Fail")
        
        result = failing_func(1, 2, z=3)
        assert result == "fallback: x=1, y=2, z=3"