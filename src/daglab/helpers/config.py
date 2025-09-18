"""
Configuration helper functions for DagLab.

This module provides utilities for loading, validating, and managing
configurations for Dagster jobs and assets in notebooks.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from deepmerge import always_merger


def load_config_from_file(
    file_path: Union[str, Path],
    expand_vars: bool = True
) -> Dict[str, Any]:
    """
    Load configuration from a YAML or JSON file.
    
    Args:
        file_path: Path to configuration file
        expand_vars: Whether to expand environment variables
        
    Returns:
        Loaded configuration dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is unsupported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    # Read file content
    content = path.read_text()
    
    # Expand environment variables if requested
    if expand_vars:
        content = expand_config_variables({"raw": content})["raw"]
    
    # Parse based on extension
    ext = path.suffix.lower()
    
    if ext in [".yaml", ".yml"]:
        config = yaml.safe_load(content)
    elif ext == ".json":
        config = json.loads(content)
    else:
        raise ValueError(f"Unsupported config file format: {ext}")
    
    return config or {}


def validate_run_config(
    run_config: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Validate run configuration against a schema.
    
    Args:
        run_config: Configuration to validate
        schema: Schema to validate against (uses basic validation if None)
        strict: Whether to fail on extra keys
        
    Returns:
        Dict containing validation result and any errors
    """
    errors = []
    warnings = []
    
    # Basic validation if no schema
    if schema is None:
        # Check for common required sections
        common_sections = ["resources", "ops", "config"]
        
        for section in common_sections:
            if section in run_config and not isinstance(run_config[section], dict):
                errors.append(f"Section '{section}' must be a dictionary")
        
        # Validate resource configurations
        if "resources" in run_config:
            for name, config in run_config["resources"].items():
                if config is not None and not isinstance(config, dict):
                    errors.append(f"Resource '{name}' config must be a dictionary or null")
                
                if isinstance(config, dict) and "config" in config:
                    if not isinstance(config["config"], dict):
                        errors.append(f"Resource '{name}' config.config must be a dictionary")
        
        # Validate op configurations
        if "ops" in run_config:
            for op_name, op_config in run_config["ops"].items():
                if not isinstance(op_config, dict):
                    errors.append(f"Op '{op_name}' config must be a dictionary")
                
                if "config" in op_config and not isinstance(op_config["config"], dict):
                    errors.append(f"Op '{op_name}' config.config must be a dictionary")
    
    else:
        # Schema-based validation
        def validate_against_schema(data: Any, schema_node: Dict[str, Any], path: str = ""):
            """Recursively validate data against schema."""
            
            # Check type
            if "type" in schema_node:
                expected_type = schema_node["type"]
                python_type = {
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                    "object": dict,
                    "array": list
                }.get(expected_type)
                
                if python_type and not isinstance(data, python_type):
                    errors.append(f"{path}: Expected type '{expected_type}', got '{type(data).__name__}'")
                    return
            
            # Validate object properties
            if isinstance(data, dict) and "properties" in schema_node:
                schema_props = schema_node["properties"]
                
                # Check required properties
                if "required" in schema_node:
                    for req_prop in schema_node["required"]:
                        if req_prop not in data:
                            errors.append(f"{path}: Missing required property '{req_prop}'")
                
                # Validate each property
                for prop, value in data.items():
                    if prop in schema_props:
                        validate_against_schema(
                            value,
                            schema_props[prop],
                            f"{path}.{prop}" if path else prop
                        )
                    elif strict:
                        errors.append(f"{path}: Unknown property '{prop}'")
                    else:
                        warnings.append(f"{path}: Unknown property '{prop}'")
            
            # Validate array items
            elif isinstance(data, list) and "items" in schema_node:
                for i, item in enumerate(data):
                    validate_against_schema(
                        item,
                        schema_node["items"],
                        f"{path}[{i}]"
                    )
        
        validate_against_schema(run_config, schema)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def expand_config_variables(
    config: Dict[str, Any],
    env: Optional[Dict[str, str]] = None,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Expand environment variables in configuration values.
    
    Supports:
    - ${VAR_NAME} - environment variable
    - ${VAR_NAME:-default} - with default value
    - ${VAR_NAME:?error message} - required variable
    
    Args:
        config: Configuration dictionary
        env: Environment variables to use (defaults to os.environ)
        recursive: Whether to expand recursively
        
    Returns:
        Configuration with expanded variables
    """
    import re
    
    if env is None:
        env = os.environ
    
    # Pattern for variable substitution
    var_pattern = re.compile(r'\$\{([^}]+)\}')
    
    def expand_value(value: Any) -> Any:
        """Expand variables in a single value."""
        if isinstance(value, str):
            def replacer(match):
                var_expr = match.group(1)
                
                # Handle default values
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                    return env.get(var_name.strip(), default)
                
                # Handle required variables
                elif ":?" in var_expr:
                    var_name, error_msg = var_expr.split(":?", 1)
                    var_name = var_name.strip()
                    if var_name not in env:
                        raise ValueError(f"Required variable '{var_name}' not found: {error_msg}")
                    return env[var_name]
                
                # Simple variable
                else:
                    var_name = var_expr.strip()
                    if var_name not in env:
                        raise ValueError(f"Variable '{var_name}' not found in environment")
                    return env[var_name]
            
            return var_pattern.sub(replacer, value)
        
        elif isinstance(value, dict) and recursive:
            return {k: expand_value(v) for k, v in value.items()}
        
        elif isinstance(value, list) and recursive:
            return [expand_value(item) for item in value]
        
        else:
            return value
    
    return expand_value(config)


def merge_configs(
    *configs: Dict[str, Any],
    strategy: str = "deep"
) -> Dict[str, Any]:
    """
    Merge multiple configuration dictionaries.
    
    Args:
        *configs: Configuration dictionaries to merge
        strategy: Merge strategy ('deep', 'shallow', 'replace')
        
    Returns:
        Merged configuration
    """
    if not configs:
        return {}
    
    if len(configs) == 1:
        return configs[0].copy()
    
    if strategy == "shallow":
        # Simple update (last wins)
        result = {}
        for config in configs:
            result.update(config)
        return result
    
    elif strategy == "replace":
        # Return last non-empty config
        for config in reversed(configs):
            if config:
                return config.copy()
        return {}
    
    else:  # deep
        # Deep merge using deepmerge library
        result = {}
        for config in configs:
            result = always_merger.merge(result, config)
        return result


def get_default_config(
    job_name: str,
    include_resources: bool = True,
    include_ops: bool = True
) -> Dict[str, Any]:
    """
    Generate default configuration for a job.
    
    Args:
        job_name: Name of the job
        include_resources: Whether to include resource configs
        include_ops: Whether to include op configs
        
    Returns:
        Default configuration dictionary
    """
    config = {}
    
    # Add resource configurations
    if include_resources:
        config["resources"] = {
            "io_manager": {
                "config": {
                    "base_dir": f"/tmp/dagster/{job_name}"
                }
            }
        }
    
    # Add op configurations placeholder
    if include_ops:
        config["ops"] = {}
    
    # Add execution config
    config["execution"] = {
        "config": {
            "multiprocess": {
                "max_concurrent": 4
            }
        }
    }
    
    # Add loggers config
    config["loggers"] = {
        "console": {
            "config": {
                "log_level": "INFO"
            }
        }
    }
    
    return config


def save_config(
    config: Dict[str, Any],
    file_path: Union[str, Path],
    format: str = "auto",
    create_dirs: bool = True
) -> Path:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration to save
        file_path: Output file path
        format: File format ('yaml', 'json', 'auto')
        create_dirs: Whether to create parent directories
        
    Returns:
        Path to saved file
    """
    path = Path(file_path)
    
    # Create parent directories if requested
    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine format
    if format == "auto":
        ext = path.suffix.lower()
        if ext in [".yaml", ".yml"]:
            format = "yaml"
        elif ext == ".json":
            format = "json"
        else:
            format = "yaml"  # Default to YAML
    
    # Save based on format
    if format == "yaml":
        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    elif format == "json":
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    return path


def diff_configs(
    config1: Dict[str, Any],
    config2: Dict[str, Any],
    ignore_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Compare two configurations and return differences.
    
    Args:
        config1: First configuration
        config2: Second configuration
        ignore_keys: Keys to ignore in comparison
        
    Returns:
        Dict with 'added', 'removed', 'modified' keys
    """
    ignore_keys = set(ignore_keys or [])
    
    def get_all_paths(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Get all paths in a nested dict."""
        paths = {}
        
        for key, value in d.items():
            if key in ignore_keys:
                continue
                
            path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                paths.update(get_all_paths(value, path))
            else:
                paths[path] = value
        
        return paths
    
    paths1 = get_all_paths(config1)
    paths2 = get_all_paths(config2)
    
    keys1 = set(paths1.keys())
    keys2 = set(paths2.keys())
    
    return {
        "added": {k: paths2[k] for k in keys2 - keys1},
        "removed": {k: paths1[k] for k in keys1 - keys2},
        "modified": {
            k: {"old": paths1[k], "new": paths2[k]}
            for k in keys1 & keys2
            if paths1[k] != paths2[k]
        }
    }