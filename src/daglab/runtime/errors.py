"""Custom exception hierarchy with error codes and remediation guidance."""

import sys
from enum import IntEnum
from typing import Any, Dict, List, Optional, Type


class ExitCode(IntEnum):
    """Standard exit codes for Daglab operations."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISUSE = 2
    CANNOT_EXECUTE = 126
    COMMAND_NOT_FOUND = 127
    
    # Custom Daglab error codes (128+)
    CONFIGURATION_ERROR = 130
    VALIDATION_ERROR = 131
    SECURITY_ERROR = 132
    NETWORK_ERROR = 133
    STORAGE_ERROR = 134
    COMPUTE_ERROR = 135
    SCHEDULING_ERROR = 136
    RUNTIME_ERROR = 137
    DEPENDENCY_ERROR = 138
    AUTHENTICATION_ERROR = 139
    AUTHORIZATION_ERROR = 140
    RESOURCE_ERROR = 141
    TIMEOUT_ERROR = 142
    INTEGRATION_ERROR = 143


class ErrorContext:
    """Context information for debugging errors."""
    
    def __init__(
        self,
        operation: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.operation = operation
        self.resource = resource
        self.details = details or {}
        self.suggestions = suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'operation': self.operation,
            'resource': self.resource,
            'details': self.details,
            'suggestions': self.suggestions
        }


class DaglabError(Exception):
    """Base exception class for all Daglab errors."""
    
    exit_code: ExitCode = ExitCode.GENERAL_ERROR
    default_message: str = "An error occurred in Daglab"
    
    def __init__(
        self,
        message: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message or self.default_message
        self.context = context or ErrorContext()
        self.cause = cause
        
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Human-readable error message."""
        parts = [self.message]
        
        if self.context.operation:
            parts.append(f"Operation: {self.context.operation}")
        
        if self.context.resource:
            parts.append(f"Resource: {self.context.resource}")
        
        if self.context.details:
            parts.append(f"Details: {self.context.details}")
        
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {str(self.cause)}")
        
        if self.context.suggestions:
            parts.append("\nSuggestions:")
            for suggestion in self.context.suggestions:
                parts.append(f"  - {suggestion}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured logging."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'exit_code': self.exit_code.value,
            'context': self.context.to_dict(),
            'cause': str(self.cause) if self.cause else None
        }
    
    @classmethod
    def with_suggestions(cls, message: str, *suggestions: str) -> "DaglabError":
        """Create error with remediation suggestions."""
        context = ErrorContext(suggestions=list(suggestions))
        return cls(message=message, context=context)


class ConfigurationError(DaglabError):
    """Errors related to configuration loading or validation."""
    exit_code = ExitCode.CONFIGURATION_ERROR
    default_message = "Configuration error occurred"


class ValidationError(DaglabError):
    """Errors related to input validation."""
    exit_code = ExitCode.VALIDATION_ERROR
    default_message = "Validation error occurred"


class SecurityError(DaglabError):
    """Errors related to security violations."""
    exit_code = ExitCode.SECURITY_ERROR
    default_message = "Security violation detected"


class NetworkError(DaglabError):
    """Errors related to network operations."""
    exit_code = ExitCode.NETWORK_ERROR
    default_message = "Network operation failed"


class StorageError(DaglabError):
    """Errors related to storage operations."""
    exit_code = ExitCode.STORAGE_ERROR
    default_message = "Storage operation failed"


class ComputeError(DaglabError):
    """Errors related to compute operations."""
    exit_code = ExitCode.COMPUTE_ERROR
    default_message = "Compute operation failed"


class SchedulingError(DaglabError):
    """Errors related to task scheduling."""
    exit_code = ExitCode.SCHEDULING_ERROR
    default_message = "Scheduling operation failed"


class RuntimeError(DaglabError):
    """Errors that occur during runtime execution."""
    exit_code = ExitCode.RUNTIME_ERROR
    default_message = "Runtime error occurred"


class DependencyError(DaglabError):
    """Errors related to missing or incompatible dependencies."""
    exit_code = ExitCode.DEPENDENCY_ERROR
    default_message = "Dependency error occurred"


class AuthenticationError(DaglabError):
    """Errors related to authentication."""
    exit_code = ExitCode.AUTHENTICATION_ERROR
    default_message = "Authentication failed"


