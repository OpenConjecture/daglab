"""Validation utilities for daglab.

This module provides comprehensive validation functions for:
- Input sanitization
- YAML validation
- File path validation
- Network endpoint validation
- Dagster and Marimo configuration validation
"""

import os
import re
import yaml
import ipaddress
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_yaml_content(content: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate YAML content and optionally check against a schema.
    
    Args:
        content: YAML string to validate
        schema: Optional schema dictionary to validate against
        
    Returns:
        Parsed YAML as dictionary
        
    Raises:
        ValidationError: If YAML is invalid or doesn't match schema
    """
    if not content or not isinstance(content, str):
        raise ValidationError("YAML content must be a non-empty string")
    
    # Check for common YAML injection patterns
    dangerous_patterns = [
        r'!!python/',  # Python object serialization
        r'!!subprocess',  # Subprocess execution
        r'!!import',  # Import statements
        r'!!eval',  # Eval expressions
        r'!!exec',  # Exec statements
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            raise ValidationError(f"Potentially dangerous YAML pattern detected: {pattern}")
    
    try:
        # Use safe_load to prevent arbitrary code execution
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValidationError(f"Invalid YAML content: {str(e)}")
    
    if schema:
        _validate_against_schema(data, schema)
    
    return data


def _validate_against_schema(data: Any, schema: Dict[str, Any], path: str = "") -> None:
    """Recursively validate data against a schema.
    
    Args:
        data: Data to validate
        schema: Schema to validate against
        path: Current path in the data structure (for error messages)
    """
    if "type" in schema:
        expected_type = schema["type"]
        if expected_type == "string" and not isinstance(data, str):
            raise ValidationError(f"Expected string at {path}, got {type(data).__name__}")
        elif expected_type == "integer" and not isinstance(data, int):
            raise ValidationError(f"Expected integer at {path}, got {type(data).__name__}")
        elif expected_type == "number" and not isinstance(data, (int, float)):
            raise ValidationError(f"Expected number at {path}, got {type(data).__name__}")
        elif expected_type == "boolean" and not isinstance(data, bool):
            raise ValidationError(f"Expected boolean at {path}, got {type(data).__name__}")
        elif expected_type == "array" and not isinstance(data, list):
            raise ValidationError(f"Expected array at {path}, got {type(data).__name__}")
        elif expected_type == "object" and not isinstance(data, dict):
            raise ValidationError(f"Expected object at {path}, got {type(data).__name__}")
    
    if "required" in schema and isinstance(data, dict):
        for required_field in schema["required"]:
            if required_field not in data:
                raise ValidationError(f"Missing required field: {path}.{required_field}")
    
    if "properties" in schema and isinstance(data, dict):
        for key, value in data.items():
            if key in schema["properties"]:
                _validate_against_schema(value, schema["properties"][key], f"{path}.{key}")


def validate_file_path(path: Union[str, Path], 
                      base_dir: Optional[Union[str, Path]] = None,
                      allowed_extensions: Optional[List[str]] = None,
                      must_exist: bool = False) -> Path:
    """Validate a file path for security and correctness.
    
    Args:
        path: File path to validate
        base_dir: Base directory to restrict paths to (prevents traversal)
        allowed_extensions: List of allowed file extensions (e.g., ['.yaml', '.yml'])
        must_exist: Whether the file must already exist
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid or insecure
    """
    if not path:
        raise ValidationError("File path cannot be empty")
    
    # Check for null bytes (common injection technique) - check before Path creation
    if '\x00' in str(path):
        raise ValidationError("File path contains null bytes")
    
    try:
        path_obj = Path(path).resolve()
    except (ValueError, OSError) as e:
        raise ValidationError(f"Invalid file path: {str(e)}")
    
    # Check if path is within base directory (prevent traversal)
    if base_dir:
        base_path = Path(base_dir).resolve()
        try:
            path_obj.relative_to(base_path)
        except ValueError:
            raise ValidationError(f"Path '{path}' is outside allowed directory '{base_dir}'")
    
    # Check file extension
    if allowed_extensions:
        if not any(str(path_obj).endswith(ext) for ext in allowed_extensions):
            raise ValidationError(f"File extension not allowed. Allowed: {allowed_extensions}")
    
    # Check if file exists (if required)
    if must_exist and not path_obj.exists():
        raise ValidationError(f"File does not exist: {path}")
    
    # Check for dangerous path components
    dangerous_components = ['..', '~', '$', '`', '|', '>', '<', '&', ';']
    path_str = str(path_obj)
    for component in dangerous_components:
        if component in path_str:
            raise ValidationError(f"Path contains dangerous component: {component}")
    
    return path_obj


def validate_network_endpoint(endpoint: str, 
                            allowed_schemes: Optional[List[str]] = None,
                            allowed_ports: Optional[List[int]] = None,
                            allow_localhost: bool = True) -> str:
    """Validate a network endpoint (URL, host:port, etc.).
    
    Args:
        endpoint: Network endpoint to validate
        allowed_schemes: Allowed URL schemes (default: ['http', 'https'])
        allowed_ports: Allowed ports (default: any)
        allow_localhost: Whether to allow localhost/127.0.0.1
        
    Returns:
        Validated endpoint string
        
    Raises:
        ValidationError: If endpoint is invalid or insecure
    """
    if not endpoint or not isinstance(endpoint, str):
        raise ValidationError("Endpoint must be a non-empty string")
    
    # Set defaults
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Try to parse as URL
    parsed = urlparse(endpoint)
    
    # Check if it has a scheme
    if parsed.scheme:
        # It's a URL
        if parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme '{parsed.scheme}' not allowed. Allowed: {allowed_schemes}")
        host = parsed.hostname
        port = parsed.port
    else:
        # No scheme, try to parse as host:port
        if ':' in endpoint and not endpoint.startswith('['):
            # Simple host:port format
            parts = endpoint.rsplit(':', 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                raise ValidationError(f"Invalid port number: {parts[1]}")
        else:
            # Just a hostname or IP
            host = endpoint
            port = None
    
    # Validate host
    if not host:
        raise ValidationError("No host specified in endpoint")
    
    # Check for localhost
    if not allow_localhost:
        localhost_patterns = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
        if host and any(pattern == host.lower() for pattern in localhost_patterns):
            raise ValidationError("Localhost connections are not allowed")
    
    # Try to validate as IP address
    try:
        ip = ipaddress.ip_address(host)
        # Check for private/reserved IP ranges
        if ip.is_private or ip.is_reserved or ip.is_multicast:
            if not allow_localhost:
                raise ValidationError(f"Private/reserved IP addresses not allowed: {host}")
    except ValueError:
        # Not an IP address, validate as hostname
        # Check for valid hostname pattern
        hostname_pattern = re.compile(
            r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$'
        )
        if not hostname_pattern.match(host):
            raise ValidationError(f"Invalid hostname: {host}")
    
    # Validate port
    if port is not None:
        if port < 1 or port > 65535:
            raise ValidationError(f"Invalid port number: {port}")
        if allowed_ports and port not in allowed_ports:
            raise ValidationError(f"Port {port} not allowed. Allowed ports: {allowed_ports}")
    
    return endpoint


def validate_dagster_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Dagster-specific configuration.
    
    Args:
        config: Dagster configuration dictionary
        
    Returns:
        Validated configuration
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError("Dagster config must be a dictionary")
    
    # Define Dagster config schema
    dagster_schema = {
        "type": "object",
        "properties": {
            "ops": {"type": "object"},
            "resources": {"type": "object"},
            "loggers": {"type": "object"},
            "executor": {"type": "object"},
            "storage": {"type": "object"},
            "run_launcher": {"type": "object"},
            "telemetry": {"type": "object"}
        }
    }
    
    _validate_against_schema(config, dagster_schema)
    
    # Additional Dagster-specific validations
    if "ops" in config:
        for op_name, op_config in config["ops"].items():
            if not isinstance(op_name, str) or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', op_name):
                raise ValidationError(f"Invalid op name: {op_name}")
            if not isinstance(op_config, dict):
                raise ValidationError(f"Op config for '{op_name}' must be a dictionary")
    
    # Validate resources
    if "resources" in config:
        for resource_name, resource_config in config["resources"].items():
            if not isinstance(resource_name, str):
                raise ValidationError(f"Resource name must be a string: {resource_name}")
            if not isinstance(resource_config, dict):
                raise ValidationError(f"Resource config for '{resource_name}' must be a dictionary")
            
            # Check for dangerous resource configurations
            if "config" in resource_config and isinstance(resource_config["config"], dict):
                dangerous_keys = ["command", "shell", "executable", "script"]
                for key in dangerous_keys:
                    if key in resource_config["config"]:
                        raise ValidationError(f"Potentially dangerous configuration key '{key}' in resource '{resource_name}'")
    
    return config


def validate_marimo_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Marimo-specific configuration.
    
    Args:
        config: Marimo configuration dictionary
        
    Returns:
        Validated configuration
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError("Marimo config must be a dictionary")
    
    # Define Marimo config schema
    marimo_schema = {
        "type": "object",
        "properties": {
            "notebooks": {"type": "object"},
            "server": {"type": "object"},
            "runtime": {"type": "object"},
            "plugins": {"type": "array"},
            "dependencies": {"type": "array"}
        }
    }
    
    _validate_against_schema(config, marimo_schema)
    
    # Validate notebooks
    if "notebooks" in config:
        for notebook_name, notebook_config in config["notebooks"].items():
            if not isinstance(notebook_name, str):
                raise ValidationError(f"Notebook name must be a string: {notebook_name}")
            if not isinstance(notebook_config, dict):
                raise ValidationError(f"Notebook config for '{notebook_name}' must be a dictionary")
            
            # Validate notebook path if present
            if "path" in notebook_config:
                validate_file_path(
                    notebook_config["path"],
                    allowed_extensions=['.py', '.marimo', '.md'],
                    must_exist=False
                )
    
    # Validate server configuration
    if "server" in config:
        server_config = config["server"]
        if "host" in server_config:
            host = server_config['host']
            port = server_config.get('port', 8000)
            validate_network_endpoint(f"{host}:{port}")
        if "port" in server_config:
            port = server_config["port"]
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ValidationError(f"Invalid server port: {port}")
    
    # Validate plugins
    if "plugins" in config:
        for plugin in config["plugins"]:
            if not isinstance(plugin, str):
                raise ValidationError(f"Plugin name must be a string: {plugin}")
            # Check for suspicious plugin names
            if any(char in plugin for char in ['/', '\\', '..', '~', '$']):
                raise ValidationError(f"Suspicious plugin name: {plugin}")
    
    return config


def sanitize_input(value: str, 
                  max_length: Optional[int] = None,
                  allowed_chars: Optional[str] = None,
                  strip_html: bool = True) -> str:
    """Sanitize user input for general use.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allowed_chars: Regex pattern of allowed characters
        strip_html: Whether to strip HTML tags
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(value, str):
        raise ValidationError("Input must be a string")
    
    # Strip leading/trailing whitespace
    value = value.strip()
    
    # Check length
    if max_length and len(value) > max_length:
        raise ValidationError(f"Input exceeds maximum length of {max_length}")
    
    # Strip HTML if requested
    if strip_html:
        # Simple HTML tag removal - handle script tags specially
        # Remove script tags and their content
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        # Remove remaining HTML tags
        value = re.sub(r'<[^>]+>', '', value)
    
    # Check allowed characters
    if allowed_chars:
        pattern = re.compile(allowed_chars)
        if not pattern.match(value):
            raise ValidationError(f"Input contains invalid characters. Allowed pattern: {allowed_chars}")
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove control characters (except newline and tab)
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t')
    
    return value