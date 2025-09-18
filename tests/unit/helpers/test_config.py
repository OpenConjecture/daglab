"""Tests for configuration helper functions."""

import json
import os
import tempfile
from pathlib import Path
import pytest
import yaml

from daglab.helpers.config import (
    load_config_from_file,
    validate_run_config,
    expand_config_variables,
    merge_configs,
    get_default_config,
    save_config,
    diff_configs
)


class TestConfigHelpers:
    """Test configuration helper functions."""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "resources": {
                "io_manager": {
                    "config": {
                        "base_dir": "/tmp/dagster"
                    }
                }
            },
            "ops": {
                "my_op": {
                    "config": {
                        "param1": "value1",
                        "param2": 42
                    }
                }
            }
        }
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_load_config_from_yaml(self, temp_dir, sample_config):
        """Test loading configuration from YAML file."""
        config_path = temp_dir / "config.yaml"
        
        # Write YAML config
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)
        
        # Load and verify
        loaded = load_config_from_file(config_path)
        assert loaded == sample_config
    
    def test_load_config_from_json(self, temp_dir, sample_config):
        """Test loading configuration from JSON file."""
        config_path = temp_dir / "config.json"
        
        # Write JSON config
        with open(config_path, "w") as f:
            json.dump(sample_config, f)
        
        # Load and verify
        loaded = load_config_from_file(config_path)
        assert loaded == sample_config
    
    def test_load_config_with_env_vars(self, temp_dir, monkeypatch):
        """Test loading config with environment variable expansion."""
        monkeypatch.setenv("BASE_DIR", "/data/dagster")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        config = {
            "resources": {
                "io_manager": {
                    "config": {
                        "base_dir": "${BASE_DIR}"
                    }
                }
            },
            "loggers": {
                "console": {
                    "config": {
                        "log_level": "${LOG_LEVEL}"
                    }
                }
            }
        }
        
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        
        loaded = load_config_from_file(config_path, expand_vars=True)
        
        assert loaded["resources"]["io_manager"]["config"]["base_dir"] == "/data/dagster"
        assert loaded["loggers"]["console"]["config"]["log_level"] == "DEBUG"
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/non/existent/config.yaml")
    
    def test_load_config_unsupported_format(self, temp_dir):
        """Test loading config with unsupported format."""
        config_path = temp_dir / "config.txt"
        config_path.write_text("some text")
        
        with pytest.raises(ValueError, match="Unsupported config file format"):
            load_config_from_file(config_path)
    
    def test_validate_run_config_basic(self):
        """Test basic run config validation."""
        config = {
            "resources": {
                "io_manager": {
                    "config": {
                        "base_dir": "/tmp"
                    }
                }
            },
            "ops": {
                "my_op": {
                    "config": {
                        "value": 42
                    }
                }
            }
        }
        
        result = validate_run_config(config)
        
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []
    
    def test_validate_run_config_invalid(self):
        """Test validation of invalid run config."""
        config = {
            "resources": {
                "io_manager": "invalid"  # Should be dict
            },
            "ops": {
                "my_op": "invalid"  # Should be dict
            }
        }
        
        result = validate_run_config(config)
        
        assert result["valid"] is False
        assert len(result["errors"]) == 2
        assert "must be a dictionary" in result["errors"][0]
    
    def test_validate_run_config_with_schema(self):
        """Test validation with custom schema."""
        schema = {
            "type": "object",
            "properties": {
                "ops": {
                    "type": "object",
                    "properties": {
                        "my_op": {
                            "type": "object",
                            "properties": {
                                "config": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "integer"}
                                    },
                                    "required": ["value"]
                                }
                            }
                        }
                    }
                }
            },
            "required": ["ops"]
        }
        
        # Valid config
        config = {"ops": {"my_op": {"config": {"value": 42}}}}
        result = validate_run_config(config, schema)
        assert result["valid"] is True
        
        # Invalid config - missing required field
        config = {"ops": {"my_op": {"config": {}}}}
        result = validate_run_config(config, schema)
        assert result["valid"] is False
        assert "Missing required property 'value'" in result["errors"][0]
    
    def test_expand_config_variables(self, monkeypatch):
        """Test environment variable expansion."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "5432")
        
        config = {
            "database": {
                "host": "${DB_HOST}",
                "port": "${DB_PORT}",
                "url": "${DB_HOST}:${DB_PORT}"
            }
        }
        
        expanded = expand_config_variables(config)
        
        assert expanded["database"]["host"] == "localhost"
        assert expanded["database"]["port"] == "5432"
        assert expanded["database"]["url"] == "localhost:5432"
    
    def test_expand_config_variables_with_defaults(self, monkeypatch):
        """Test variable expansion with default values."""
        monkeypatch.setenv("EXISTING_VAR", "exists")
        
        config = {
            "value1": "${EXISTING_VAR}",
            "value2": "${MISSING_VAR:-default_value}",
            "value3": "${ANOTHER_MISSING:-another_default}"
        }
        
        expanded = expand_config_variables(config)
        
        assert expanded["value1"] == "exists"
        assert expanded["value2"] == "default_value"
        assert expanded["value3"] == "another_default"
    
    def test_expand_config_variables_required(self):
        """Test required variable expansion."""
        config = {
            "required": "${REQUIRED_VAR:?This variable is required}"
        }
        
        with pytest.raises(ValueError, match="This variable is required"):
            expand_config_variables(config)
    
    def test_merge_configs_deep(self):
        """Test deep merging of configurations."""
        config1 = {
            "resources": {
                "io_manager": {"config": {"base_dir": "/tmp"}},
                "db": {"config": {"host": "localhost"}}
            },
            "ops": {
                "op1": {"config": {"value": 1}}
            }
        }
        
        config2 = {
            "resources": {
                "io_manager": {"config": {"format": "parquet"}},
                "cache": {"config": {"ttl": 3600}}
            },
            "ops": {
                "op2": {"config": {"value": 2}}
            }
        }
        
        merged = merge_configs(config1, config2, strategy="deep")
        
        # Check deep merge
        assert merged["resources"]["io_manager"]["config"]["base_dir"] == "/tmp"
        assert merged["resources"]["io_manager"]["config"]["format"] == "parquet"
        assert merged["resources"]["db"]["config"]["host"] == "localhost"
        assert merged["resources"]["cache"]["config"]["ttl"] == 3600
        assert merged["ops"]["op1"]["config"]["value"] == 1
        assert merged["ops"]["op2"]["config"]["value"] == 2
    
    def test_merge_configs_shallow(self):
        """Test shallow merging of configurations."""
        config1 = {"a": {"b": 1, "c": 2}, "d": 3}
        config2 = {"a": {"b": 10, "e": 4}, "f": 5}
        
        merged = merge_configs(config1, config2, strategy="shallow")
        
        assert merged["a"] == {"b": 10, "e": 4}  # config2's 'a' replaces config1's
        assert merged["d"] == 3
        assert merged["f"] == 5
    
    def test_merge_configs_replace(self):
        """Test replace strategy for merging."""
        config1 = {"a": 1, "b": 2}
        config2 = {"c": 3, "d": 4}
        config3 = {}
        
        merged = merge_configs(config1, config2, config3, strategy="replace")
        
        assert merged == {"c": 3, "d": 4}  # Last non-empty config wins
    
    def test_get_default_config(self):
        """Test generation of default configuration."""
        config = get_default_config("test_job")
        
        assert "resources" in config
        assert "io_manager" in config["resources"]
        assert "/test_job" in config["resources"]["io_manager"]["config"]["base_dir"]
        
        assert "ops" in config
        assert config["ops"] == {}
        
        assert "execution" in config
        assert "loggers" in config
    
    def test_save_config_yaml(self, temp_dir):
        """Test saving configuration to YAML."""
        config = {"test": "config", "nested": {"value": 42}}
        
        file_path = save_config(config, temp_dir / "output.yaml")
        
        assert file_path.exists()
        
        # Load and verify
        with open(file_path) as f:
            loaded = yaml.safe_load(f)
        
        assert loaded == config
    
    def test_save_config_json(self, temp_dir):
        """Test saving configuration to JSON."""
        config = {"test": "config", "nested": {"value": 42}}
        
        file_path = save_config(config, temp_dir / "output.json", format="json")
        
        assert file_path.exists()
        
        # Load and verify
        with open(file_path) as f:
            loaded = json.load(f)
        
        assert loaded == config
    
    def test_save_config_create_dirs(self, temp_dir):
        """Test saving config with directory creation."""
        config = {"test": "config"}
        
        file_path = save_config(
            config,
            temp_dir / "nested" / "dirs" / "config.yaml",
            create_dirs=True
        )
        
        assert file_path.exists()
        assert file_path.parent.exists()
    
    def test_diff_configs(self):
        """Test configuration diffing."""
        config1 = {
            "resources": {
                "io_manager": {"config": {"base_dir": "/tmp"}},
                "db": {"config": {"host": "localhost"}}
            },
            "ops": {
                "op1": {"config": {"value": 1}},
                "op2": {"config": {"value": 2}}
            }
        }
        
        config2 = {
            "resources": {
                "io_manager": {"config": {"base_dir": "/data"}},  # Modified
                "cache": {"config": {"ttl": 3600}}  # Added
            },
            "ops": {
                "op1": {"config": {"value": 1}},  # Same
                # op2 removed
                "op3": {"config": {"value": 3}}  # Added
            }
        }
        
        diff = diff_configs(config1, config2)
        
        # Check added
        assert "resources.cache.config.ttl" in diff["added"]
        assert diff["added"]["resources.cache.config.ttl"] == 3600
        assert "ops.op3.config.value" in diff["added"]
        
        # Check removed
        assert "resources.db.config.host" in diff["removed"]
        assert "ops.op2.config.value" in diff["removed"]
        
        # Check modified
        assert "resources.io_manager.config.base_dir" in diff["modified"]
        assert diff["modified"]["resources.io_manager.config.base_dir"]["old"] == "/tmp"
        assert diff["modified"]["resources.io_manager.config.base_dir"]["new"] == "/data"
    
    def test_diff_configs_with_ignore_keys(self):
        """Test configuration diffing with ignored keys."""
        config1 = {"a": 1, "b": 2, "timestamp": "2024-01-01"}
        config2 = {"a": 2, "b": 2, "timestamp": "2024-01-02"}
        
        # Diff without ignoring
        diff1 = diff_configs(config1, config2)
        assert len(diff1["modified"]) == 2
        
        # Diff with ignoring timestamp
        diff2 = diff_configs(config1, config2, ignore_keys=["timestamp"])
        assert len(diff2["modified"]) == 1
        assert "a" in diff2["modified"]
        assert "timestamp" not in diff2["modified"]