class AuthorizationError(DaglabError):
    """Errors related to authorization."""
    exit_code = ExitCode.AUTHORIZATION_ERROR
    default_message = "Authorization failed"


class ResourceError(DaglabError):
    """Errors related to resource availability or limits."""
    exit_code = ExitCode.RESOURCE_ERROR
    default_message = "Resource error occurred"


class TimeoutError(DaglabError):
    """Errors related to operation timeouts."""
    exit_code = ExitCode.TIMEOUT_ERROR
    default_message = "Operation timed out"


class IntegrationError(DaglabError):
    """Errors related to third-party integrations."""
    exit_code = ExitCode.INTEGRATION_ERROR
    default_message = "Integration error occurred"


class ErrorHandler:
    """Centralized error handling and reporting."""
    
    @staticmethod
    def handle_error(
        error: Exception,
        exit_on_error: bool = True,
        log_error: bool = True
    ) -> Optional[int]:
        """Handle an error with appropriate logging and exit behavior."""
        if log_error:
            import logging
            logger = logging.getLogger("daglab.errors")
            
            if isinstance(error, DaglabError):
                logger.error(
                    f"{type(error).__name__}: {error.message}",
                    extra=error.to_dict()
                )
            else:
                logger.error(
                    f"Unexpected error: {type(error).__name__}: {str(error)}",
                    exc_info=True
                )
        
        if exit_on_error:
            exit_code = error.exit_code if isinstance(error, DaglabError) else ExitCode.GENERAL_ERROR
            sys.exit(exit_code)
        
        return error.exit_code if isinstance(error, DaglabError) else ExitCode.GENERAL_ERROR
    
    @staticmethod
    def wrap_error(
        error: Exception,
        error_class: Type[DaglabError] = DaglabError,
        message: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ) -> DaglabError:
        """Wrap a standard exception in a DaglabError."""
        if isinstance(error, DaglabError):
            return error
        
        wrapped_message = message or f"{type(error).__name__}: {str(error)}"
        return error_class(message=wrapped_message, context=context, cause=error)


