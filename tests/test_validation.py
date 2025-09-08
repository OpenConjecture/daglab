"""Tests for validation utilities."""

import pytest
from pathlib import Path
import tempfile
import os

from daglab.helpers.validation import (
    validate_yaml_content,
    validate_file_path,
    validate_network_endpoint,
    validate_dagster_config,
    validate_marimo_config,
    sanitize_input,
    ValidationError
)


class TestYAMLValidation:
    """Test YAML validation functions."""
    
    def test_valid_yaml(self):
        """Test valid YAML content."""
        yaml_content = """
        name: test
        version: 1.0
        items:
          - item1
          - item2
        """
        result = validate_yaml_content(yaml_content)
        assert result['name'] == 'test'
        assert result['version'] == 1.0
        assert len(result['items']) == 2
    
    def test_empty_yaml(self):
        """Test empty YAML content."""
        with pytest.raises(ValidationError):
            validate_yaml_content("")
    
    def test_invalid_yaml(self):
        """Test invalid YAML syntax."""
        yaml_content = """
        name: test
        items:
          - item1
         - item2  # Invalid indentation
        """
        with pytest.raises(ValidationError):
            validate_yaml_content(yaml_content)
    
    def test_dangerous_yaml_patterns(self):
        """Test detection of dangerous YAML patterns."""
        dangerous_patterns = [
            "!!python/object/apply:os.system ['ls']",
            "!!python/name:os.system",
            "!!subprocess/Popen ['ls']",
            "!!import os",
            "!!eval 'print(\"hello\")'",
            "!!exec 'import os; os.system(\"ls\")'",
        ]
        
        for pattern in dangerous_patterns:
            with pytest.raises(ValidationError, match="dangerous YAML pattern"):
                validate_yaml_content(pattern)
    
    def test_yaml_with_schema(self):
        """Test YAML validation with schema."""
        yaml_content = """
        name: test
        age: 25
        active: true
        """
        
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"}
            }
        }
        
        result = validate_yaml_content(yaml_content, schema)
        assert result['name'] == 'test'
        assert result['age'] == 25
        assert result['active'] is True
    
    def test_yaml_schema_validation_failure(self):
        """Test YAML schema validation failure."""
        yaml_content = """
        name: test
        age: "not a number"
        """
        
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"}
            }
        }
        
        with pytest.raises(ValidationError, match="Expected integer"):
            validate_yaml_content(yaml_content, schema)


class TestFilePathValidation:
    """Test file path validation functions."""
    
    def test_valid_path(self):
        """Test valid file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            result = validate_file_path(str(test_file), must_exist=True)
            assert result == test_file.resolve()
    
    def test_empty_path(self):
        """Test empty file path."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_file_path("")
    
    def test_null_byte_in_path(self):
        """Test null byte in path."""
        with pytest.raises(ValidationError, match="null bytes"):
            validate_file_path("test\x00file.txt")
    
    def test_path_traversal(self):
        """Test path traversal prevention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValidationError, match="outside allowed directory"):
                validate_file_path("../../../etc/passwd", base_dir=tmpdir)
    
    def test_allowed_extensions(self):
        """Test file extension validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_file = Path(tmpdir) / "test.yaml"
            valid_file.write_text("test")
            
            result = validate_file_path(
                str(valid_file),
                allowed_extensions=['.yaml', '.yml'],
                must_exist=True
            )
            assert result == valid_file.resolve()
            
            invalid_file = Path(tmpdir) / "test.exe"
            invalid_file.write_text("test")
            
            with pytest.raises(ValidationError, match="extension not allowed"):
                validate_file_path(
                    str(invalid_file),
                    allowed_extensions=['.yaml', '.yml'],
                    must_exist=True
                )
    
    def test_dangerous_path_components(self):
        """Test detection of dangerous path components."""
        dangerous_paths = [
            "test; rm -rf /",
            "test | cat /etc/passwd",
            "test > /dev/null",
            "test < /etc/passwd",
            "test & echo hacked",
            "test`whoami`",
            "test$(whoami)",
        ]
        
        for path in dangerous_paths:
            with pytest.raises(ValidationError, match="dangerous component"):
                validate_file_path(path)


