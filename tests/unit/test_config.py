"""
Unit tests for DagLab configuration management system.
"""

import os
import json
import yaml
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any

from daglab.config import (
    DaglabConfig, DagsterConfig, MarimoConfig, DefaultsConfig,
    PerformanceConfig, ExportConfig, LoggingConfig, TelemetryConfig,
    SecurityConfig, ConfigLoader, LogLevel, ExportFormat, SecurityMode,
    get_config, reload_config
)


class TestDagsterConfig:
    """Test cases for DagsterConfig."""
    
    def test_default_values(self):
        """Test default DagsterConfig values."""
        config = DagsterConfig()
        assert config.repository_name == "daglab_repository"
        assert config.job_name == "daglab_job"
        assert config.run_launcher == "default"
        assert config.storage["filesystem"]["base_dir"] == "dagster_storage"
    
    def test_path_expansion(self):
        """Test home directory expansion."""
        config = DagsterConfig(home="~/test_dagster")
        assert str(config.home).startswith(str(Path.home()))
        assert str(config.home).endswith("test_dagster")
    
    def test_custom_values(self):
        """Test custom DagsterConfig values."""
        config = DagsterConfig(
            repository_name="custom_repo",
            job_name="custom_job",
            storage={"s3": {"bucket": "my-bucket"}}
        )
        assert config.repository_name == "custom_repo"
        assert config.job_name == "custom_job"
        assert config.storage["s3"]["bucket"] == "my-bucket"


class TestMarimoConfig:
    """Test cases for MarimoConfig."""
    
    def test_default_values(self):
        """Test default MarimoConfig values."""
        config = MarimoConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 2718
        assert config.auto_open is True
        assert config.theme == "light"
        assert config.autosave is True
        assert config.autosave_interval == 30
    
    def test_port_validation(self):
        """Test port number validation."""
        with pytest.raises(ValueError):
            MarimoConfig(port=70000)  # Too high
        
        with pytest.raises(ValueError):
            MarimoConfig(port=0)  # Too low
        
        # Valid port
        config = MarimoConfig(port=8080)
        assert config.port == 8080
    
    def test_theme_validation(self):
        """Test theme validation."""
        # Valid themes
        for theme in ["light", "dark", "auto"]:
            config = MarimoConfig(theme=theme)
            assert config.theme == theme
        
        # Invalid theme
        with pytest.raises(ValueError):
            MarimoConfig(theme="invalid")
    
    def test_notebook_dir_creation(self):
        """Test notebook directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook_dir = Path(tmpdir) / "notebooks"
            config = MarimoConfig(notebook_dir=notebook_dir)
            assert notebook_dir.exists()


class TestDefaultsConfig:
    """Test cases for DefaultsConfig."""
    
    def test_default_values(self):
        """Test default DefaultsConfig values."""
        config = DefaultsConfig()
        assert config.execution_timeout == 300
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.batch_size == 100
        assert config.parallelism == 4
    
    def test_validation(self):
        """Test validation constraints."""
        # Valid values
        config = DefaultsConfig(
            execution_timeout=600,
            retry_count=5,
            retry_delay=2.5,
            batch_size=200,
            parallelism=8
        )
        assert config.execution_timeout == 600
        
        # Invalid values
        with pytest.raises(ValueError):
            DefaultsConfig(execution_timeout=0)
        
        with pytest.raises(ValueError):
            DefaultsConfig(retry_delay=0.05)
        
        with pytest.raises(ValueError):
            DefaultsConfig(parallelism=0)


class TestPerformanceConfig:
    """Test cases for PerformanceConfig."""
    
    def test_default_values(self):
        """Test default PerformanceConfig values."""
        config = PerformanceConfig()
        assert config.cache_enabled is True
        assert config.cache_size == 1000
        assert config.cache_ttl == 3600
        assert config.memory_limit == "4G"
        assert config.cpu_limit is None
        assert config.enable_profiling is False
    
    def test_memory_limit_validation(self):
        """Test memory limit validation."""
        # Valid formats
        for limit in ["512M", "2G", "1024K", "8"]:
            config = PerformanceConfig(memory_limit=limit)
            assert config.memory_limit == limit
        
        # Invalid format
        with pytest.raises(ValueError):
            PerformanceConfig(memory_limit="invalid")


class TestExportConfig:
    """Test cases for ExportConfig."""
    
    def test_default_values(self):
        """Test default ExportConfig values."""
        config = ExportConfig()
        assert config.default_format == ExportFormat.YAML
        assert config.include_metadata is True
        assert config.pretty_print is True
        assert config.compression is None
    
    def test_compression_validation(self):
        """Test compression type validation."""
        # Valid compression types
        for comp in ["gzip", "zip", None]:
            config = ExportConfig(compression=comp)
            assert config.compression == comp
        
        # Invalid compression type
        with pytest.raises(ValueError):
            ExportConfig(compression="rar")
    
    def test_output_dir_creation(self):
        """Test output directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "exports"
            config = ExportConfig(output_dir=output_dir)
            assert output_dir.exists()


