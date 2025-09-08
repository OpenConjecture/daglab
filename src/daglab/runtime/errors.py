"""Custom exception hierarchy for daglab with error codes and remediation.

Provides structured error handling with clear messages, error codes,
and actionable remediation steps.
"""

import json
import traceback
from enum import Enum
from typing import Any, Dict, Optional, List


class ErrorCode(Enum):
    """Standardized error codes for daglab."""
    
    # Configuration errors (1xxx)
    CONFIG_NOT_FOUND = 1001
    CONFIG_INVALID = 1002
    CONFIG_MISSING_REQUIRED = 1003
    
    # Asset errors (2xxx)
    ASSET_NOT_FOUND = 2001
    ASSET_INVALID_DEFINITION = 2002
    ASSET_DEPENDENCY_MISSING = 2003
    ASSET_EXECUTION_FAILED = 2004
    ASSET_VALIDATION_FAILED = 2005
    
    # Notebook errors (3xxx)
    NOTEBOOK_NOT_FOUND = 3001
    NOTEBOOK_INVALID_FORMAT = 3002
    NOTEBOOK_EXECUTION_ERROR = 3003
    NOTEBOOK_KERNEL_ERROR = 3004
    NOTEBOOK_CELL_ERROR = 3005
    
    # Runtime errors (4xxx)
    RUNTIME_INITIALIZATION_FAILED = 4001
    RUNTIME_EXECUTION_FAILED = 4002
    RUNTIME_RESOURCE_EXHAUSTED = 4003
    RUNTIME_TIMEOUT = 4004
    RUNTIME_PERMISSION_DENIED = 4005
    
    # Storage errors (5xxx)
    STORAGE_CONNECTION_FAILED = 5001
    STORAGE_READ_FAILED = 5002
    STORAGE_WRITE_FAILED = 5003
    STORAGE_PERMISSION_DENIED = 5004
    
    # Validation errors (6xxx)
    VALIDATION_SCHEMA_INVALID = 6001
    VALIDATION_DATA_INVALID = 6002
    VALIDATION_TYPE_MISMATCH = 6003
    
    # Network errors (7xxx)
    NETWORK_CONNECTION_FAILED = 7001
    NETWORK_TIMEOUT = 7002
    NETWORK_AUTHENTICATION_FAILED = 7003
    
    # Unknown error
    UNKNOWN_ERROR = 9999


class DaglabError(Exception):
    """Base exception class for all daglab errors."""
    
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    default_message: str = "An error occurred in daglab"
    
    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        remediation: Optional[List[str]] = None
    ):
        """Initialize the error with structured information."""
        self.message = message or self.default_message
        self.details = details or {}
        self.cause = cause
        self.remediation = remediation or self._get_default_remediation()
        
        # Build the full error message
        super().__init__(self._build_message())
    
    def _build_message(self) -> str:
        """Build a comprehensive error message."""
        parts = [
            f"[{self.error_code.name}] {self.message}"
        ]
        
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {str(self.cause)}")
        
        if self.details:
            parts.append(f"Details: {json.dumps(self.details, indent=2)}")
        
        if self.remediation:
            parts.append("Remediation steps:")
            for i, step in enumerate(self.remediation, 1):
                parts.append(f"  {i}. {step}")
        
        return "\n".join(parts)
    
    def _get_default_remediation(self) -> List[str]:
        """Get default remediation steps for the error type."""
        return [
            "Check the error details for more information",
            "Review the documentation at https://docs.daglab.io",
            "Contact support if the issue persists"
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            'error_code': self.error_code.value,
            'error_name': self.error_code.name,
            'message': self.message,
            'details': self.details,
            'remediation': self.remediation,
            'traceback': traceback.format_exc() if self.cause else None
        }


# Configuration Errors
class ConfigurationError(DaglabError):
    """Base class for configuration-related errors."""
    error_code = ErrorCode.CONFIG_INVALID
    default_message = "Configuration error"


class ConfigNotFoundError(ConfigurationError):
    """Raised when a configuration file cannot be found."""
    error_code = ErrorCode.CONFIG_NOT_FOUND
    default_message = "Configuration file not found"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Ensure the configuration file exists in the expected location",
            "Check if DAGLAB_CONFIG environment variable is set correctly",
            "Run 'daglab init' to create a default configuration"
        ]


class ConfigInvalidError(ConfigurationError):
    """Raised when configuration is invalid."""
    error_code = ErrorCode.CONFIG_INVALID
    default_message = "Invalid configuration"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Validate your configuration against the schema",
            "Check for syntax errors in the configuration file",
            "Refer to the configuration documentation"
        ]


# Asset Errors
class AssetError(DaglabError):
    """Base class for asset-related errors."""
    error_code = ErrorCode.ASSET_EXECUTION_FAILED
    default_message = "Asset error"


class AssetNotFoundError(AssetError):
    """Raised when an asset cannot be found."""
    error_code = ErrorCode.ASSET_NOT_FOUND
    default_message = "Asset not found"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Verify the asset name is correct",
            "Check if the asset is registered in the asset catalog",
            "Ensure the asset module is properly imported"
        ]


class AssetDependencyError(AssetError):
    """Raised when asset dependencies are not met."""
    error_code = ErrorCode.ASSET_DEPENDENCY_MISSING
    default_message = "Asset dependency not satisfied"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check that all upstream dependencies are defined",
            "Verify dependency names are correct",
            "Ensure dependencies are executed before this asset"
        ]


