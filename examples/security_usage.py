"""Example usage of security and validation helpers."""

from pathlib import Path
import yaml

from daglab.helpers import (
    # Validation functions
    validate_yaml_content,
    validate_file_path,
    validate_network_endpoint,
    validate_dagster_config,
    validate_marimo_config,
    # Security functions
    sanitize_input,
    prevent_path_traversal,
    prevent_command_injection,
    safe_file_read,
    safe_file_write,
    SecurityError,
    ValidationError
)


def example_yaml_validation():
    """Example of YAML validation with security checks."""
    print("=== YAML Validation Example ===")
    
    # Safe YAML content
    safe_yaml = """
    dagster:
      ops:
        extract_data:
          config:
            source: "database"
            table: "users"
      resources:
        postgres:
          config:
            host: "localhost"
            port: 5432
    """
    
    try:
        config = validate_yaml_content(safe_yaml)
        print(f"✓ Valid YAML parsed: {list(config.keys())}")
    except ValidationError as e:
        print(f"✗ Validation error: {e}")
    
    # Dangerous YAML content
    dangerous_yaml = """
    !!python/object/apply:os.system ['rm -rf /']
    """
    
    try:
        config = validate_yaml_content(dangerous_yaml)
        print("✗ Dangerous YAML was not detected!")
    except ValidationError as e:
        print(f"✓ Dangerous YAML blocked: {e}")


def example_path_validation():
    """Example of path validation and traversal prevention."""
    print("\n=== Path Validation Example ===")
    
    # Set up a safe base directory
    base_dir = Path.cwd() / "data"
    base_dir.mkdir(exist_ok=True)
    
    # Valid paths
    valid_paths = [
        "data/input.csv",
        "data/notebooks/analysis.py",
        "./data/config.yaml",
    ]
    
    for path_str in valid_paths:
        try:
            safe_path = validate_file_path(path_str, base_dir=base_dir.parent)
            print(f"✓ Valid path: {path_str} -> {safe_path}")
        except ValidationError as e:
            print(f"✗ Invalid path {path_str}: {e}")
    
    # Path traversal attempts
    dangerous_paths = [
        "../../../etc/passwd",
        "data/../../secrets.txt",
        "/etc/shadow",
        "data/file;rm -rf /",
    ]
    
    for path_str in dangerous_paths:
        try:
            safe_path = prevent_path_traversal(path_str, base_dir)
            print(f"✗ Path traversal not blocked: {path_str}")
        except (ValidationError, SecurityError) as e:
            print(f"✓ Path traversal blocked: {path_str}")


def example_network_validation():
    """Example of network endpoint validation."""
    print("\n=== Network Endpoint Validation Example ===")
    
    # Valid endpoints
    valid_endpoints = [
        "https://api.example.com",
        "http://localhost:8080",
        "dagster-webserver:3000",
    ]
    
    for endpoint in valid_endpoints:
        try:
            validated = validate_network_endpoint(endpoint)
            print(f"✓ Valid endpoint: {validated}")
        except ValidationError as e:
            print(f"✗ Invalid endpoint {endpoint}: {e}")
    
    # Restrict localhost
    try:
        validate_network_endpoint("http://localhost:8080", allow_localhost=False)
        print("✗ Localhost was not blocked when restricted")
    except ValidationError:
        print("✓ Localhost blocked when restricted")


def example_command_injection_prevention():
    """Example of command injection prevention."""
    print("\n=== Command Injection Prevention Example ===")
    
    # Safe commands
    safe_commands = [
        "ls -la",
        "grep pattern file.txt",
        "echo 'Hello World'",
    ]
    
    for cmd in safe_commands:
        try:
            args = prevent_command_injection(cmd, allowed_commands=["ls", "grep", "echo"])
            print(f"✓ Safe command parsed: {cmd} -> {args}")
        except SecurityError as e:
            print(f"✗ Command blocked: {cmd}: {e}")
    
    # Dangerous commands
    dangerous_commands = [
        "ls; rm -rf /",
        "echo hello && cat /etc/passwd",
        "grep pattern `whoami`",
        "python -c 'import os; os.system(\"id\")'",
    ]
    
    for cmd in dangerous_commands:
        try:
            args = prevent_command_injection(cmd)
            print(f"✗ Dangerous command not blocked: {cmd}")
        except SecurityError:
            print(f"✓ Command injection blocked: {cmd}")


