"""Security validation for GraphQL queries and configurations.

This module provides comprehensive validation for:
- GraphQL query sanitization
- Configuration validation against schemas
- Asset selection validation
- Run configuration security checks
- SQL injection prevention for state management
- Authentication token validation
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path
import yaml
from datetime import datetime, timedelta

from ..helpers.auth import AuthConfig, AuthType

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Main security validator for Daglab operations."""
    
    # Dangerous SQL patterns
    SQL_INJECTION_PATTERNS = [
        r"(union|select|insert|update|delete|drop|create|alter|exec|script)\s+",
        r"(--|#|/\*|\*/|;)",
        r"(char|nchar|varchar|nvarchar)\s*\(",
        r"(exec|execute|xp_|sp_)\s*\(",
        r"(cast|convert)\s*\(",
    ]
    
    # GraphQL injection patterns
    GRAPHQL_INJECTION_PATTERNS = [
        r"__schema",
        r"__type",
        r"mutation\s*{[^}]*delete",
        r"mutation\s*{[^}]*drop",
        r"fragment\s+[^{]+on\s+__",
    ]
    
    # Allowed GraphQL operations
    ALLOWED_OPERATIONS = {
        "query": ["repositories", "jobs", "runs", "assets", "schedules", "sensors"],
        "mutation": ["launchPipelineExecution", "terminatePipelineExecution", "reloadRepository"],
        "subscription": ["pipelineRunLogs"]
    }
    
    # Maximum sizes
    MAX_QUERY_SIZE = 50000  # 50KB
    MAX_CONFIG_SIZE = 100000  # 100KB
    MAX_TAG_COUNT = 50
    MAX_TAG_KEY_LENGTH = 100
    MAX_TAG_VALUE_LENGTH = 500
    
    def __init__(self, strict_mode: bool = True):
        """Initialize security validator.
        
        Args:
            strict_mode: If True, apply stricter validation rules
        """
        self.strict_mode = strict_mode
        self._compiled_patterns = {
            "sql": [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS],
            "graphql": [re.compile(p, re.IGNORECASE) for p in self.GRAPHQL_INJECTION_PATTERNS]
        }
    
    def validate_graphql_query(self, query: str, operation_type: str = "query") -> tuple[bool, Optional[str]]:
        """Validate GraphQL query for security issues.
        
        Args:
            query: GraphQL query string
            operation_type: Type of operation (query, mutation, subscription)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"
        
        # Check size
        if len(query) > self.MAX_QUERY_SIZE:
            return False, f"Query exceeds maximum size of {self.MAX_QUERY_SIZE} bytes"
        
        # Check for GraphQL injection patterns
        for pattern in self._compiled_patterns["graphql"]:
            if pattern.search(query):
                return False, f"Potentially dangerous GraphQL pattern detected"
        
        # In strict mode, validate operation whitelist
        if self.strict_mode:
            # Extract operation names
            operation_pattern = rf"{operation_type}\s+(\w+)"
            matches = re.findall(operation_pattern, query, re.IGNORECASE)
            
            if not matches:
                return False, f"No valid {operation_type} operation found"
            
            # Check if operations are allowed
            allowed = self.ALLOWED_OPERATIONS.get(operation_type, [])
            for op_name in matches:
                if not any(op_name.startswith(allowed_op) for allowed_op in allowed):
                    return False, f"Operation '{op_name}' is not allowed"
        
        return True, None
    
    def validate_run_config(self, config: Union[str, Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """Validate run configuration for security issues.
        
        Args:
            config: Run configuration (JSON string or dict)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Parse config if string
        if isinstance(config, str):
            try:
                if config.strip().startswith("{"):
                    config_dict = json.loads(config)
                else:
                    config_dict = yaml.safe_load(config)
            except (json.JSONDecodeError, yaml.YAMLError) as e:
                return False, f"Invalid configuration format: {str(e)}"
        else:
            config_dict = config
        
        # Check size
        config_str = json.dumps(config_dict)
        if len(config_str) > self.MAX_CONFIG_SIZE:
            return False, f"Configuration exceeds maximum size of {self.MAX_CONFIG_SIZE} bytes"
        
        # Validate structure
        if not isinstance(config_dict, dict):
            return False, "Configuration must be a dictionary"
        
        # Check for dangerous patterns in values
        def check_value(value: Any, path: str = "") -> Optional[str]:
            if isinstance(value, str):
                # Check for SQL injection
                for pattern in self._compiled_patterns["sql"]:
                    if pattern.search(value):
                        return f"Potentially dangerous SQL pattern in {path}"
                
                # Check for path traversal
                if ".." in value or value.startswith("/etc/") or value.startswith("/proc/"):
                    return f"Potentially dangerous path in {path}"
                
                # Check for command injection
                if any(char in value for char in [";", "|", "&", "`", "$("]):
                    return f"Potentially dangerous command characters in {path}"
                    
            elif isinstance(value, dict):
                for k, v in value.items():
                    error = check_value(v, f"{path}.{k}" if path else k)
                    if error:
                        return error
                        
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    error = check_value(item, f"{path}[{i}]")
                    if error:
                        return error
            
            return None
        
        error = check_value(config_dict)
        if error:
            return False, error
        
        return True, None
    
    def validate_asset_selection(self, assets: List[str]) -> tuple[bool, Optional[str]]:
        """Validate asset selection list.
        
        Args:
            assets: List of asset names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(assets, list):
            return False, "Asset selection must be a list"
        
        if len(assets) > 1000:
            return False, "Too many assets selected (max 1000)"
        
        for asset in assets:
            if not isinstance(asset, str):
                return False, "All asset names must be strings"
            
            if not asset:
                return False, "Asset names cannot be empty"
            
            # Check for valid asset name pattern
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", asset):
                return False, f"Invalid asset name: {asset}"
            
            if len(asset) > 200:
                return False, f"Asset name too long: {asset}"
        
        return True, None
    
    def validate_tags(self, tags: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate run tags.
        
        Args:
            tags: Dictionary of tags
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(tags, dict):
            return False, "Tags must be a dictionary"
        
        if len(tags) > self.MAX_TAG_COUNT:
            return False, f"Too many tags (max {self.MAX_TAG_COUNT})"
        
        for key, value in tags.items():
            if not isinstance(key, str):
                return False, "Tag keys must be strings"
            
            if len(key) > self.MAX_TAG_KEY_LENGTH:
                return False, f"Tag key too long: {key}"
            
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", key):
                return False, f"Invalid tag key: {key}"
            
            # Convert value to string for validation
            value_str = str(value)
            if len(value_str) > self.MAX_TAG_VALUE_LENGTH:
                return False, f"Tag value too long for key: {key}"
        
        return True, None
    
    def validate_sql_query(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate SQL query for state management.
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"
        
        # Check for SQL injection patterns
        for pattern in self._compiled_patterns["sql"]:
            if pattern.search(query):
                return False, "Potentially dangerous SQL pattern detected"
        
        # In strict mode, only allow SELECT queries
        if self.strict_mode:
            query_lower = query.strip().lower()
            if not query_lower.startswith("select"):
                return False, "Only SELECT queries are allowed in strict mode"
        
        return True, None
    
    def validate_auth_token(self, token: str, auth_type: AuthType) -> tuple[bool, Optional[str]]:
        """Validate authentication token format and structure.
        
        Args:
            token: Authentication token
            auth_type: Type of authentication
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token or not isinstance(token, str):
            return False, "Token must be a non-empty string"
        
        if auth_type == AuthType.BEARER:
            # Check for common JWT structure (header.payload.signature)
            parts = token.split(".")
            if len(parts) == 3:
                # Basic JWT validation
                try:
                    import base64
                    for part in parts[:2]:  # Don't decode signature
                        # Add padding if needed
                        padding = 4 - len(part) % 4
                        if padding != 4:
                            part += "=" * padding
                        base64.urlsafe_b64decode(part)
                except Exception:
                    return False, "Invalid JWT token format"
            elif len(token) < 20:
                return False, "Bearer token too short"
            elif len(token) > 4096:
                return False, "Bearer token too long"
        
        elif auth_type == AuthType.BASIC:
            # Basic auth should be base64 encoded username:password
            try:
                import base64
                decoded = base64.b64decode(token).decode("utf-8")
                if ":" not in decoded:
                    return False, "Invalid basic auth format"
            except Exception:
                return False, "Invalid basic auth encoding"
        
        return True, None
    
    def sanitize_string(self, value: str, max_length: int = 1000) -> str:
        """Sanitize string value for safe usage.
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove null bytes
        value = value.replace("\x00", "")
        
        # Escape special characters for SQL
        value = value.replace("'", "''")
        
        return value
    
    def validate_file_path(self, path: Union[str, Path]) -> tuple[bool, Optional[str]]:
        """Validate file path for security issues.
        
        Args:
            path: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path_obj = Path(path)
            
            # Check for path traversal
            if ".." in str(path_obj):
                return False, "Path traversal detected"
            
            # Check for absolute paths to sensitive directories
            sensitive_dirs = ["/etc", "/proc", "/sys", "/dev", "/boot"]
            for sensitive in sensitive_dirs:
                if str(path_obj).startswith(sensitive):
                    return False, f"Access to {sensitive} is not allowed"
            
            # Resolve path to check if it escapes allowed directories
            try:
                resolved = path_obj.resolve()
                # Add additional checks based on your allowed directories
            except Exception:
                # Path doesn't exist yet, that's okay
                pass
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"