class AssetExecutionError(AssetError):
    """Raised when asset execution fails."""
    error_code = ErrorCode.ASSET_EXECUTION_FAILED
    default_message = "Asset execution failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check the asset logs for detailed error information",
            "Verify input data is in the expected format",
            "Ensure all required resources are available",
            "Review the asset implementation for bugs"
        ]


# Notebook Errors
class NotebookError(DaglabError):
    """Base class for notebook-related errors."""
    error_code = ErrorCode.NOTEBOOK_EXECUTION_ERROR
    default_message = "Notebook error"


class NotebookNotFoundError(NotebookError):
    """Raised when a notebook cannot be found."""
    error_code = ErrorCode.NOTEBOOK_NOT_FOUND
    default_message = "Notebook not found"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Verify the notebook path is correct",
            "Check if the notebook file exists",
            "Ensure the notebook is in the expected directory"
        ]


class NotebookExecutionError(NotebookError):
    """Raised when notebook execution fails."""
    error_code = ErrorCode.NOTEBOOK_EXECUTION_ERROR
    default_message = "Notebook execution failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check the notebook cells for errors",
            "Verify all dependencies are installed",
            "Review the kernel logs for detailed error information",
            "Ensure the notebook environment matches requirements"
        ]


class NotebookCellError(NotebookError):
    """Raised when a specific notebook cell fails."""
    error_code = ErrorCode.NOTEBOOK_CELL_ERROR
    default_message = "Notebook cell execution failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Review the failing cell for syntax errors",
            "Check if required variables are defined in previous cells",
            "Verify imports and dependencies are available",
            "Run the notebook interactively to debug"
        ]


# Runtime Errors
class RuntimeError(DaglabError):
    """Base class for runtime errors."""
    error_code = ErrorCode.RUNTIME_EXECUTION_FAILED
    default_message = "Runtime error"


class RuntimeInitializationError(RuntimeError):
    """Raised when runtime initialization fails."""
    error_code = ErrorCode.RUNTIME_INITIALIZATION_FAILED
    default_message = "Runtime initialization failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check system requirements are met",
            "Verify all dependencies are installed",
            "Review initialization logs for errors",
            "Ensure configuration is valid"
        ]


class RuntimeTimeoutError(RuntimeError):
    """Raised when an operation times out."""
    error_code = ErrorCode.RUNTIME_TIMEOUT
    default_message = "Operation timed out"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Increase the timeout value if the operation is expected to take longer",
            "Check for performance issues or bottlenecks",
            "Consider breaking the operation into smaller chunks",
            "Review system resources (CPU, memory, network)"
        ]


class RuntimePermissionError(RuntimeError):
    """Raised when permissions are insufficient."""
    error_code = ErrorCode.RUNTIME_PERMISSION_DENIED
    default_message = "Permission denied"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check file and directory permissions",
            "Ensure the user has required privileges",
            "Verify API credentials and access tokens",
            "Review security policies and access controls"
        ]


# Storage Errors
class StorageError(DaglabError):
    """Base class for storage-related errors."""
    error_code = ErrorCode.STORAGE_CONNECTION_FAILED
    default_message = "Storage error"


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""
    error_code = ErrorCode.STORAGE_CONNECTION_FAILED
    default_message = "Failed to connect to storage"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Verify storage connection credentials",
            "Check network connectivity",
            "Ensure storage service is accessible",
            "Review firewall and security group settings"
        ]


class StorageReadError(StorageError):
    """Raised when reading from storage fails."""
    error_code = ErrorCode.STORAGE_READ_FAILED
    default_message = "Failed to read from storage"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Verify the resource exists in storage",
            "Check read permissions on the resource",
            "Ensure the storage path is correct",
            "Review storage access logs for errors"
        ]


class StorageWriteError(StorageError):
    """Raised when writing to storage fails."""
    error_code = ErrorCode.STORAGE_WRITE_FAILED
    default_message = "Failed to write to storage"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check write permissions on the destination",
            "Verify sufficient storage space is available",
            "Ensure the storage path is valid",
            "Review storage quotas and limits"
        ]


# Validation Errors
class ValidationError(DaglabError):
    """Base class for validation errors."""
    error_code = ErrorCode.VALIDATION_DATA_INVALID
    default_message = "Validation error"


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""
    error_code = ErrorCode.VALIDATION_SCHEMA_INVALID
    default_message = "Schema validation failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Review the data against the expected schema",
            "Check for missing required fields",
            "Verify data types match schema definitions",
            "Use validation tools to identify specific issues"
        ]


class DataValidationError(ValidationError):
    """Raised when data validation fails."""
    error_code = ErrorCode.VALIDATION_DATA_INVALID
    default_message = "Data validation failed"
    
    def _get_default_remediation(self) -> List[str]:
        return [
            "Check data quality and completeness",
            "Verify data formats and encodings",
            "Review validation rules and constraints",
            "Clean and preprocess data as needed"
        ]


# Helper functions
def wrap_error(
    error: Exception,
    error_class: type[DaglabError],
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> DaglabError:
    """Wrap a standard exception in a DaglabError."""
    return error_class(
        message=message or str(error),
        details=details,
        cause=error
    )


def get_error_by_code(error_code: int) -> type[DaglabError]:
    """Get the error class for a given error code."""
    # Build a mapping of error codes to classes
    error_map = {}
    for subclass in DaglabError.__subclasses__():
        if hasattr(subclass, 'error_code'):
            error_map[subclass.error_code.value] = subclass
        # Check nested subclasses
        for nested in subclass.__subclasses__():
            if hasattr(nested, 'error_code'):
                error_map[nested.error_code.value] = nested
    
    return error_map.get(error_code, DaglabError)