def example_safe_file_operations():
    """Example of safe file operations."""
    print("\n=== Safe File Operations Example ===")
    
    # Create a safe working directory
    work_dir = Path.cwd() / "safe_workspace"
    work_dir.mkdir(exist_ok=True)
    
    # Safe file write
    try:
        config_content = """
        # Safe configuration
        database:
          host: localhost
          port: 5432
        """
        
        config_file = safe_file_write(
            work_dir / "config.yaml",
            config_content,
            base_dir=work_dir,
            overwrite=True
        )
        print(f"✓ File written safely: {config_file}")
        
        # Safe file read
        content = safe_file_read(config_file, base_dir=work_dir)
        print(f"✓ File read safely: {len(content)} bytes")
        
    except SecurityError as e:
        print(f"✗ File operation error: {e}")
    
    # Attempt to read outside base directory
    try:
        content = safe_file_read("/etc/passwd", base_dir=work_dir)
        print("✗ Path traversal in read not blocked!")
    except SecurityError:
        print("✓ Path traversal in file read blocked")


def example_input_sanitization():
    """Example of input sanitization."""
    print("\n=== Input Sanitization Example ===")
    
    # Different sanitization contexts
    examples = [
        ("Hello World", "general"),
        ("../../../etc/passwd", "filename"),
        ("echo 'test'", "command"),
        ("SELECT * FROM users", "sql"),
    ]
    
    for input_text, context in examples:
        try:
            sanitized = sanitize_input(input_text, context=context)
            print(f"✓ Sanitized ({context}): '{input_text}' -> '{sanitized}'")
        except SecurityError as e:
            print(f"✗ Sanitization failed ({context}): {e}")
    
    # Dangerous inputs
    dangerous_inputs = [
        ("file\x00.txt", "general"),  # Null byte
        ("'; DROP TABLE users; --", "sql"),  # SQL injection
        ("<script>alert('xss')</script>", "general"),  # XSS attempt
    ]
    
    for input_text, context in dangerous_inputs:
        try:
            sanitized = sanitize_input(input_text, context=context, max_length=100)
            if context == "general":
                print(f"✓ Dangerous content sanitized: '{sanitized}'")
            else:
                print(f"✗ Dangerous input not blocked: {input_text}")
        except (SecurityError, ValidationError):
            print(f"✓ Dangerous input blocked: {input_text}")


def example_dagster_config_validation():
    """Example of Dagster configuration validation."""
    print("\n=== Dagster Config Validation Example ===")
    
    # Valid Dagster config
    valid_config = {
        "ops": {
            "extract_data": {
                "config": {
                    "table_name": "users",
                    "batch_size": 1000
                }
            },
            "transform_data": {
                "config": {
                    "operations": ["normalize", "deduplicate"]
                }
            }
        },
        "resources": {
            "postgres": {
                "config": {
                    "host": "localhost",
                    "database": "dagster"
                }
            }
        }
    }
    
    try:
        validated = validate_dagster_config(valid_config)
        print("✓ Valid Dagster configuration")
    except ValidationError as e:
        print(f"✗ Invalid Dagster config: {e}")
    
    # Invalid config with dangerous resource
    dangerous_config = {
        "resources": {
            "shell": {
                "config": {
                    "command": "rm -rf /",  # Dangerous!
                    "shell": "/bin/bash"
                }
            }
        }
    }
    
    try:
        validated = validate_dagster_config(dangerous_config)
        print("✗ Dangerous Dagster config not blocked!")
    except ValidationError:
        print("✓ Dangerous Dagster config blocked")


def main():
    """Run all examples."""
    example_yaml_validation()
    example_path_validation()
    example_network_validation()
    example_command_injection_prevention()
    example_safe_file_operations()
    example_input_sanitization()
    example_dagster_config_validation()
    
    print("\n=== Security Examples Complete ===")
    print("These examples demonstrate secure coding practices for:")
    print("- YAML parsing without code execution")
    print("- Path validation and traversal prevention")
    print("- Network endpoint validation")
    print("- Command injection prevention")
    print("- Safe file operations")
    print("- Input sanitization")
    print("- Configuration validation")


if __name__ == "__main__":
    main()