class TestLoggingConfig:
    """Test cases for LoggingConfig."""
    
    def test_default_values(self):
        """Test default LoggingConfig values."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.console_output is True
        assert config.structured is False
        assert config.backup_count == 5
        assert config.max_file_size == "10M"
    
    def test_log_level_enum(self):
        """Test log level enumeration."""
        for level in LogLevel:
            config = LoggingConfig(level=level)
            assert config.level == level
    
    def test_file_size_validation(self):
        """Test file size format validation."""
        # Valid formats
        for size in ["100K", "50M", "1G"]:
            config = LoggingConfig(max_file_size=size)
            assert config.max_file_size == size
        
        # Invalid format
        with pytest.raises(ValueError):
            LoggingConfig(max_file_size="invalid")


class TestTelemetryConfig:
    """Test cases for TelemetryConfig."""
    
    def test_default_values(self):
        """Test default TelemetryConfig values."""
        config = TelemetryConfig()
        assert config.enabled is False
        assert config.sample_rate == 1.0
        assert config.include_system_info is True
        assert config.flush_interval == 60
    
    def test_sample_rate_validation(self):
        """Test sample rate validation."""
        # Valid rates
        for rate in [0.0, 0.5, 1.0]:
            config = TelemetryConfig(sample_rate=rate)
            assert config.sample_rate == rate
        
        # Invalid rates
        with pytest.raises(ValueError):
            TelemetryConfig(sample_rate=1.5)
        
        with pytest.raises(ValueError):
            TelemetryConfig(sample_rate=-0.1)


class TestSecurityConfig:
    """Test cases for SecurityConfig."""
    
    def test_default_values(self):
        """Test default SecurityConfig values."""
        config = SecurityConfig()
        assert config.mode == SecurityMode.MODERATE
        assert config.enable_ssl is False
        assert config.enable_auth is False
        assert config.encrypt_storage is False
        assert "localhost" in config.allowed_hosts
        assert "127.0.0.1" in config.allowed_hosts
    
    def test_ssl_validation(self):
        """Test SSL configuration validation."""
        # SSL disabled - no validation
        config = SecurityConfig(
            enable_ssl=False,
            ssl_cert=Path("/nonexistent/cert.pem")
        )
        assert config.ssl_cert == Path("/nonexistent/cert.pem")
        
        # SSL enabled - requires valid paths
        with tempfile.NamedTemporaryFile(suffix=".pem") as cert:
            config = SecurityConfig(
                enable_ssl=True,
                ssl_cert=Path(cert.name)
            )
            assert config.ssl_cert == Path(cert.name)


class TestDaglabConfig:
    """Test cases for main DaglabConfig."""
    
    def test_default_values(self):
        """Test default DaglabConfig values."""
        config = DaglabConfig()
        assert config.project_name == "daglab"
        assert config.version == "0.1.0"
        assert config.environment == "development"
        assert config.debug is False
        
        # Check sub-configs
        assert isinstance(config.dagster, DagsterConfig)
        assert isinstance(config.marimo, MarimoConfig)
        assert isinstance(config.defaults, DefaultsConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.telemetry, TelemetryConfig)
        assert isinstance(config.security, SecurityConfig)
    
    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "test"]:
            config = DaglabConfig(environment=env)
            assert config.environment == env
        
        # Invalid environment
        with pytest.raises(ValueError):
            DaglabConfig(environment="invalid")
    
    def test_env_var_override(self):
        """Test environment variable overrides."""
        # Set environment variables
        os.environ["DAGLAB_PROJECT_NAME"] = "test_project"
        os.environ["DAGLAB_DEBUG"] = "true"
        os.environ["DAGLAB_DEFAULTS__EXECUTION_TIMEOUT"] = "600"
        os.environ["DAGLAB_MARIMO__PORT"] = "8888"
        
        try:
            config = DaglabConfig()
            assert config.project_name == "test_project"
            assert config.debug is True
            assert config.defaults.execution_timeout == 600
            assert config.marimo.port == 8888
        finally:
            # Cleanup
            del os.environ["DAGLAB_PROJECT_NAME"]
            del os.environ["DAGLAB_DEBUG"]
            del os.environ["DAGLAB_DEFAULTS__EXECUTION_TIMEOUT"]
            del os.environ["DAGLAB_MARIMO__PORT"]
    
    def test_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
        project_name: yaml_test
        version: 1.0.0
        environment: production
        debug: false
        
        dagster:
          repository_name: yaml_repo
          job_name: yaml_job
        
        marimo:
          port: 3000
          theme: dark
        
        logging:
          level: warning
          structured: true
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = DaglabConfig.from_file(f.name)
                assert config.project_name == "yaml_test"
                assert config.version == "1.0.0"
                assert config.environment == "production"
                assert config.dagster.repository_name == "yaml_repo"
                assert config.marimo.port == 3000
                assert config.marimo.theme == "dark"
                assert config.logging.level == LogLevel.WARNING
                assert config.logging.structured is True
            finally:
                os.unlink(f.name)
    
    def test_from_json_file(self):
        """Test loading configuration from JSON file."""
        json_content = {
            "project_name": "json_test",
            "version": "2.0.0",
            "debug": True,
            "performance": {
                "cache_enabled": False,
                "cache_size": 500
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            f.flush()
            
            try:
                config = DaglabConfig.from_file(f.name)
                assert config.project_name == "json_test"
                assert config.version == "2.0.0"
                assert config.debug is True
                assert config.performance.cache_enabled is False
                assert config.performance.cache_size == 500
            finally:
                os.unlink(f.name)
    
    def test_to_file_yaml(self):
        """Test saving configuration to YAML file."""
        config = DaglabConfig(
            project_name="save_test",
            environment="staging",
            marimo=MarimoConfig(port=4000)
        )
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            try:
                config.to_file(f.name)
                
                # Load and verify
                with open(f.name, 'r') as rf:
                    data = yaml.safe_load(rf)
                    assert data['project_name'] == "save_test"
                    assert data['environment'] == "staging"
                    assert data['marimo']['port'] == 4000
            finally:
                os.unlink(f.name)
    
    def test_merge_configs(self):
        """Test merging configurations."""
        base_config = DaglabConfig(
            project_name="base",
            debug=False,
            marimo=MarimoConfig(port=2718, theme="light")
        )
        
        updates = {
            "project_name": "merged",
            "debug": True,
            "marimo": {"theme": "dark"},
            "logging": {"level": "debug"}
        }
        
        merged = base_config.merge(updates)
        assert merged.project_name == "merged"
        assert merged.debug is True
        assert merged.marimo.port == 2718  # Preserved
        assert merged.marimo.theme == "dark"  # Updated
        assert merged.logging.level == LogLevel.DEBUG


class TestConfigLoader:
    """Test cases for ConfigLoader."""
    
    def test_default_loading(self):
        """Test loading with defaults."""
        loader = ConfigLoader()
        config = loader.load()
        assert isinstance(config, DaglabConfig)
        assert config.project_name == "daglab"
    
    def test_specific_file_loading(self):
        """Test loading from specific file."""
        config_data = {
            "project_name": "loader_test",
            "version": "3.0.0"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            
            try:
                loader = ConfigLoader(f.name)
                config = loader.load()
                assert config.project_name == "loader_test"
                assert config.version == "3.0.0"
            finally:
                os.unlink(f.name)
    
    def test_env_var_config_path(self):
        """Test loading from environment variable path."""
        config_data = {"project_name": "env_path_test"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            
            os.environ["DAGLAB_CONFIG"] = f.name
            
            try:
                loader = ConfigLoader()
                config = loader.load()
                assert config.project_name == "env_path_test"
            finally:
                del os.environ["DAGLAB_CONFIG"]
                os.unlink(f.name)
    
    def test_create_template(self):
        """Test creating configuration templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Development template
            dev_path = Path(tmpdir) / "dev_config.yaml"
            ConfigLoader.create_template(dev_path, environment="development")
            assert dev_path.exists()
            
            dev_config = DaglabConfig.from_file(dev_path)
            assert dev_config.environment == "development"
            assert dev_config.debug is True
            assert dev_config.logging.level == LogLevel.DEBUG
            
            # Production template
            prod_path = Path(tmpdir) / "prod_config.yaml"
            ConfigLoader.create_template(prod_path, environment="production")
            assert prod_path.exists()
            
            prod_config = DaglabConfig.from_file(prod_path)
            assert prod_config.environment == "production"
            assert prod_config.debug is False
            assert prod_config.logging.level == LogLevel.WARNING
            assert prod_config.security.mode == SecurityMode.STRICT
    
    def test_config_info(self):
        """Test getting configuration information."""
        info = ConfigLoader.get_config_info()
        assert "loaded_from" in info
        assert "environment" in info
        assert "debug" in info
        assert "env_vars" in info
        assert "search_paths" in info
        assert isinstance(info["search_paths"], list)


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_get_config(self):
        """Test get_config function."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2  # Should be cached
        assert isinstance(config1, DaglabConfig)
    
    def test_reload_config(self):
        """Test reload_config function."""
        config1 = get_config()
        config2 = reload_config()
        assert isinstance(config2, DaglabConfig)
        # After reload, get_config should return new instance
        config3 = get_config()
        assert config3 is not config1  # Cache cleared


@pytest.fixture
def clean_env():
    """Fixture to ensure clean environment variables."""
    # Store original env vars
    original = {k: v for k, v in os.environ.items() if k.startswith("DAGLAB_")}
    
    # Clear DAGLAB_ env vars
    for key in list(os.environ.keys()):
        if key.startswith("DAGLAB_"):
            del os.environ[key]
    
    yield
    
    # Restore original env vars
    for key, value in original.items():
        os.environ[key] = value


# Mark all test classes to use clean_env fixture
pytestmark = pytest.mark.usefixtures("clean_env")