"""
DagLab Configuration Management System

This module provides comprehensive configuration management for DagLab,
supporting multiple configuration sources with proper override hierarchy.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import yaml
import json
from functools import lru_cache

from pydantic import BaseModel, Field, validator, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    YAML = "yaml"
    JSON = "json"
    PYTHON = "python"
    MARKDOWN = "markdown"


class SecurityMode(str, Enum):
    """Security mode enumeration."""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


class DagsterConfig(BaseModel):
    """Dagster-specific configuration."""
    model_config = ConfigDict(extra='forbid')
    
    home: Optional[Path] = Field(
        default=Path("~/.dagster").expanduser(),
        description="Dagster home directory"
    )
    instance_yaml: Optional[Path] = Field(
        default=None,
        description="Path to dagster.yaml instance config"
    )
    repository_name: str = Field(
        default="daglab_repository",
        description="Default repository name"
    )
    job_name: str = Field(
        default="daglab_job",
        description="Default job name"
    )
    run_launcher: str = Field(
        default="default",
        description="Run launcher type"
    )
    storage: Dict[str, Any] = Field(
        default_factory=lambda: {"filesystem": {"base_dir": "dagster_storage"}},
        description="Storage configuration"
    )
    event_log_storage: Dict[str, Any] = Field(
        default_factory=lambda: {"sqlite": {"base_dir": "dagster_events"}},
        description="Event log storage configuration"
    )
    compute_log_manager: Dict[str, Any] = Field(
        default_factory=lambda: {"module": "dagster.core.storage.local_compute_log_manager", 
                                "class": "LocalComputeLogManager"},
        description="Compute log manager configuration"
    )
    
    @field_validator('home', 'instance_yaml')
    @classmethod
    def expand_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Expand user home directory in paths."""
        if v is not None:
            return Path(str(v).replace("~", str(Path.home())))
        return v


class MarimoConfig(BaseModel):
    """Marimo-specific configuration."""
    model_config = ConfigDict(extra='forbid')
    
    host: str = Field(
        default="127.0.0.1",
        description="Marimo server host"
    )
    port: int = Field(
        default=2718,
        description="Marimo server port",
        ge=1,
        le=65535
    )
    auto_open: bool = Field(
        default=True,
        description="Auto-open browser on server start"
    )
    theme: str = Field(
        default="light",
        description="UI theme",
        pattern="^(light|dark|auto)$"
    )
    notebook_dir: Path = Field(
        default=Path("./notebooks"),
        description="Default notebook directory"
    )
    autosave: bool = Field(
        default=True,
        description="Enable autosave"
    )
    autosave_interval: int = Field(
        default=30,
        description="Autosave interval in seconds",
        ge=5
    )
    
    @field_validator('notebook_dir')
    @classmethod
    def expand_notebook_dir(cls, v: Path) -> Path:
        """Expand and create notebook directory if needed."""
        expanded = Path(str(v).replace("~", str(Path.home())))
        expanded.mkdir(parents=True, exist_ok=True)
        return expanded


