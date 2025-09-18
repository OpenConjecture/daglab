"""Tests for the validation module."""

import re
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest
import yaml
from pydantic import ValidationError as PydanticValidationError

from daglab.helpers.validation import (
    ConfigModel,
    DaglabConfigModel,
    InputSanitizer,
    NetworkValidator,
    PathValidator,
    ValidationResult,
    YAMLValidator,
    validate_email,
    validate_semantic_version,
)
from daglab.runtime.errors import ValidationError as DaglabValidationError


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_initialization(self):
        """Test ValidationResult initialization."""
        result = ValidationResult()
        assert result.valid is True
        assert result.errors == []
        
        result = ValidationResult(valid=False, errors=["Error 1"])
        assert result.valid is False
        assert result.errors == ["Error 1"]
    
    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult()
        assert result.valid is True
        
        result.add_error("Test error")
        assert result.valid is False
        assert "Test error" in result.errors
        
        result.add_error("Another error")
        assert len(result.errors) == 2
    
    def test_merge(self):
        """Test merging results."""
        result1 = ValidationResult()
        result1.add_error("Error 1")
        
        result2 = ValidationResult()
        result2.add_error("Error 2")
        result2.add_error("Error 3")
        
        result1.merge(result2)
        assert len(result1.errors) == 3
        assert "Error 1" in result1.errors
        assert "Error 2" in result1.errors
        assert "Error 3" in result1.errors
    
    def test_raise_if_invalid(self):
        """Test raising exception on invalid."""
        result = ValidationResult()
        result.raise_if_invalid()  # Should not raise
        
        result.add_error("Test error")
        with pytest.raises(DaglabValidationError) as exc_info:
            result.raise_if_invalid()
        
        assert "Validation failed" in str(exc_info.value)


class TestPathValidator:
    """Test PathValidator class."""
    
    def test_validate_simple_path(self):
        """Test validating simple paths."""
        result = PathValidator.validate_path("test.txt")
        assert result.valid is True
        
        result = PathValidator.validate_path("subdir/file.txt")
        assert result.valid is True
    
    def test_forbidden_patterns(self):
        """Test detection of forbidden patterns."""
        # Directory traversal
        result = PathValidator.validate_path("../etc/passwd")
        assert result.valid is False
        assert any("forbidden pattern" in e for e in result.errors)
        
        # Absolute path when not allowed
        result = PathValidator.validate_path("/etc/passwd")
        assert result.valid is False
        
        # Invalid characters
        result = PathValidator.validate_path("file<name>.txt")
        assert result.valid is False
    
    def test_forbidden_names(self):
        """Test detection of forbidden names."""
        result = PathValidator.validate_path("con.txt")
        assert result.valid is False
        assert any("forbidden name" in e for e in result.errors)
        
        result = PathValidator.validate_path("subdir/nul")
        assert result.valid is False
    
    def test_allow_absolute_paths(self):
        """Test allowing absolute paths."""
        result = PathValidator.validate_path("/usr/local/bin", allow_absolute=True)
        assert result.valid is True
    
    def test_symlink_detection(self, tmp_path):
        """Test symlink detection."""
        # Create a regular file and a symlink
        regular_file = tmp_path / "regular.txt"
        regular_file.write_text("content")
        
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(regular_file)
        
        # Test without allowing symlinks
        result = PathValidator.validate_path(symlink, allow_symlinks=False)
        assert result.valid is False
        assert any("Symbolic links are not allowed" in e for e in result.errors)
        
        # Test with allowing symlinks
        result = PathValidator.validate_path(symlink, allow_symlinks=True)
        assert result.valid is True
    
    def test_must_exist(self, tmp_path):
        """Test must_exist validation."""
        existing = tmp_path / "exists.txt"
        existing.write_text("content")
        
        result = PathValidator.validate_path(existing, must_exist=True)
        assert result.valid is True
        
        result = PathValidator.validate_path(tmp_path / "nonexistent.txt", must_exist=True)
        assert result.valid is False
        assert any("does not exist" in e for e in result.errors)
    
    def test_file_type_validation(self, tmp_path):
        """Test file type validation."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        
        # Test file validation
        result = PathValidator.validate_path(file_path, file_type='file')
        assert result.valid is True
        
        result = PathValidator.validate_path(dir_path, file_type='file')
        assert result.valid is False
        assert any("not a file" in e for e in result.errors)
        
        # Test directory validation
        result = PathValidator.validate_path(dir_path, file_type='dir')
        assert result.valid is True
        
        result = PathValidator.validate_path(file_path, file_type='dir')
        assert result.valid is False
        assert any("not a directory" in e for e in result.errors)
    
    def test_base_dir_containment(self, tmp_path):
        """Test that paths stay within base_dir."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        
        # Valid path within base_dir
        result = PathValidator.validate_path("subdir/file.txt", base_dir=base_dir)
        assert result.valid is True
        
        # Path traversal attempt
        result = PathValidator.validate_path("../outside.txt", base_dir=base_dir)
        assert result.valid is False
        assert any("Path traversal detected" in e for e in result.errors)


