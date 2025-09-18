"""Input validation helpers for security and data integrity."""

import ipaddress
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set, Union
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, ValidationError, validator

from daglab.runtime.errors import ValidationError as DaglabValidationError


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self, valid: bool = True, errors: Optional[List[str]] = None):
        self.valid = valid
        self.errors = errors or []
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.valid = False
        self.errors.append(error)
    
    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        if not other.valid:
            self.valid = False
            self.errors.extend(other.errors)
    
    def raise_if_invalid(self) -> None:
        """Raise ValidationError if validation failed."""
        if not self.valid:
            raise DaglabValidationError(
                "Validation failed",
                context=ErrorContext(details={'errors': self.errors})
            )


class PathValidator:
    """Validate file paths for security."""
    
    FORBIDDEN_PATTERNS = [
        r'\.\.',  # Directory traversal
        r'^/',    # Absolute paths (unless allowed)
        r'^~',    # Home directory expansion
        r'[<>"|?*]',  # Invalid characters
        r'\\',    # Backslash (Windows paths)
    ]
    
    FORBIDDEN_NAMES = {
        'con', 'prn', 'aux', 'nul',  # Windows reserved
        'com1', 'com2', 'com3', 'com4',
        'lpt1', 'lpt2', 'lpt3', 'lpt4',
    }
    
    @classmethod
    def validate_path(
        cls,
        path: Union[str, Path],
        base_dir: Optional[Path] = None,
        allow_absolute: bool = False,
        allow_symlinks: bool = False,
        must_exist: bool = False,
        file_type: Optional[str] = None  # 'file', 'dir', None for any
    ) -> ValidationResult:
        """Validate a file path for security and correctness."""
        result = ValidationResult()
        
        try:
            path = Path(path)
        except Exception as e:
            result.add_error(f"Invalid path format: {e}")
            return result
        
        # Check for forbidden patterns
        path_str = str(path)
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, path_str):
                if pattern == r'^/' and allow_absolute:
                    continue
                result.add_error(f"Path contains forbidden pattern: {pattern}")
        
        # Check for forbidden names
        for part in path.parts:
            if part.lower() in cls.FORBIDDEN_NAMES:
                result.add_error(f"Path contains forbidden name: {part}")
        
        # Check if absolute when not allowed
        if path.is_absolute() and not allow_absolute:
            result.add_error("Absolute paths are not allowed")
        
        # Resolve path safely
        if base_dir:
            try:
                # Ensure path stays within base_dir
                base_dir = Path(base_dir).resolve()
                full_path = (base_dir / path).resolve()
                
                if not str(full_path).startswith(str(base_dir)):
                    result.add_error("Path traversal detected")
            except Exception as e:
                result.add_error(f"Path resolution error: {e}")
        
        # Check symlinks
        if not allow_symlinks and path.exists() and path.is_symlink():
            result.add_error("Symbolic links are not allowed")
        
        # Check existence
        if must_exist and not path.exists():
            result.add_error(f"Path does not exist: {path}")
        
        # Check file type
        if file_type and path.exists():
            if file_type == 'file' and not path.is_file():
                result.add_error(f"Path is not a file: {path}")
            elif file_type == 'dir' and not path.is_dir():
                result.add_error(f"Path is not a directory: {path}")
        
        return result


class NetworkValidator:
    """Validate network endpoints and URLs."""
    
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),
        ipaddress.ip_network('::1/128'),
    ]
    
    FORBIDDEN_SCHEMES = {'file', 'ftp', 'telnet'}
    ALLOWED_SCHEMES = {'http', 'https', 'grpc', 'grpcs'}
    
    @classmethod
    def validate_url(
        cls,
        url: str,
        allowed_schemes: Optional[Set[str]] = None,
        allow_private_ips: bool = False,
        allow_ports: Optional[Set[int]] = None,
        require_https: bool = False
    ) -> ValidationResult:
        """Validate a URL for security and correctness."""
        result = ValidationResult()
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            result.add_error(f"Invalid URL format: {e}")
            return result
        
        # Check scheme
        if parsed.scheme in cls.FORBIDDEN_SCHEMES:
            result.add_error(f"Forbidden URL scheme: {parsed.scheme}")
        
        allowed = allowed_schemes or cls.ALLOWED_SCHEMES
        if parsed.scheme not in allowed:
            result.add_error(f"URL scheme not allowed: {parsed.scheme}")
        
        if require_https and parsed.scheme != 'https':
            result.add_error("HTTPS is required")
        
        # Check hostname
        if not parsed.hostname:
            result.add_error("URL must have a hostname")
            return result
        
        # Check for private IPs
        if not allow_private_ips:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                for network in cls.PRIVATE_IP_RANGES:
                    if ip in network:
                        result.add_error(f"Private IP addresses not allowed: {ip}")
                        break
            except ValueError:
                # Not an IP address, probably a domain name
                pass
        
        # Check port
        if parsed.port and allow_ports is not None:
            if parsed.port not in allow_ports:
                result.add_error(f"Port not allowed: {parsed.port}")
        
        return result