class DefaultsConfig(BaseModel):
    """Default values configuration."""
    model_config = ConfigDict(extra='forbid')
    
    execution_timeout: int = Field(
        default=300,
        description="Default execution timeout in seconds",
        ge=1
    )
    retry_count: int = Field(
        default=3,
        description="Default retry count for failed operations",
        ge=0
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds",
        ge=0.1
    )
    batch_size: int = Field(
        default=100,
        description="Default batch size for operations",
        ge=1
    )
    parallelism: int = Field(
        default=4,
        description="Default parallelism level",
        ge=1
    )
    temp_dir: Path = Field(
        default=Path("/tmp/daglab"),
        description="Temporary directory for intermediate files"
    )
    
    @field_validator('temp_dir')
    @classmethod
    def create_temp_dir(cls, v: Path) -> Path:
        """Create temp directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class PerformanceConfig(BaseModel):
    """Performance tuning configuration."""
    model_config = ConfigDict(extra='forbid')
    
    cache_enabled: bool = Field(
        default=True,
        description="Enable caching"
    )
    cache_size: int = Field(
        default=1000,
        description="Maximum cache entries",
        ge=0
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds",
        ge=0
    )
    memory_limit: Optional[str] = Field(
        default="4G",
        description="Memory limit (e.g., '4G', '512M')",
        pattern="^[0-9]+[KMG]?$"
    )
    cpu_limit: Optional[int] = Field(
        default=None,
        description="CPU core limit",
        ge=1
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling"
    )
    profile_output_dir: Path = Field(
        default=Path("./profiles"),
        description="Directory for profiling output"
    )


class ExportConfig(BaseModel):
    """Export configuration."""
    model_config = ConfigDict(extra='forbid')
    
    default_format: ExportFormat = Field(
        default=ExportFormat.YAML,
        description="Default export format"
    )
    output_dir: Path = Field(
        default=Path("./exports"),
        description="Default export directory"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in exports"
    )
    pretty_print: bool = Field(
        default=True,
        description="Pretty print exported files"
    )
    compression: Optional[str] = Field(
        default=None,
        description="Compression type (gzip, zip, None)",
        pattern="^(gzip|zip)?$"
    )
    
    @field_validator('output_dir')
    @classmethod
    def create_output_dir(cls, v: Path) -> Path:
        """Create output directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    model_config = ConfigDict(extra='forbid')
    
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Default logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file: Optional[Path] = Field(
        default=None,
        description="Log file path"
    )
    max_file_size: str = Field(
        default="10M",
        description="Maximum log file size",
        pattern="^[0-9]+[KMG]?$"
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files",
        ge=0
    )
    console_output: bool = Field(
        default=True,
        description="Enable console output"
    )
    structured: bool = Field(
        default=False,
        description="Use structured JSON logging"
    )


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    model_config = ConfigDict(extra='forbid')
    
    enabled: bool = Field(
        default=False,
        description="Enable telemetry"
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="Telemetry endpoint URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Telemetry API key"
    )
    sample_rate: float = Field(
        default=1.0,
        description="Telemetry sampling rate",
        ge=0.0,
        le=1.0
    )
    include_system_info: bool = Field(
        default=True,
        description="Include system information"
    )
    flush_interval: int = Field(
        default=60,
        description="Flush interval in seconds",
        ge=1
    )


class SecurityConfig(BaseModel):
    """Security configuration."""
    model_config = ConfigDict(extra='forbid')
    
    mode: SecurityMode = Field(
        default=SecurityMode.MODERATE,
        description="Security mode"
    )
    enable_ssl: bool = Field(
        default=False,
        description="Enable SSL/TLS"
    )
    ssl_cert: Optional[Path] = Field(
        default=None,
        description="SSL certificate path"
    )
    ssl_key: Optional[Path] = Field(
        default=None,
        description="SSL key path"
    )
    allowed_hosts: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        description="Allowed hosts for connections"
    )
    enable_auth: bool = Field(
        default=False,
        description="Enable authentication"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Authentication token"
    )
    encrypt_storage: bool = Field(
        default=False,
        description="Encrypt storage at rest"
    )
    
    @field_validator('ssl_cert', 'ssl_key')
    @classmethod
    def validate_ssl_paths(cls, v: Optional[Path], info) -> Optional[Path]:
        """Validate SSL certificate and key paths."""
        if info.data.get('enable_ssl') and v is not None:
            if not v.exists():
                raise ValueError(f"SSL file not found: {v}")
        return v


