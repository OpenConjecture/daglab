"""Unit tests for configuration management."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from pydantic import ValidationError

from daglab.config import (
    get_config_search_paths,
    DagsterConfig,
    DaglabConfig,
    DefaultsConfig,
    ExportConfig,
    ExportFormat,
    LogLevel,
    LoggingConfig,
    MarimoConfig,
    PerformanceConfig,
    SecurityConfig,
    TelemetryConfig,
    TelemetryLevel,
    find_config_file,
    get_config,
    get_default_config,
    load_config,
    load_config_file,
    merge_configs,
    save_config,
    set_config,
)


class TestConfigModels:
    """Test individual configuration models."""
    
    def test_dagster_config_defaults(self):
        """Test DagsterConfig default values."""
        config = DagsterConfig()
        assert config.project_dir == Path.cwd()
        assert config.module_name is None
        assert config.repository_name is None
        assert config.assets_module == "assets"
        assert config.jobs_module == "jobs"
    
    def test_dagster_config_path_resolution(self):
        """Test that paths are resolved to absolute."""
        config = DagsterConfig(project_dir=Path("../relative/path"))
        assert config.project_dir.is_absolute()
    
    def test_marimo_config_defaults(self):
        """Test MarimoConfig default values."""
        config = MarimoConfig()
        assert config.port_range_start == 2718
        assert config.port_range_end == 2818
        assert config.auto_reload is True
        assert config.theme == "light"
        assert config.layout_file is None
    
    def test_marimo_config_port_validation(self):
        """Test port range validation."""
        # Valid range
        config = MarimoConfig(port_range_start=3000, port_range_end=3100)
        assert config.port_range_start == 3000
        assert config.port_range_end == 3100
        
        # Invalid range
        with pytest.raises(ValidationError):
            MarimoConfig(port_range_start=3000, port_range_end=2999)
    
    def test_defaults_config(self):
        """Test DefaultsConfig values."""
        config = DefaultsConfig()
        assert config.author is None
        assert config.email is None
        assert config.license == "MIT"
        assert config.python_version == "3.10"
        assert config.tags == []
        
        # With custom values
        config = DefaultsConfig(
            author="John Doe",
            email="john@example.com",
            tags=["test", "example"]
        )
        assert config.author == "John Doe"
        assert config.email == "john@example.com"
        assert config.tags == ["test", "example"]
    
    def test_performance_config(self):
        """Test PerformanceConfig values and validation."""
        config = PerformanceConfig()
        assert config.max_workers == 4
        assert config.timeout == 300
        assert config.cache_enabled is True
        assert config.cache_dir == Path.home() / ".cache" / "daglab"
        
        # Test validation
        with pytest.raises(ValidationError):
            PerformanceConfig(max_workers=0)
        
        with pytest.raises(ValidationError):
            PerformanceConfig(timeout=-1)
    
    def test_export_config(self):
        """Test ExportConfig values."""
        config = ExportConfig()
        assert ExportFormat.PYTHON in config.formats
        assert ExportFormat.HTML in config.formats
        assert config.output_dir == Path.cwd() / "exports"
        assert config.include_metadata is True
        assert config.minify is False
    
    def test_logging_config(self):
        """Test LoggingConfig values."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.file is None
        assert config.json_format is False
        assert config.rotation == "10MB"
        assert config.retention == 7
        
        # With custom values
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            file=Path("/var/log/daglab.log"),
            json_format=True
        )
        assert config.level == LogLevel.DEBUG
        assert config.file == Path("/var/log/daglab.log")
        assert config.json_format is True
    
    def test_telemetry_config(self):
        """Test TelemetryConfig values."""
        config = TelemetryConfig()
        assert config.enabled is False
        assert config.level == TelemetryLevel.ANONYMOUS
        assert config.endpoint is None
        assert config.batch_size == 100
        assert config.flush_interval == 60
        
        # Test validation
        with pytest.raises(ValidationError):
            TelemetryConfig(batch_size=0)
    
    def test_security_config(self):
        """Test SecurityConfig values."""
        config = SecurityConfig()
        assert config.sandbox_enabled is True
        assert "dagster" in config.allowed_imports
        assert "marimo" in config.allowed_imports
        assert config.restricted_paths == []
        assert config.validate_inputs is True
        assert config.max_file_size == 100 * 1024 * 1024