class TestNetworkEndpointValidation:
    """Test network endpoint validation."""
    
    def test_valid_urls(self):
        """Test valid URL endpoints."""
        valid_urls = [
            "http://example.com",
            "https://example.com:8080",
            "https://api.example.com/v1",
            "http://192.168.1.1:3000",
        ]
        
        for url in valid_urls:
            result = validate_network_endpoint(url)
            assert result == url
    
    def test_valid_host_port(self):
        """Test valid host:port format."""
        valid_endpoints = [
            "localhost:8080",
            "example.com:443",
            "192.168.1.1:3000",
        ]
        
        for endpoint in valid_endpoints:
            result = validate_network_endpoint(endpoint)
            assert result == endpoint
    
    def test_invalid_schemes(self):
        """Test invalid URL schemes."""
        with pytest.raises(ValidationError, match="scheme"):
            validate_network_endpoint("ftp://example.com", allowed_schemes=['http', 'https'])
    
    def test_invalid_ports(self):
        """Test invalid port numbers."""
        invalid_ports = [
            "example.com:0",
            "example.com:65536",
            "example.com:abc",
        ]
        
        for endpoint in invalid_ports:
            with pytest.raises(ValidationError):
                validate_network_endpoint(endpoint)
    
    def test_localhost_restriction(self):
        """Test localhost restriction."""
        localhost_endpoints = [
            "http://localhost",
            "http://127.0.0.1",
            "http://::1",
            "http://0.0.0.0",
        ]
        
        for endpoint in localhost_endpoints:
            with pytest.raises(ValidationError, match="Localhost"):
                validate_network_endpoint(endpoint, allow_localhost=False)
    
    def test_port_restriction(self):
        """Test port restriction."""
        with pytest.raises(ValidationError, match="not allowed"):
            validate_network_endpoint("example.com:22", allowed_ports=[80, 443, 8080])


class TestDagsterConfigValidation:
    """Test Dagster configuration validation."""
    
    def test_valid_dagster_config(self):
        """Test valid Dagster configuration."""
        config = {
            "ops": {
                "my_op": {
                    "config": {"param": "value"}
                }
            },
            "resources": {
                "my_resource": {
                    "config": {"connection": "postgresql://localhost"}
                }
            }
        }
        
        result = validate_dagster_config(config)
        assert result == config
    
    def test_invalid_op_names(self):
        """Test invalid op names."""
        config = {
            "ops": {
                "my-op": {},  # Hyphens not allowed
                "123op": {},  # Can't start with number
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid op name"):
            validate_dagster_config(config)
    
    def test_dangerous_resource_config(self):
        """Test detection of dangerous resource configurations."""
        dangerous_configs = [
            {"resources": {"res": {"config": {"command": "rm -rf /"}}}},
            {"resources": {"res": {"config": {"shell": "/bin/bash"}}}},
            {"resources": {"res": {"config": {"executable": "/usr/bin/python"}}}},
            {"resources": {"res": {"config": {"script": "malicious.py"}}}},
        ]
        
        for config in dangerous_configs:
            with pytest.raises(ValidationError, match="dangerous configuration key"):
                validate_dagster_config(config)


class TestMarimoConfigValidation:
    """Test Marimo configuration validation."""
    
    def test_valid_marimo_config(self):
        """Test valid Marimo configuration."""
        config = {
            "notebooks": {
                "my_notebook": {
                    "path": "notebooks/test.py"
                }
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000
            },
            "plugins": ["matplotlib", "numpy"]
        }
        
        result = validate_marimo_config(config)
        assert result == config
    
    def test_invalid_notebook_path(self):
        """Test invalid notebook path validation."""
        config = {
            "notebooks": {
                "my_notebook": {
                    "path": "../../../etc/passwd"
                }
            }
        }
        
        with pytest.raises(ValidationError):
            validate_marimo_config(config)
    
    def test_invalid_server_port(self):
        """Test invalid server port."""
        config = {
            "server": {
                "port": 99999
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid server port"):
            validate_marimo_config(config)
    
    def test_suspicious_plugin_names(self):
        """Test detection of suspicious plugin names."""
        config = {
            "plugins": [
                "../../evil_plugin",
                "plugin; rm -rf /",
                "$HOME/plugin",
            ]
        }
        
        with pytest.raises(ValidationError, match="Suspicious plugin name"):
            validate_marimo_config(config)


class TestInputSanitization:
    """Test input sanitization."""
    
    def test_basic_sanitization(self):
        """Test basic input sanitization."""
        result = sanitize_input("  Hello World  ")
        assert result == "Hello World"
    
    def test_length_limit(self):
        """Test input length limit."""
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            sanitize_input("x" * 1000, max_length=100)
    
    def test_html_stripping(self):
        """Test HTML tag stripping."""
        result = sanitize_input("<script>alert('xss')</script>Hello", strip_html=True)
        assert result == "Hello"
    
    def test_allowed_chars(self):
        """Test allowed character validation."""
        result = sanitize_input("abc123", allowed_chars=r'^[a-zA-Z0-9]+$')
        assert result == "abc123"
        
        with pytest.raises(ValidationError, match="invalid characters"):
            sanitize_input("abc@123", allowed_chars=r'^[a-zA-Z0-9]+$')
    
    def test_control_char_removal(self):
        """Test control character removal."""
        result = sanitize_input("Hello\x00\x01\x02World\nTest")
        assert result == "HelloWorld\nTest"