"""Security utilities for daglab.

This module provides security functions for:
- Input sanitization
- Path traversal prevention
- Command injection prevention
- Safe file operations
- Security-focused utilities
"""

import os
import re
import shlex
import hashlib
import secrets
from pathlib import Path
from typing import Any, List, Optional, Union, Callable
import subprocess
import tempfile
from contextlib import contextmanager


class SecurityError(Exception):
    """Custom exception for security violations."""
    pass


def sanitize_input(text: str, 
                  context: str = "general",
                  max_length: int = 10000,
                  encoding: str = "utf-8") -> str:
    """Sanitize input based on context with security focus.
    
    Args:
        text: Input text to sanitize
        context: Context for sanitization ('general', 'filename', 'command', 'sql')
        max_length: Maximum allowed length
        encoding: Expected text encoding
        
    Returns:
        Sanitized string
        
    Raises:
        SecurityError: If input contains dangerous content
    """
    if not isinstance(text, str):
        raise SecurityError("Input must be a string")
    
    # Enforce length limit
    if len(text) > max_length:
        raise SecurityError(f"Input exceeds maximum length of {max_length}")
    
    # Try to decode/encode to catch encoding attacks
    try:
        text = text.encode(encoding, errors='strict').decode(encoding, errors='strict')
    except UnicodeError:
        raise SecurityError("Input contains invalid encoding")
    
    # Remove null bytes (common attack vector)
    if '\x00' in text:
        # For general context, we can strip null bytes instead of failing
        if context == "general":
            text = text.replace('\x00', '')
        else:
            raise SecurityError("Input contains null bytes")
    
    # Context-specific sanitization
    if context == "filename":
        # Filename sanitization
        return _sanitize_filename(text)
    elif context == "command":
        # Command sanitization
        return _sanitize_command(text)
    elif context == "sql":
        # SQL sanitization (basic - use parameterized queries instead!)
        return _sanitize_sql(text)
    else:
        # General sanitization
        return _sanitize_general(text)