class TestNetworkValidator:
    """Test NetworkValidator class."""
    
    def test_validate_url_basic(self):
        """Test basic URL validation."""
        result = NetworkValidator.validate_url("https://example.com")
        assert result.valid is True
        
        result = NetworkValidator.validate_url("http://localhost:8080/path")
        assert result.valid is True
    
    def test_forbidden_schemes(self):
        """Test forbidden URL schemes."""
        result = NetworkValidator.validate_url("file:///etc/passwd")
        assert result.valid is False
        assert any("Forbidden URL scheme" in e for e in result.errors)
        
        result = NetworkValidator.validate_url("ftp://example.com")
        assert result.valid is False
    
    def test_allowed_schemes(self):
        """Test custom allowed schemes."""
        result = NetworkValidator.validate_url(
            "custom://example.com",
            allowed_schemes={'custom'}
        )
        assert result.valid is True
    
    def test_require_https(self):
        """Test requiring HTTPS."""
        result = NetworkValidator.validate_url(
            "http://example.com",
            require_https=True
        )
        assert result.valid is False
        assert any("HTTPS is required" in e for e in result.errors)
        
        result = NetworkValidator.validate_url(
            "https://example.com",
            require_https=True
        )
        assert result.valid is True
    
    def test_private_ip_detection(self):
        """Test private IP detection."""
        private_urls = [
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
            "http://127.0.0.1",
            "http://[::1]",
        ]
        
        for url in private_urls:
            result = NetworkValidator.validate_url(url, allow_private_ips=False)
            assert result.valid is False
            assert any("Private IP addresses not allowed" in e for e in result.errors)
        
        # Test allowing private IPs
        for url in private_urls:
            result = NetworkValidator.validate_url(url, allow_private_ips=True)
            assert result.valid is True
    
    def test_port_validation(self):
        """Test port validation."""
        result = NetworkValidator.validate_url(
            "https://example.com:443",
            allow_ports={443, 8443}
        )
        assert result.valid is True
        
        result = NetworkValidator.validate_url(
            "https://example.com:9999",
            allow_ports={443, 8443}
        )
        assert result.valid is False
        assert any("Port not allowed" in e for e in result.errors)
    
    def test_missing_hostname(self):
        """Test URL without hostname."""
        result = NetworkValidator.validate_url("https://")
        assert result.valid is False
        assert any("must have a hostname" in e for e in result.errors)