class DaglabConfig(BaseSettings):
    """Main DagLab configuration."""
    model_config = SettingsConfigDict(
        env_prefix='DAGLAB_',
        env_nested_delimiter='__',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='forbid',
        validate_assignment=True
    )
    
    # Sub-configurations
    dagster: DagsterConfig = Field(
        default_factory=DagsterConfig,
        description="Dagster configuration"
    )
    marimo: MarimoConfig = Field(
        default_factory=MarimoConfig,
        description="Marimo configuration"
    )
    defaults: DefaultsConfig = Field(
        default_factory=DefaultsConfig,
        description="Default values"
    )
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description="Performance settings"
    )
    export: ExportConfig = Field(
        default_factory=ExportConfig,
        description="Export settings"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging settings"
    )
    telemetry: TelemetryConfig = Field(
        default_factory=TelemetryConfig,
        description="Telemetry settings"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security settings"
    )
    
    # Global settings
    project_name: str = Field(
        default="daglab",
        description="Project name"
    )
    version: str = Field(
        default="0.1.0",
        description="Configuration version"
    )
    environment: str = Field(
        default="development",
        description="Environment name",
        pattern="^(development|staging|production|test)$"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "DaglabConfig":
        """Load configuration from a YAML or JSON file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        return cls(**data)
    
    def to_file(self, config_path: Union[str, Path], format: Optional[str] = None) -> None:
        """Save configuration to a file."""
        config_path = Path(config_path)
        
        # Determine format from extension if not specified
        if format is None:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                format = 'yaml'
            elif config_path.suffix.lower() == '.json':
                format = 'json'
            else:
                format = 'yaml'  # Default to YAML
        
        # Convert to dict and save
        data = self.model_dump(mode='json')
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            if format == 'yaml':
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            elif format == 'json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")
    
    def merge(self, other: Dict[str, Any]) -> "DaglabConfig":
        """Merge another configuration dict into this one."""
        current = self.model_dump()
        merged = self._deep_merge(current, other)
        return self.__class__(**merged)
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DaglabConfig._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result


class ConfigLoader:
    """Configuration loader with override hierarchy."""
    
    DEFAULT_CONFIG_LOCATIONS = [
        Path("./daglab.yaml"),
        Path("./daglab.yml"),
        Path("./daglab.json"),
        Path("./.daglab/config.yaml"),
        Path("./.daglab/config.yml"),
        Path("./.daglab/config.json"),
        Path.home() / ".daglab" / "config.yaml",
        Path.home() / ".daglab" / "config.yml",
        Path.home() / ".daglab" / "config.json",
        Path("/etc/daglab/config.yaml"),
        Path("/etc/daglab/config.yml"),
        Path("/etc/daglab/config.json"),
    ]
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize the config loader."""
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[DaglabConfig] = None
    
    @property
    def config(self) -> DaglabConfig:
        """Get the loaded configuration (lazy loading)."""
        if self._config is None:
            self._config = self.load()
        return self._config
    
    def load(self) -> DaglabConfig:
        """
        Load configuration with the following priority (highest to lowest):
        1. Command-line arguments (if passed to methods)
        2. Environment variables (DAGLAB_*)
        3. Specified config file (if provided)
        4. Default config file locations
        5. Built-in defaults
        """
        config = DaglabConfig()
        
        # Try to load from file
        config_file = self._find_config_file()
        if config_file:
            try:
                file_config = DaglabConfig.from_file(config_file)
                # File config is already merged with env vars by Pydantic
                config = file_config
            except Exception as e:
                # Log warning but continue with defaults
                print(f"Warning: Failed to load config from {config_file}: {e}")
        
        return config
    
    def _find_config_file(self) -> Optional[Path]:
        """Find the configuration file to use."""
        # If specific path provided, use it
        if self.config_path and self.config_path.exists():
            return self.config_path
        
        # Check environment variable
        env_config = os.environ.get("DAGLAB_CONFIG")
        if env_config:
            env_path = Path(env_config)
            if env_path.exists():
                return env_path
        
        # Check default locations
        for location in self.DEFAULT_CONFIG_LOCATIONS:
            if location.exists():
                return location
        
        return None
    
    @classmethod
    def create_template(
        cls, 
        path: Union[str, Path], 
        environment: str = "development",
        format: str = "yaml"
    ) -> None:
        """Create a template configuration file."""
        path = Path(path)
        
        # Create appropriate config based on environment
        if environment == "development":
            config = DaglabConfig(
                environment="development",
                debug=True,
                logging=LoggingConfig(level=LogLevel.DEBUG)
            )
        elif environment == "production":
            config = DaglabConfig(
                environment="production",
                debug=False,
                logging=LoggingConfig(level=LogLevel.WARNING),
                security=SecurityConfig(mode=SecurityMode.STRICT),
                performance=PerformanceConfig(enable_profiling=False)
            )
        else:
            config = DaglabConfig(environment=environment)
        
        config.to_file(path, format=format)
        print(f"Created template configuration at: {path}")
    
    @classmethod
    def get_config_info(cls) -> Dict[str, Any]:
        """Get information about configuration sources and values."""
        loader = cls()
        config = loader.config
        
        return {
            "loaded_from": str(loader._find_config_file() or "defaults"),
            "environment": config.environment,
            "debug": config.debug,
            "env_vars": {
                k: v for k, v in os.environ.items() 
                if k.startswith("DAGLAB_")
            },
            "search_paths": [str(p) for p in cls.DEFAULT_CONFIG_LOCATIONS]
        }


# Convenience functions
@lru_cache(maxsize=1)
def get_config(config_path: Optional[str] = None) -> DaglabConfig:
    """Get the global configuration instance."""
    loader = ConfigLoader(config_path)
    return loader.config


def reload_config(config_path: Optional[str] = None) -> DaglabConfig:
    """Reload the configuration (clears cache)."""
    get_config.cache_clear()
    return get_config(config_path)