def _sanitize_general(text: str) -> str:
    """General text sanitization."""
    # Remove control characters except newline and tab
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t' or char == '\r')
    
    # Remove potential script injections
    dangerous_patterns = [
        (r'<script[^>]*>.*?</script>', ''),  # Script tags
        (r'javascript:', ''),  # JavaScript protocol
        (r'on\w+\s*=', ''),  # Event handlers
        (r'<!--.*?-->', ''),  # HTML comments
        (r'<iframe[^>]*>', ''),  # Iframes
        (r'<object[^>]*>', ''),  # Objects
        (r'<embed[^>]*>', ''),  # Embeds
    ]
    
    for pattern, replacement in dangerous_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    return sanitized.strip()


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename for security."""
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    
    # Remove special characters that could be problematic
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')
    
    # Remove shell metacharacters
    filename = re.sub(r'[$`!]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    # Ensure non-empty
    if not filename:
        raise SecurityError("Filename cannot be empty after sanitization")
    
    return filename


def _sanitize_command(text: str) -> str:
    """Sanitize command arguments."""
    # Use shlex to properly quote
    try:
        # This will raise an exception if the string has unmatched quotes
        shlex.split(text)
        return shlex.quote(text)
    except ValueError:
        raise SecurityError("Command contains unmatched quotes")


def _sanitize_sql(text: str) -> str:
    """Basic SQL sanitization (prefer parameterized queries!)."""
    # Remove SQL comments
    text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Escape single quotes
    text = text.replace("'", "''")
    
    # Remove potentially dangerous keywords (very basic)
    dangerous_keywords = [
        'EXEC', 'EXECUTE', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'GRANT', 'REVOKE', 'UNION', 'SCRIPT'
    ]
    
    for keyword in dangerous_keywords:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            raise SecurityError(f"SQL contains potentially dangerous keyword: {keyword}")
    
    return text


def sanitize_path(path: Union[str, Path]) -> Path:
    """Sanitize a file path for security.
    
    Args:
        path: Path to sanitize
        
    Returns:
        Sanitized Path object
        
    Raises:
        SecurityError: If path contains dangerous elements
    """
    if not path:
        raise SecurityError("Path cannot be empty")
    
    path_str = str(path)
    
    # Check for null bytes
    if '\x00' in path_str:
        raise SecurityError("Path contains null bytes")
    
    # Remove multiple slashes
    path_str = re.sub(r'/+', '/', path_str)
    path_str = re.sub(r'\\\\+', r'\\', path_str)
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'\.\./',  # Parent directory traversal
        r'\.\.\\',  # Parent directory traversal (Windows)
        r'^~',  # Home directory expansion
        r'\$\{',  # Variable expansion
        r'\$\(',  # Command substitution
        r'`',  # Command substitution
        r'<', r'>',  # Redirection
        r'\|',  # Pipe
        r'&',  # Background/and
        r';',  # Command separator
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, path_str):
            raise SecurityError(f"Path contains dangerous pattern: {pattern}")
    
    # Convert to Path object and resolve
    try:
        sanitized_path = Path(path_str).resolve()
    except (ValueError, OSError) as e:
        raise SecurityError(f"Invalid path: {str(e)}")
    
    return sanitized_path


def prevent_path_traversal(path: Union[str, Path], 
                          base_dir: Union[str, Path],
                          follow_symlinks: bool = False) -> Path:
    """Prevent path traversal attacks by ensuring path is within base directory.
    
    Args:
        path: Path to check
        base_dir: Base directory that path must be within
        follow_symlinks: Whether to follow symbolic links
        
    Returns:
        Validated absolute path
        
    Raises:
        SecurityError: If path traversal is detected
    """
    # Sanitize both paths
    safe_path = sanitize_path(path)
    safe_base = sanitize_path(base_dir)
    
    # Resolve to absolute paths
    abs_base = safe_base.resolve()
    
    # Handle symlinks
    if follow_symlinks:
        abs_path = safe_path.resolve()
    else:
        # Resolve path without following symlinks in the final component
        abs_path = safe_path.resolve(strict=False)
        if abs_path.is_symlink():
            raise SecurityError("Path contains symbolic link (symlinks disabled)")
    
    # Check if path is within base directory
    try:
        abs_path.relative_to(abs_base)
    except ValueError:
        raise SecurityError(f"Path traversal detected: {path} is outside {base_dir}")
    
    # Additional check for symlink pointing outside base
    if abs_path.exists() and abs_path.is_symlink():
        link_target = abs_path.readlink()
        if link_target.is_absolute():
            try:
                link_target.relative_to(abs_base)
            except ValueError:
                raise SecurityError("Symlink points outside base directory")
    
    return abs_path


def prevent_command_injection(command: str, 
                            allowed_commands: Optional[List[str]] = None,
                            allow_shell: bool = False) -> List[str]:
    """Prevent command injection by validating and sanitizing commands.
    
    Args:
        command: Command string to validate
        allowed_commands: List of allowed command names
        allow_shell: Whether to allow shell execution (dangerous!)
        
    Returns:
        List of command arguments suitable for subprocess
        
    Raises:
        SecurityError: If command injection is detected
    """
    if not command or not isinstance(command, str):
        raise SecurityError("Command must be a non-empty string")
    
    # Check for obvious injection attempts
    dangerous_chars = ['&', '|', ';', '\n', '\r', '$', '`', '(', ')', '<', '>', '{', '}']
    if not allow_shell:
        for char in dangerous_chars:
            if char in command:
                raise SecurityError(f"Command contains dangerous character: {char}")
    
    # Parse command safely
    try:
        args = shlex.split(command)
    except ValueError as e:
        raise SecurityError(f"Invalid command format: {str(e)}")
    
    if not args:
        raise SecurityError("Empty command after parsing")
    
    # Validate command name
    cmd_name = args[0]
    
    # Check if command is in allowed list
    if allowed_commands and cmd_name not in allowed_commands:
        raise SecurityError(f"Command '{cmd_name}' not in allowed list")
    
    # Additional checks for dangerous commands
    dangerous_commands = [
        'eval', 'exec', 'sh', 'bash', 'zsh', 'fish', 'cmd', 'powershell',
        'python', 'perl', 'ruby', 'php', 'node', 'nc', 'netcat', 'curl',
        'wget', 'ssh', 'telnet', 'rm', 'dd', 'format', 'mkfs'
    ]
    
    if cmd_name.lower() in dangerous_commands and not allowed_commands:
        raise SecurityError(f"Potentially dangerous command: {cmd_name}")
    
    # Validate arguments
    for arg in args[1:]:
        # Check for argument injection
        if arg.startswith('-') and '=' in arg:
            # Could be trying to inject via --option=value
            key, value = arg.split('=', 1)
            if any(char in value for char in dangerous_chars):
                raise SecurityError(f"Dangerous character in argument value: {arg}")
    
    return args


@contextmanager
def safe_temp_file(suffix: Optional[str] = None, 
                  prefix: Optional[str] = None,
                  dir: Optional[Union[str, Path]] = None):
    """Create a secure temporary file.
    
    Args:
        suffix: File suffix
        prefix: File prefix
        dir: Directory for temp file (must be validated separately)
        
    Yields:
        Path to temporary file
    """
    # Validate directory if provided
    if dir:
        dir = prevent_path_traversal(dir, dir)
    
    # Create secure temporary file
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    temp_path = Path(path)
    
    try:
        os.close(fd)  # Close the file descriptor
        yield temp_path
    finally:
        # Secure deletion
        if temp_path.exists():
            # Overwrite with random data before deletion (optional, for sensitive data)
            if temp_path.is_file():
                with open(temp_path, 'wb') as f:
                    f.write(secrets.token_bytes(min(1024, temp_path.stat().st_size)))
            temp_path.unlink()


def safe_file_read(path: Union[str, Path], 
                  base_dir: Optional[Union[str, Path]] = None,
                  max_size: int = 100 * 1024 * 1024,  # 100MB default
                  encoding: str = 'utf-8') -> str:
    """Safely read a file with security checks.
    
    Args:
        path: File path to read
        base_dir: Base directory to restrict reading to
        max_size: Maximum file size in bytes
        encoding: File encoding
        
    Returns:
        File contents as string
        
    Raises:
        SecurityError: If file access is unsafe
    """
    # Validate path
    if base_dir:
        safe_path = prevent_path_traversal(path, base_dir)
    else:
        safe_path = sanitize_path(path)
    
    # Check if file exists and is a regular file
    if not safe_path.exists():
        raise SecurityError(f"File does not exist: {safe_path}")
    if not safe_path.is_file():
        raise SecurityError(f"Path is not a regular file: {safe_path}")
    
    # Check file size
    file_size = safe_path.stat().st_size
    if file_size > max_size:
        raise SecurityError(f"File too large: {file_size} bytes (max: {max_size})")
    
    # Check if file is readable
    if not os.access(safe_path, os.R_OK):
        raise SecurityError(f"File is not readable: {safe_path}")
    
    # Read file safely
    try:
        with open(safe_path, 'r', encoding=encoding) as f:
            contents = f.read()
    except UnicodeDecodeError:
        raise SecurityError(f"File has invalid {encoding} encoding")
    except Exception as e:
        raise SecurityError(f"Error reading file: {str(e)}")
    
    return contents


def safe_file_write(path: Union[str, Path],
                   content: str,
                   base_dir: Optional[Union[str, Path]] = None,
                   overwrite: bool = False,
                   mode: int = 0o644,
                   encoding: str = 'utf-8') -> Path:
    """Safely write to a file with security checks.
    
    Args:
        path: File path to write to
        content: Content to write
        base_dir: Base directory to restrict writing to
        overwrite: Whether to overwrite existing files
        mode: File permissions (Unix)
        encoding: File encoding
        
    Returns:
        Path to written file
        
    Raises:
        SecurityError: If file write is unsafe
    """
    # Validate path
    if base_dir:
        safe_path = prevent_path_traversal(path, base_dir)
    else:
        safe_path = sanitize_path(path)
    
    # Check if file exists
    if safe_path.exists() and not overwrite:
        raise SecurityError(f"File already exists: {safe_path}")
    
    # Ensure parent directory exists
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file atomically using a temporary file
    temp_fd, temp_path = tempfile.mkstemp(
        dir=safe_path.parent,
        prefix=f".{safe_path.name}.",
        suffix=".tmp"
    )
    
    try:
        # Write content to temporary file
        with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
            f.write(content)
        
        # Set proper permissions
        os.chmod(temp_path, mode)
        
        # Atomic move (rename) to final location
        Path(temp_path).replace(safe_path)
        
    except Exception as e:
        # Clean up temporary file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise SecurityError(f"Error writing file: {str(e)}")
    
    return safe_path


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """Securely hash a password using PBKDF2.
    
    Args:
        password: Password to hash
        salt: Optional salt (will generate if not provided)
        
    Returns:
        Tuple of (hash_hex, salt)
    """
    if not password:
        raise SecurityError("Password cannot be empty")
    
    # Generate salt if not provided
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Hash password using PBKDF2 with SHA256
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100000  # OWASP recommendation
    )
    
    return key.hex(), salt


def verify_password(password: str, hash_hex: str, salt: bytes) -> bool:
    """Verify a password against a hash.
    
    Args:
        password: Password to verify
        hash_hex: Expected hash in hex format
        salt: Salt used for hashing
        
    Returns:
        True if password matches, False otherwise
    """
    calculated_hash, _ = hash_password(password, salt)
    
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(calculated_hash, hash_hex)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def run_command_safely(args: List[str],
                      timeout: int = 30,
                      cwd: Optional[Union[str, Path]] = None,
                      env: Optional[dict] = None,
                      capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command safely with security restrictions.
    
    Args:
        args: Command arguments (already validated)
        timeout: Command timeout in seconds
        cwd: Working directory (will be validated)
        env: Environment variables (filtered)
        capture_output: Whether to capture output
        
    Returns:
        CompletedProcess instance
        
    Raises:
        SecurityError: If command execution is unsafe
    """
    # Validate working directory
    if cwd:
        cwd = prevent_path_traversal(cwd, cwd)
    
    # Filter environment variables
    if env:
        # Remove potentially dangerous environment variables
        dangerous_vars = [
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'DYLD_LIBRARY_PATH', 'PYTHONPATH', 'PERL5LIB', 'RUBYLIB',
            'NODE_PATH', 'CLASSPATH'
        ]
        filtered_env = {k: v for k, v in env.items() 
                       if k not in dangerous_vars}
    else:
        filtered_env = None
    
    try:
        result = subprocess.run(
            args,
            timeout=timeout,
            cwd=cwd,
            env=filtered_env,
            capture_output=capture_output,
            text=True,
            shell=False  # Never use shell
        )
        return result
    except subprocess.TimeoutExpired:
        raise SecurityError(f"Command timed out after {timeout} seconds")
    except Exception as e:
        raise SecurityError(f"Command execution failed: {str(e)}")