class YAMLValidator:
    """Validate YAML configuration files."""
    
    @staticmethod
    def validate_yaml_file(
        file_path: Union[str, Path],
        schema: Optional[Dict[str, Any]] = None,
        safe_load: bool = True
    ) -> ValidationResult:
        """Validate a YAML file."""
        result = ValidationResult()
        
        # First validate the path
        path_result = PathValidator.validate_path(
            file_path,
            must_exist=True,
            file_type='file'
        )
        result.merge(path_result)
        
        if not result.valid:
            return result
        
        try:
            with open(file_path, 'r') as f:
                if safe_load:
                    data = yaml.safe_load(f)
                else:
                    data = yaml.load(f, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            result.add_error(f"YAML parsing error: {e}")
            return result
        except Exception as e:
            result.add_error(f"File reading error: {e}")
            return result
        
        # Validate against schema if provided
        if schema:
            schema_result = YAMLValidator.validate_against_schema(data, schema)
            result.merge(schema_result)
        
        return result
    
    @staticmethod
    def validate_against_schema(
        data: Any,
        schema: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against a schema definition."""
        result = ValidationResult()
        
        # This is a simple implementation. In production, you might want to use
        # a library like jsonschema or cerberus for more comprehensive validation
        
        if not isinstance(data, dict):
            result.add_error("Data must be a dictionary")
            return result
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                result.add_error(f"Missing required field: {field}")
        
        # Check field types
        properties = schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                field_schema = properties[field]
                expected_type = field_schema.get('type')
                
                if expected_type:
                    type_map = {
                        'string': str,
                        'integer': int,
                        'number': (int, float),
                        'boolean': bool,
                        'array': list,
                        'object': dict
                    }
                    
                    expected_python_type = type_map.get(expected_type)
                    if expected_python_type and not isinstance(value, expected_python_type):
                        result.add_error(
                            f"Field '{field}' has wrong type. "
                            f"Expected {expected_type}, got {type(value).__name__}"
                        )
        
        # Check for unknown fields
        if schema.get('additionalProperties') is False:
            allowed_fields = set(properties.keys())
            for field in data:
                if field not in allowed_fields:
                    result.add_error(f"Unknown field: {field}")
        
        return result


class InputSanitizer:
    """Sanitize user input for security."""
    
    # Patterns that might indicate injection attempts
    DANGEROUS_PATTERNS = [
        r'[;&|`$]',  # Shell metacharacters
        r'<script',   # XSS attempts
        r'javascript:', # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'on\w+\s*=',  # Event handlers
        r'--',         # SQL comment
        r'union\s+select',  # SQL injection
        r'exec\s*\(',  # Python exec
        r'eval\s*\(',  # Eval functions
        r'__\w+__',    # Python magic methods
    ]
    
    @classmethod
    def sanitize_string(
        cls,
        value: str,
        max_length: Optional[int] = None,
        allowed_chars: Optional[Pattern] = None,
        strip_html: bool = True
    ) -> str:
        """Sanitize a string value."""
        if not isinstance(value, str):
            raise TypeError(f"Expected string, got {type(value)}")
        
        # Truncate if too long
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        # Strip HTML tags if requested
        if strip_html:
            value = re.sub(r'<[^>]+>', '', value)
        
        # Check against dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                # Remove the dangerous content
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Filter allowed characters
        if allowed_chars:
            value = ''.join(c for c in value if allowed_chars.match(c))
        
        return value.strip()
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize a filename for safe use."""
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure not empty
        if not filename:
            filename = 'unnamed'
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            if ext:
                name = name[:250 - len(ext)]
                filename = f"{name}.{ext}"
            else:
                filename = filename[:255]
        
        return filename


# Pydantic models for common validation scenarios
class ConfigModel(BaseModel):
    """Base model for configuration validation."""
    
    class Config:
        extra = 'forbid'  # No extra fields allowed
        validate_assignment = True


class DaglabConfigModel(ConfigModel):
    """Example configuration model for Daglab settings."""
    
    environment: str = Field(..., pattern='^(development|staging|production)$')
    log_level: str = Field('INFO', pattern='^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')
    max_workers: int = Field(4, ge=1, le=100)
    timeout: float = Field(300.0, gt=0)
    base_path: Optional[Path] = None
    
    @validator('base_path')
    def validate_base_path(cls, v: Optional[Path]) -> Optional[Path]:
        if v is not None:
            result = PathValidator.validate_path(v, file_type='dir')
            if not result.valid:
                raise ValueError(f"Invalid base path: {', '.join(result.errors)}")
        return v


# Helper functions
def validate_email(email: str) -> bool:
    """Validate an email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_semantic_version(version: str) -> bool:
    """Validate semantic version string."""
    pattern = r'^\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$'
    return bool(re.match(pattern, version))


from daglab.runtime.errors import ErrorContext