class TestDaglabConfig:
    """Test main DaglabConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DaglabConfig()
        assert config.version == "1.0"
        assert config.notebooks_dir == Path("dagster/notebooks").resolve()
        assert isinstance(config.dagster, DagsterConfig)
        assert isinstance(config.marimo, MarimoConfig)
        assert isinstance(config.defaults, DefaultsConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.telemetry, TelemetryConfig)
        assert isinstance(config.security, SecurityConfig)
    
    def test_environment_variables(self, monkeypatch):
        """Test loading from environment variables."""
        # Set environment variables
        monkeypatch.setenv("daglab_version", "2.0")
        monkeypatch.setenv("daglab_notebooks_dir", "/custom/notebooks")
        monkeypatch.setenv("daglab_dagster__assets_module", "custom_assets")
        monkeypatch.setenv("daglab_marimo__port_range_start", "4000")
        monkeypatch.setenv("daglab_marimo__port_range_end", "4100")
        monkeypatch.setenv("daglab_logging__level", "DEBUG")
        monkeypatch.setenv("daglab_performance__max_workers", "8")
        
        config = DaglabConfig()
        assert config.version == "2.0"
        assert config.notebooks_dir == Path("/custom/notebooks")
        assert config.dagster.assets_module == "custom_assets"
        assert config.marimo.port_range_start == 4000
        assert config.marimo.port_range_end == 4100
        assert config.logging.level == LogLevel.DEBUG
        assert config.performance.max_workers == 8
    
    def test_nested_config_creation(self):
        """Test creating config with nested values."""
        config = DaglabConfig(
            version="1.1",
            dagster=DagsterConfig(
                project_dir=Path("/custom/project"),
                assets_module="my_assets"
            ),
            marimo=MarimoConfig(
                port_range_start=5000,
                port_range_end=5100,
                theme="dark"
            )
        )
        
        assert config.version == "1.1"
        assert config.dagster.project_dir == Path("/custom/project")
        assert config.dagster.assets_module == "my_assets"
        assert config.marimo.port_range_start == 5000
        assert config.marimo.theme == "dark"


class TestConfigLoading:
    """Test configuration loading functionality."""
    
    def test_find_config_file_custom(self, tmp_path):
        """Test finding custom config file."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("version: '1.0'")
        
        found = find_config_file(config_file)
        assert found == config_file
        
        # Non-existent custom file
        found = find_config_file(tmp_path / "nonexistent.yaml")
        assert found is None
    
    def test_find_config_file_standard_locations(self, tmp_path, monkeypatch):
        """Test finding config in standard locations."""
        # Change working directory to temp path
        monkeypatch.chdir(tmp_path)
        
        # No config files
        found = find_config_file()
        assert found is None
        
        # Create config in current directory
        config_file = tmp_path / "daglab.yaml"
        config_file.write_text("version: '1.0'")
        
        found = find_config_file()
        assert found == config_file
    
    def test_load_config_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "test.yaml"
        config_data = {
            "version": "1.1",
            "notebooks_dir": "/custom/notebooks",
            "dagster": {
                "assets_module": "custom_assets"
            }
        }
        
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        loaded = load_config_file(config_file)
        assert loaded["version"] == "1.1"
        assert loaded["notebooks_dir"] == "/custom/notebooks"
        assert loaded["dagster"]["assets_module"] == "custom_assets"
    
    def test_load_config_file_invalid(self, tmp_path):
        """Test loading invalid configuration files."""
        # Non-YAML file
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("not valid yaml: [")
        
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            load_config_file(config_file)
        
        # Non-dictionary YAML
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2")
        
        with pytest.raises(ValueError, match="must contain a YAML dictionary"):
            load_config_file(config_file)
    
    def test_merge_configs(self):
        """Test configuration merging."""
        base = {
            "version": "1.0",
            "dagster": {
                "assets_module": "assets",
                "jobs_module": "jobs"
            },
            "marimo": {
                "port_range_start": 2718
            }
        }
        
        override = {
            "version": "1.1",
            "dagster": {
                "assets_module": "custom_assets"
            },
            "marimo": {
                "theme": "dark"
            },
            "new_field": "value"
        }
        
        result = merge_configs(base, override)
        
        assert result["version"] == "1.1"
        assert result["dagster"]["assets_module"] == "custom_assets"
        assert result["dagster"]["jobs_module"] == "jobs"  # Preserved from base
        assert result["marimo"]["port_range_start"] == 2718  # Preserved from base
        assert result["marimo"]["theme"] == "dark"
        assert result["new_field"] == "value"
    
    def test_load_config_hierarchy(self, tmp_path, monkeypatch):
        """Test complete configuration loading hierarchy."""
        # Create config file
        config_file = tmp_path / "daglab.yaml"
        config_data = {
            "version": "1.0",
            "notebooks_dir": "from_file",
            "dagster": {
                "assets_module": "file_assets"
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        # Set environment variable (higher priority)
        monkeypatch.setenv("daglab_notebooks_dir", "from_env")
        
        # CLI override (highest priority)
        cli_overrides = {
            "version": "2.0",
            "dagster": {
                "jobs_module": "cli_jobs"
            }
        }
        
        # Load configuration
        config = load_config(config_file, cli_overrides)
        
        # Check hierarchy: CLI > ENV > File > Defaults
        assert config.version == "2.0"  # From CLI
        assert str(config.notebooks_dir).endswith("from_env")  # From ENV
        assert config.dagster.assets_module == "file_assets"  # From file
        assert config.dagster.jobs_module == "cli_jobs"  # From CLI
        assert config.marimo.port_range_start == 2718  # Default
    
    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        config = DaglabConfig(
            version="1.2",
            dagster=DagsterConfig(assets_module="test_assets"),
            marimo=MarimoConfig(theme="dark")
        )
        
        output_file = tmp_path / "output.yaml"
        save_config(config, output_file, comments=True)
        
        assert output_file.exists()
        
        # Load and verify
        with open(output_file) as f:
            content = f.read()
            assert "# daglab configuration file" in content
            assert "Version: 1.2" in content
        
        loaded = yaml.safe_load(output_file.read_text())
        assert loaded["version"] == "1.2"
        assert loaded["dagster"]["assets_module"] == "test_assets"
        assert loaded["marimo"]["theme"] == "dark"


class TestGlobalConfig:
    """Test global configuration management."""
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()
        assert isinstance(config, DaglabConfig)
        assert config.version == "1.0"
    
    def test_get_config_singleton(self):
        """Test configuration singleton behavior."""
        # Clear any existing config
        set_config(None)
        
        # First call creates config
        config1 = get_config()
        assert isinstance(config1, DaglabConfig)
        
        # Second call returns same instance
        config2 = get_config()
        assert config2 is config1
    
    def test_set_config(self):
        """Test setting global configuration."""
        custom_config = DaglabConfig(version="2.0")
        set_config(custom_config)
        
        retrieved = get_config()
        assert retrieved is custom_config
        assert retrieved.version == "2.0"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_invalid_enum_values(self):
        """Test invalid enum values."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")
        
        with pytest.raises(ValidationError):
            TelemetryConfig(level="invalid")
        
        with pytest.raises(ValidationError):
            ExportConfig(formats=["invalid_format"])
    
    def test_path_validation(self):
        """Test path validation and resolution."""
        # Relative paths should be resolved
        config = DaglabConfig(notebooks_dir="relative/path")
        assert config.notebooks_dir.is_absolute()
        
        # Same for nested configs
        config = PerformanceConfig(cache_dir="./cache")
        assert config.cache_dir.is_absolute()
    
    def test_numeric_validation(self):
        """Test numeric field validation."""
        # Port ranges
        with pytest.raises(ValidationError):
            MarimoConfig(port_range_start=0)  # Too low
        
        with pytest.raises(ValidationError):
            MarimoConfig(port_range_end=70000)  # Too high
        
        # Worker counts
        with pytest.raises(ValidationError):
            PerformanceConfig(max_workers=0)
        
        # Timeouts
        with pytest.raises(ValidationError):
            PerformanceConfig(timeout=0)
    
    def test_empty_config_file(self, tmp_path):
        """Test loading empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        
        # Should not raise, just use defaults
        config = load_config(config_file)
        assert config.version == "1.0"