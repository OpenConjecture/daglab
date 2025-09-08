# Security Guide for daglab

This guide covers security best practices and usage of the security/validation helpers in daglab.

## Overview

The daglab security module provides comprehensive protection against common security vulnerabilities:

- **Input Validation**: Sanitize and validate all user inputs
- **Path Traversal Prevention**: Prevent directory traversal attacks
- **Command Injection Prevention**: Safe command execution
- **YAML Security**: Prevent code execution via YAML
- **Safe File Operations**: Secure file reading/writing
- **Network Validation**: Validate endpoints and prevent SSRF

## Quick Start

```python
from daglab.helpers import (
    validate_yaml_content,
    validate_file_path,
    prevent_path_traversal,
    safe_file_read,
    safe_file_write,
    SecurityError,
    ValidationError
)
```

## Validation Module (`daglab.helpers.validation`)

### YAML Validation

Prevent code execution via YAML deserialization:

```python
# Safe YAML parsing
config = validate_yaml_content(yaml_string)

# With schema validation
schema = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "port": {"type": "integer"}
    }
}
config = validate_yaml_content(yaml_string, schema=schema)
```

**Blocked patterns:**
- `!!python/` tags
- `!!subprocess`
- `!!import`
- `!!eval`
- `!!exec`

### File Path Validation

```python
# Basic validation
safe_path = validate_file_path(user_input)

# With restrictions
safe_path = validate_file_path(
    user_input,
    base_dir="/app/data",  # Restrict to directory
    allowed_extensions=['.yaml', '.json'],
    must_exist=True
)
```

**Security checks:**
- Null byte detection
- Path traversal prevention
- Dangerous character detection
- Extension validation

### Network Endpoint Validation

```python
# Validate URLs
endpoint = validate_network_endpoint("https://api.example.com")

# Restrict schemes and ports
endpoint = validate_network_endpoint(
    user_input,
    allowed_schemes=['https'],
    allowed_ports=[443, 8443],
    allow_localhost=False
)
```

**Features:**
- Scheme validation
- Port range checking
- Localhost/private IP blocking
- Hostname validation

### Configuration Validation

```python
# Validate Dagster configuration
config = validate_dagster_config(dagster_dict)

# Validate Marimo configuration
config = validate_marimo_config(marimo_dict)
```

## Security Module (`daglab.helpers.security`)

### Input Sanitization

```python
# Context-aware sanitization
safe_input = sanitize_input(user_input, context="general")
safe_filename = sanitize_input(filename, context="filename")
safe_command = sanitize_input(cmd, context="command")
safe_sql = sanitize_input(query, context="sql")  # Use parameters instead!
```

### Path Traversal Prevention

```python
# Ensure path is within base directory
safe_path = prevent_path_traversal(
    user_path,
    base_dir="/app/data",
    follow_symlinks=False  # Prevent symlink attacks
)
```

### Command Injection Prevention

```python
# Parse command safely
args = prevent_command_injection(
    user_command,
    allowed_commands=["ls", "grep", "cat"]
)

# Execute safely
result = run_command_safely(
    args,
    timeout=30,
    cwd="/app/data"
)
```

### Safe File Operations

```python
# Safe file reading
content = safe_file_read(
    file_path,
    base_dir="/app/data",
    max_size=10 * 1024 * 1024  # 10MB limit
)

# Safe file writing (atomic)
path = safe_file_write(
    file_path,
    content,
    base_dir="/app/data",
    overwrite=False,
    mode=0o644
)

# Secure temporary files
with safe_temp_file(suffix=".yaml") as temp_path:
    temp_path.write_text(data)
    # File is securely deleted after context
```

### Password Security

```python
# Hash passwords securely
hash_hex, salt = hash_password(password)

# Verify passwords (constant-time)
is_valid = verify_password(password, hash_hex, salt)

# Generate secure tokens
token = generate_secure_token(length=32)
```

## Security Best Practices

### 1. Input Validation

Always validate and sanitize user inputs:

```python
def process_user_file(filename, content):
    # Sanitize filename
    safe_name = sanitize_input(filename, context="filename")
    
    # Validate content
    try:
        config = validate_yaml_content(content)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}")
    
    # Safe file operations
    file_path = Path("/app/data") / safe_name
    safe_file_write(file_path, content, base_dir="/app/data")
```

### 2. Path Security

Never trust user-provided paths:

```python
def read_user_file(user_path):
    BASE_DIR = Path("/app/user_files")
    
    # Prevent path traversal
    safe_path = prevent_path_traversal(user_path, BASE_DIR)
    
    # Additional validation
    safe_path = validate_file_path(
        safe_path,
        allowed_extensions=['.txt', '.csv', '.json'],
        must_exist=True
    )
    
    return safe_file_read(safe_path, base_dir=BASE_DIR)
```

### 3. Command Execution

Never execute user input directly:

```python
def run_analysis(dataset_name):
    # Sanitize input
    safe_name = sanitize_input(dataset_name, context="filename")
    
    # Build command safely
    cmd = f"python analyze.py --dataset {safe_name}"
    args = prevent_command_injection(
        cmd,
        allowed_commands=["python"]
    )
    
    # Execute with restrictions
    result = run_command_safely(
        args,
        timeout=300,  # 5 minute timeout
        cwd="/app/scripts"
    )
```

### 4. Configuration Security

Validate all configuration:

```python
def load_dagster_config(config_path):
    # Validate path
    safe_path = validate_file_path(
        config_path,
        base_dir="/app/configs",
        allowed_extensions=['.yaml', '.yml'],
        must_exist=True
    )
    
    # Read safely
    content = safe_file_read(safe_path)
    
    # Parse and validate
    config = validate_yaml_content(content)
    return validate_dagster_config(config)
```

## Common Attack Scenarios

### Path Traversal

```python
# Attack attempt
user_input = "../../../etc/passwd"

# Prevention
try:
    safe_path = prevent_path_traversal(user_input, "/app/data")
except SecurityError:
    # Attack blocked
    pass
```

### Command Injection

```python
# Attack attempt
user_input = "file.txt; rm -rf /"

# Prevention
try:
    args = prevent_command_injection(f"cat {user_input}")
except SecurityError:
    # Attack blocked
    pass
```

### YAML Code Execution

```python
# Attack attempt
yaml_content = """
!!python/object/apply:os.system ['whoami']
"""

# Prevention
try:
    config = validate_yaml_content(yaml_content)
except ValidationError:
    # Attack blocked
    pass
```

### SQL Injection

```python
# Attack attempt
user_input = "'; DROP TABLE users; --"

# Prevention (basic)
try:
    safe_input = sanitize_input(user_input, context="sql")
except SecurityError:
    # Attack blocked
    pass

# Better: Use parameterized queries!
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

## Testing Security

Run security tests:

```bash
pytest tests/test_security.py -v
pytest tests/test_validation.py -v
```

## Security Checklist

- [ ] All user inputs are validated and sanitized
- [ ] File paths are restricted to allowed directories
- [ ] YAML parsing uses safe_load only
- [ ] Commands are parsed and whitelisted
- [ ] Network endpoints are validated
- [ ] Passwords are hashed with salt
- [ ] File operations use atomic writes
- [ ] Symlinks are handled safely
- [ ] Size limits are enforced
- [ ] Timeouts are set for operations
- [ ] Error messages don't leak information
- [ ] Logging doesn't include sensitive data

## Error Handling

Always handle security errors appropriately:

```python
from daglab.helpers import SecurityError, ValidationError

try:
    # Security-sensitive operation
    result = validate_file_path(user_input)
except ValidationError as e:
    # Log the attempt (not the input!)
    logger.warning("Invalid file path provided")
    # Return generic error to user
    return "Invalid input provided"
except SecurityError as e:
    # Log security event
    logger.error(f"Security violation: {e.__class__.__name__}")
    # Alert administrators
    send_security_alert(request_id)
    # Return generic error
    return "Access denied"
```

## Reporting Security Issues

If you discover a security vulnerability in daglab:

1. Do NOT open a public issue
2. Email security@example.com with details
3. Include steps to reproduce
4. Allow 90 days for patching

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)