class ConfigValidator:
    """Validator for Dagster configuration against schemas."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """Initialize config validator.
        
        Args:
            schema_dir: Directory containing configuration schemas
        """
        self.schema_dir = schema_dir or Path(__file__).parent / "schemas"
        self._schemas: Dict[str, Dict] = {}
    
    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """Load configuration schema.
        
        Args:
            schema_name: Name of the schema to load
            
        Returns:
            Schema dictionary
        """
        if schema_name in self._schemas:
            return self._schemas[schema_name]
        
        schema_path = self.schema_dir / f"{schema_name}.yaml"
        if not schema_path.exists():
            schema_path = self.schema_dir / f"{schema_name}.json"
        
        if not schema_path.exists():
            raise ValueError(f"Schema not found: {schema_name}")
        
        with open(schema_path, "r") as f:
            if schema_path.suffix == ".yaml":
                schema = yaml.safe_load(f)
            else:
                schema = json.load(f)
        
        self._schemas[schema_name] = schema
        return schema
    
    def validate_against_schema(
        self, 
        config: Dict[str, Any], 
        schema_name: str
    ) -> tuple[bool, Optional[List[str]]]:
        """Validate configuration against a schema.
        
        Args:
            config: Configuration dictionary
            schema_name: Name of schema to validate against
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            schema = self.load_schema(schema_name)
            errors = []
            
            # Simple validation implementation
            # In production, use jsonschema or similar library
            def validate_value(value: Any, schema_part: Dict, path: str = "") -> None:
                val_type = schema_part.get("type")
                
                if val_type == "object" and isinstance(value, dict):
                    # Check required fields
                    required = schema_part.get("required", [])
                    for req in required:
                        if req not in value:
                            errors.append(f"{path}.{req} is required")
                    
                    # Validate properties
                    properties = schema_part.get("properties", {})
                    for key, val in value.items():
                        if key in properties:
                            validate_value(
                                val, 
                                properties[key], 
                                f"{path}.{key}" if path else key
                            )
                        elif not schema_part.get("additionalProperties", True):
                            errors.append(f"Unknown property: {path}.{key}")
                
                elif val_type == "array" and isinstance(value, list):
                    items_schema = schema_part.get("items", {})
                    for i, item in enumerate(value):
                        validate_value(item, items_schema, f"{path}[{i}]")
                
                elif val_type:
                    # Type validation
                    type_map = {
                        "string": str,
                        "number": (int, float),
                        "integer": int,
                        "boolean": bool,
                        "null": type(None)
                    }
                    expected_type = type_map.get(val_type)
                    if expected_type and not isinstance(value, expected_type):
                        errors.append(
                            f"{path} must be of type {val_type}, got {type(value).__name__}"
                        )
            
            validate_value(config, schema)
            
            return len(errors) == 0, errors if errors else None
            
        except Exception as e:
            return False, [f"Schema validation error: {str(e)}"]


# Convenience functions
_default_validator = SecurityValidator()
_default_config_validator = ConfigValidator()

def validate_graphql_query(query: str, operation_type: str = "query") -> tuple[bool, Optional[str]]:
    """Validate GraphQL query using default validator."""
    return _default_validator.validate_graphql_query(query, operation_type)

def validate_run_config(config: Union[str, Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """Validate run configuration using default validator."""
    return _default_validator.validate_run_config(config)

def validate_asset_selection(assets: List[str]) -> tuple[bool, Optional[str]]:
    """Validate asset selection using default validator."""
    return _default_validator.validate_asset_selection(assets)

def validate_tags(tags: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate tags using default validator."""
    return _default_validator.validate_tags(tags)

def validate_auth_token(token: str, auth_type: AuthType) -> tuple[bool, Optional[str]]:
    """Validate authentication token using default validator."""
    return _default_validator.validate_auth_token(token, auth_type)

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string using default validator."""
    return _default_validator.sanitize_string(value, max_length)