"""Runtime utilities for daglab.

Provides logging, error handling, and telemetry capabilities.
"""

from daglab.runtime.logging import (
    get_logger,
    log_event,
    log_metric,
    log_duration,
    DaglabLogger,
    SecurityFilter,
    JSONFormatter
)

from daglab.runtime.errors import (
    DaglabError,
    ErrorCode,
    ConfigurationError,
    ConfigNotFoundError,
    ConfigInvalidError,
    AssetError,
    AssetNotFoundError,
    AssetDependencyError,
    AssetExecutionError,
    NotebookError,
    NotebookNotFoundError,
    NotebookExecutionError,
    NotebookCellError,
    RuntimeError,
    RuntimeInitializationError,
    RuntimeTimeoutError,
    RuntimePermissionError,
    StorageError,
    StorageConnectionError,
    StorageReadError,
    StorageWriteError,
    ValidationError,
    SchemaValidationError,
    DataValidationError,
    wrap_error,
    get_error_by_code
)

from daglab.runtime.telemetry import (
    TelemetryClient,
    TelemetryLevel,
    MetricType,
    TelemetryEvent,
    Metric,
    get_telemetry_client,
    track_event,
    track_operation,
    record_metric,
    increment_counter,
    set_gauge
)

__all__ = [
    # Logging
    'get_logger',
    'log_event',
    'log_metric', 
    'log_duration',
    'DaglabLogger',
    'SecurityFilter',
    'JSONFormatter',
    
    # Errors
    'DaglabError',
    'ErrorCode',
    'ConfigurationError',
    'ConfigNotFoundError',
    'ConfigInvalidError',
    'AssetError',
    'AssetNotFoundError',
    'AssetDependencyError',
    'AssetExecutionError',
    'NotebookError',
    'NotebookNotFoundError',
    'NotebookExecutionError',
    'NotebookCellError',
    'RuntimeError',
    'RuntimeInitializationError',
    'RuntimeTimeoutError',
    'RuntimePermissionError',
    'StorageError',
    'StorageConnectionError',
    'StorageReadError',
    'StorageWriteError',
    'ValidationError',
    'SchemaValidationError',
    'DataValidationError',
    'wrap_error',
    'get_error_by_code',
    
    # Telemetry
    'TelemetryClient',
    'TelemetryLevel',
    'MetricType',
    'TelemetryEvent',
    'Metric',
    'get_telemetry_client',
    'track_event',
    'track_operation',
    'record_metric',
    'increment_counter',
    'set_gauge'
]