def graceful_degradation(
    func,
    fallback=None,
    error_class: Type[DaglabError] = RuntimeError,
    log_error: bool = True
):
    """Decorator for graceful degradation on errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                import logging
                logger = logging.getLogger("daglab.errors")
                logger.warning(f"Graceful degradation triggered: {str(e)}")
            
            if callable(fallback):
                return fallback(*args, **kwargs)
            return fallback
    
    return wrapper


class ErrorRecovery:
    """Advanced error recovery strategies."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._recovery_strategies = {}
        self._error_patterns = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies."""
        # Network errors
        self.register_strategy(
            NetworkError,
            lambda e: [
                "Check your internet connection",
                "Verify the remote server is accessible",
                "Check firewall settings",
                "Try using a VPN if the service is region-locked",
                f"Retry with: daglab {e.context.operation or 'command'} --retry"
            ]
        )
        
        # Configuration errors
        self.register_strategy(
            ConfigurationError,
            lambda e: [
                "Run: daglab config validate",
                "Check configuration file syntax",
                "Ensure all required fields are present",
                "Review environment variables",
                "Use: daglab config generate --template"
            ]
        )
        
        # Authentication errors
        self.register_strategy(
            AuthenticationError,
            lambda e: [
                "Check your credentials",
                "Run: daglab auth login",
                "Verify API keys are valid",
                "Check token expiration",
                "Review authentication configuration"
            ]
        )
        
        # Resource errors
        self.register_strategy(
            ResourceError,
            lambda e: [
                "Check available disk space",
                "Monitor memory usage with: daglab stats",
                "Close unnecessary applications",
                "Increase resource limits in configuration",
                "Consider using cloud resources"
            ]
        )
        
        # Timeout errors
        self.register_strategy(
            TimeoutError,
            lambda e: [
                "Increase timeout in configuration",
                "Check network latency",
                "Try during off-peak hours",
                "Break large operations into smaller chunks",
                "Use asynchronous execution mode"
            ]
        )
    
    def register_strategy(
        self,
        error_class: Type[DaglabError],
        strategy_func: callable
    ):
        """Register a recovery strategy for an error type."""
        self._recovery_strategies[error_class] = strategy_func
    
    def register_pattern(
        self,
        pattern: str,
        suggestions: List[str]
    ):
        """Register recovery suggestions for error message patterns."""
        import re
        self._error_patterns[re.compile(pattern, re.IGNORECASE)] = suggestions
    
    def get_suggestions(self, error: Exception) -> List[str]:
        """Get recovery suggestions for an error."""
        suggestions = []
        
        # Check registered strategies
        if isinstance(error, DaglabError):
            for error_class, strategy_func in self._recovery_strategies.items():
                if isinstance(error, error_class):
                    suggestions.extend(strategy_func(error))
                    break
            
            # Add context-specific suggestions
            if error.context and error.context.suggestions:
                suggestions.extend(error.context.suggestions)
        
        # Check error message patterns
        error_msg = str(error)
        for pattern, pattern_suggestions in self._error_patterns.items():
            if pattern.search(error_msg):
                suggestions.extend(pattern_suggestions)
        
        # Generic suggestions if none found
        if not suggestions:
            suggestions = [
                "Check the error message for details",
                "Review recent changes to configuration",
                "Consult the documentation",
                "Run with --debug for more information",
                "Report issue: daglab feedback --error"
            ]
        
        return list(dict.fromkeys(suggestions))  # Remove duplicates
    
    def retry_with_backoff(
        self,
        func: callable,
        *args,
        error_class: Type[Exception] = Exception,
        **kwargs
    ):
        """Retry a function with exponential backoff."""
        import time
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except error_class as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    sleep_time = (self.backoff_factor ** attempt) + 0.1
                    time.sleep(sleep_time)
        
        raise last_error
    
    def create_error_report(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a detailed error report."""
        import platform
        import sys
        import traceback
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
            "system": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "daglab_version": "0.1.0",  # TODO: Get from package
            },
            "context": context or {},
            "suggestions": self.get_suggestions(error),
        }
        
        if isinstance(error, DaglabError):
            report["error"]["exit_code"] = error.exit_code.value
            if error.context:
                report["error"]["context"] = error.context.to_dict()
        
        return report
    
    def save_error_report(self, report: Dict[str, Any], filepath: Optional[Path] = None):
        """Save error report to file."""
        import json
        from pathlib import Path
        
        if filepath is None:
            error_dir = Path.home() / ".daglab" / "error_reports"
            error_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = report["timestamp"].replace(":", "-").replace(".", "-")
            filepath = error_dir / f"error_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath


class ErrorContext(ErrorContext):
    """Enhanced error context with collection capabilities."""
    
    def collect_system_info(self) -> None:
        """Collect system information for debugging."""
        import platform
        import psutil
        
        self.details["system"] = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024 ** 3),
            "disk_usage": dict(psutil.disk_usage('/')._asdict()),
        }
    
    def collect_environment(self) -> None:
        """Collect relevant environment variables."""
        import os
        
        relevant_vars = [
            var for var in os.environ 
            if var.startswith(("DAGLAB_", "DAGSTER_", "MARIMO_"))
        ]
        
        self.details["environment"] = {
            var: os.environ[var] for var in relevant_vars
        }
    
    def add_code_context(self, filename: str, line_number: int, context_lines: int = 5):
        """Add code context around error location."""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            
            self.details["code_context"] = {
                "file": filename,
                "line": line_number,
                "snippet": ''.join(lines[start:end]),
                "start_line": start + 1,
            }
        except:
            pass


# Global error recovery instance
error_recovery = ErrorRecovery()


def with_recovery(func):
    """Decorator to add automatic error recovery to functions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DaglabError as e:
            # Get recovery suggestions
            suggestions = error_recovery.get_suggestions(e)
            
            # Enhance error with suggestions
            if not e.context.suggestions:
                e.context.suggestions = suggestions
            
            # Re-raise with enhanced context
            raise
        except Exception as e:
            # Wrap in DaglabError with suggestions
            wrapped = ErrorHandler.wrap_error(
                e,
                RuntimeError,
                context=ErrorContext(
                    operation=func.__name__,
                    suggestions=error_recovery.get_suggestions(e)
                )
            )
            raise wrapped
    
    return wrapper