class TestYAMLValidator:
    """Test YAMLValidator class."""
    
    def test_validate_yaml_file(self, tmp_path):
        """Test YAML file validation."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("""
        name: test
        version: 1.0
        settings:
          debug: true
        """)
        
        result = YAMLValidator.validate_yaml_file(yaml_file)
        assert result.valid is True
    
    def test_invalid_yaml(self, tmp_path):
        """Test invalid YAML syntax."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("""
        name: test
        version: 1.0
        invalid: [
        """)
        
        result = YAMLValidator.validate_yaml_file(yaml_file)
        assert result.valid is False
        assert any("YAML parsing error" in e for e in result.errors)
    
    def test_yaml_schema_validation(self, tmp_path):
        """Test YAML schema validation."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""
        name: myapp
        port: 8080
        """)
        
        schema = {
            'required': ['name', 'version'],
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'},
                'port': {'type': 'integer'}
            }
        }
        
        result = YAMLValidator.validate_yaml_file(yaml_file, schema=schema)
        assert result.valid is False
        assert any("Missing required field: version" in e for e in result.errors)
    
    def test_schema_type_validation(self, tmp_path):
        """Test schema type validation."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""
        port: "8080"
        enabled: yes
        """)
        
        schema = {
            'properties': {
                'port': {'type': 'integer'},
                'enabled': {'type': 'boolean'}
            }
        }
        
        result = YAMLValidator.validate_yaml_file(yaml_file, schema=schema)
        assert result.valid is False
        assert any("wrong type" in e and "port" in e for e in result.errors)
    
    def test_additional_properties(self, tmp_path):
        """Test additional properties validation."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""
        allowed: true
        extra: false
        """)
        
        schema = {
            'properties': {
                'allowed': {'type': 'boolean'}
            },
            'additionalProperties': False
        }
        
        result = YAMLValidator.validate_yaml_file(yaml_file, schema=schema)
        assert result.valid is False
        assert any("Unknown field: extra" in e for e in result.errors)


class TestInputSanitizer:
    """Test InputSanitizer class."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = InputSanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
        
        result = InputSanitizer.sanitize_string("  spaces  ")
        assert result == "spaces"
    
    def test_max_length(self):
        """Test max length truncation."""
        result = InputSanitizer.sanitize_string("x" * 100, max_length=10)
        assert len(result) == 10
    
    def test_strip_html(self):
        """Test HTML stripping."""
        result = InputSanitizer.sanitize_string(
            "<script>alert('xss')</script>Hello",
            strip_html=True
        )
        assert result == "Hello"
        assert "<script>" not in result
        assert "alert" not in result
    
    def test_dangerous_patterns(self):
        """Test removal of dangerous patterns."""
        dangerous_inputs = [
            "command; rm -rf /",
            "value'; DROP TABLE users; --",
            "javascript:alert(1)",
            "onclick=alert(1)",
            "__import__('os').system('cmd')",
            "exec('malicious code')",
            "eval(dangerous_code)"
        ]
        
        for dangerous in dangerous_inputs:
            result = InputSanitizer.sanitize_string(dangerous)
            # Check that dangerous patterns are removed
            assert ";" not in result or "rm -rf" not in result
            assert "DROP TABLE" not in result
            assert "javascript:" not in result
            assert "onclick=" not in result
            assert "__import__" not in result
            assert "exec(" not in result
            assert "eval(" not in result
    
    def test_allowed_chars(self):
        """Test character filtering."""
        allowed = re.compile(r'[a-zA-Z0-9\s]')
        result = InputSanitizer.sanitize_string(
            "Hello@World#123!",
            allowed_chars=allowed
        )
        assert result == "HelloWorld123"
    
    def test_type_error(self):
        """Test type checking."""
        with pytest.raises(TypeError):
            InputSanitizer.sanitize_string(123)
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Path separators
        assert InputSanitizer.sanitize_filename("../../../etc/passwd") == "_.._.._.._etc_passwd"
        assert InputSanitizer.sanitize_filename("C:\\Windows\\System32") == "C__Windows_System32"
        
        # Dangerous characters
        assert InputSanitizer.sanitize_filename('file<name>.txt') == 'file_name_.txt'
        assert InputSanitizer.sanitize_filename('file:name?.txt') == 'file_name_.txt'
        
        # Leading/trailing dots and spaces
        assert InputSanitizer.sanitize_filename('  .hidden.  ') == 'hidden'
        assert InputSanitizer.sanitize_filename('...') == 'unnamed'
        
        # Empty filename
        assert InputSanitizer.sanitize_filename('') == 'unnamed'
        
        # Long filename
        long_name = 'a' * 300 + '.txt'
        result = InputSanitizer.sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith('.txt')


class TestPydanticModels:
    """Test Pydantic models."""
    
    def test_config_model(self):
        """Test ConfigModel base class."""
        class TestConfig(ConfigModel):
            name: str
            value: int
        
        # Valid config
        config = TestConfig(name="test", value=42)
        assert config.name == "test"
        assert config.value == 42
        
        # Extra fields forbidden
        with pytest.raises(PydanticValidationError):
            TestConfig(name="test", value=42, extra="field")
    
    def test_daglab_config_model(self):
        """Test DaglabConfigModel."""
        # Valid config
        config = DaglabConfigModel(
            environment="production",
            log_level="DEBUG",
            max_workers=10,
            timeout=600.0
        )
        assert config.environment == "production"
        assert config.max_workers == 10
        
        # Invalid environment
        with pytest.raises(PydanticValidationError):
            DaglabConfigModel(environment="invalid")
        
        # Invalid log level
        with pytest.raises(PydanticValidationError):
            DaglabConfigModel(environment="production", log_level="INVALID")
        
        # Workers out of range
        with pytest.raises(PydanticValidationError):
            DaglabConfigModel(environment="production", max_workers=200)
        
        # Negative timeout
        with pytest.raises(PydanticValidationError):
            DaglabConfigModel(environment="production", timeout=-1)
    
    def test_daglab_config_base_path(self, tmp_path):
        """Test base_path validation in DaglabConfigModel."""
        # Valid directory
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        
        config = DaglabConfigModel(
            environment="development",
            base_path=valid_dir
        )
        assert config.base_path == valid_dir
        
        # Invalid path (with forbidden patterns)
        with pytest.raises(PydanticValidationError):
            DaglabConfigModel(
                environment="development",
                base_path="../../../etc"
            )


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert validate_email("user@example.com") is True
        assert validate_email("user.name+tag@example.co.uk") is True
        assert validate_email("123@test.org") is True
        
        # Invalid emails
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False
        assert validate_email("user @example.com") is False
    
    def test_validate_semantic_version(self):
        """Test semantic version validation."""
        # Valid versions
        assert validate_semantic_version("1.0.0") is True
        assert validate_semantic_version("0.0.1") is True
        assert validate_semantic_version("10.20.30") is True
        assert validate_semantic_version("1.0.0-alpha") is True
        assert validate_semantic_version("1.0.0-alpha.1") is True
        assert validate_semantic_version("1.0.0+build123") is True
        assert validate_semantic_version("1.0.0-rc.1+build123") is True
        
        # Invalid versions
        assert validate_semantic_version("1.0") is False
        assert validate_semantic_version("1") is False
        assert validate_semantic_version("v1.0.0") is False
        assert validate_semantic_version("1.0.0.0") is False
        assert validate_semantic_version("a.b.c") is False