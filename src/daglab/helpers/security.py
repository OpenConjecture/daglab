"""Security helpers for safe operations and input handling."""

import hashlib
import hmac
import os
import re
import secrets
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from daglab.helpers.validation import InputSanitizer, PathValidator, ValidationResult
from daglab.runtime.errors import SecurityError


class SecurityManager:
    """Central security management for Daglab operations."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._trusted_commands = {
            'ls', 'cat', 'echo', 'grep', 'find', 'head', 'tail',
            'wc', 'sort', 'uniq', 'cut', 'awk', 'sed'
        }
        self._forbidden_env_vars = {
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'PATH', 'PYTHONPATH', 'HOME', 'USER'
        }
    
    def sanitize_command(self, command: Union[str, List[str]]) -> List[str]:
        """Sanitize a command for safe execution."""
        if isinstance(command, str):
            # Use shlex to safely split the command
            try:
                parts = shlex.split(command)
            except ValueError as e:
                raise SecurityError(f"Invalid command syntax: {e}")
        else:
            parts = list(command)
        
        if not parts:
            raise SecurityError("Empty command")
        
        # Check if command is in trusted list
        cmd_name = Path(parts[0]).name
        if self.strict_mode and cmd_name not in self._trusted_commands:
            raise SecurityError(
                f"Command '{cmd_name}' not in trusted command list",
                context=ErrorContext(
                    suggestions=[
                        f"Use one of the trusted commands: {', '.join(sorted(self._trusted_commands))}",
                        "Disable strict mode if you need to run arbitrary commands"
                    ]
                )
            )
        
        # Sanitize each argument
        sanitized = []
        for part in parts:
            # Check for command injection attempts
            if any(char in part for char in ';|&`$(){}[]<>'):
                if self.strict_mode:
                    raise SecurityError(f"Potentially dangerous characters in argument: {part}")
                # In non-strict mode, quote the argument
                part = shlex.quote(part)
            sanitized.append(part)
        
        return sanitized
    
    def safe_subprocess_run(
        self,
        command: Union[str, List[str]],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> subprocess.CompletedProcess:
        """Safely run a subprocess with security checks."""
        # Sanitize command
        command = self.sanitize_command(command)
        
        # Validate working directory
        if cwd:
            result = PathValidator.validate_path(cwd, must_exist=True, file_type='dir')
            if not result.valid:
                raise SecurityError(f"Invalid working directory: {', '.join(result.errors)}")
        
        # Sanitize environment
        if env:
            env = self.sanitize_environment(env)
        
        # Set secure defaults
        kwargs.setdefault('shell', False)  # Never use shell=True
        kwargs.setdefault('check', True)
        
        try:
            return subprocess.run(
                command,
                env=env,
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
                **kwargs
            )
        except subprocess.TimeoutExpired:
            raise SecurityError(f"Command timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            raise SecurityError(
                f"Command failed with exit code {e.returncode}",
                cause=e,
                context=ErrorContext(
                    details={
                        'stdout': e.stdout,
                        'stderr': e.stderr
                    }
                )
            )
    
    def sanitize_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """Sanitize environment variables."""
        sanitized = {}
        
        for key, value in env.items():
            # Check for forbidden variables
            if key.upper() in self._forbidden_env_vars:
                if self.strict_mode:
                    raise SecurityError(f"Forbidden environment variable: {key}")
                continue
            
            # Sanitize key
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                raise SecurityError(f"Invalid environment variable name: {key}")
            
            # Sanitize value
            if isinstance(value, str):
                # Remove null bytes
                value = value.replace('\x00', '')
                # Limit length
                if len(value) > 32768:  # 32KB limit
                    value = value[:32768]
            
            sanitized[key] = str(value)
        
        return sanitized


class PathTraversalPrevention:
    """Prevent path traversal attacks."""
    
    @staticmethod
    def safe_join(base_path: Path, *paths: Union[str, Path]) -> Path:
        """Safely join paths preventing traversal attacks."""
        base_path = Path(base_path).resolve()
        
        # Join all paths
        joined = base_path
        for p in paths:
            # Remove any leading slashes to prevent absolute paths
            p = str(p).lstrip('/')
            joined = joined / p
        
        # Resolve and check if still under base path
        resolved = joined.resolve()
        
        try:
            resolved.relative_to(base_path)
        except ValueError:
            raise SecurityError(
                f"Path traversal detected: {joined} -> {resolved}",
                context=ErrorContext(
                    details={
                        'base_path': str(base_path),
                        'attempted_path': str(joined),
                        'resolved_path': str(resolved)
                    }
                )
            )
        
        return resolved
    
    @staticmethod
    def is_safe_path(path: Path, base_path: Path) -> bool:
        """Check if a path is safe (within base_path)."""
        try:
            path.resolve().relative_to(base_path.resolve())
            return True
        except ValueError:
            return False


class FileOperationSecurity:
    """Secure file operations."""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path
    
    def safe_read(self, file_path: Union[str, Path], mode: str = 'r') -> str:
        """Safely read a file with security checks."""
        file_path = Path(file_path)
        
        # Validate path
        if self.base_path:
            file_path = PathTraversalPrevention.safe_join(self.base_path, file_path)
        
        result = PathValidator.validate_path(
            file_path,
            base_dir=self.base_path,
            must_exist=True,
            file_type='file'
        )
        
        if not result.valid:
            raise SecurityError(f"Invalid file path: {', '.join(result.errors)}")
        
        # Check file size before reading
        max_size = 100 * 1024 * 1024  # 100MB
        if file_path.stat().st_size > max_size:
            raise SecurityError(f"File too large: {file_path}")
        
        # Read file
        try:
            with open(file_path, mode) as f:
                return f.read()
        except Exception as e:
            raise SecurityError(f"Failed to read file: {e}", cause=e)
    
    def safe_write(
        self,
        file_path: Union[str, Path],
        content: Union[str, bytes],
        mode: str = 'w',
        create_parents: bool = False
    ) -> None:
        """Safely write to a file with security checks."""
        file_path = Path(file_path)
        
        # Validate path
        if self.base_path:
            file_path = PathTraversalPrevention.safe_join(self.base_path, file_path)
        
        # Create parent directories if requested
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = PathValidator.validate_path(
            file_path,
            base_dir=self.base_path,
            file_type='file' if file_path.exists() else None
        )
        
        if not result.valid:
            raise SecurityError(f"Invalid file path: {', '.join(result.errors)}")
        
        # Write file with atomic operation
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        try:
            with open(temp_path, mode) as f:
                f.write(content)
            
            # Atomic rename
            temp_path.replace(file_path)
        except Exception as e:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise SecurityError(f"Failed to write file: {e}", cause=e)
    
    def safe_delete(self, file_path: Union[str, Path]) -> None:
        """Safely delete a file with security checks."""
        file_path = Path(file_path)
        
        # Validate path
        if self.base_path:
            file_path = PathTraversalPrevention.safe_join(self.base_path, file_path)
        
        result = PathValidator.validate_path(
            file_path,
            base_dir=self.base_path,
            must_exist=True
        )
        
        if not result.valid:
            raise SecurityError(f"Invalid file path: {', '.join(result.errors)}")
        
        try:
            if file_path.is_dir():
                file_path.rmdir()  # Only removes empty directories
            else:
                file_path.unlink()
        except Exception as e:
            raise SecurityError(f"Failed to delete file: {e}", cause=e)


class EnvironmentSecurity:
    """Secure environment variable handling."""
    
    # Environment variables that may contain sensitive data
    SENSITIVE_VARS = {
        'PASSWORD', 'TOKEN', 'SECRET', 'KEY', 'AUTH',
        'CREDENTIAL', 'PRIVATE', 'API_KEY', 'ACCESS_TOKEN'
    }
    
    @classmethod
    def get_safe_env(
        cls,
        key: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> Optional[str]:
        """Safely get environment variable."""
        # Validate key
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
            raise SecurityError(f"Invalid environment variable name: {key}")
        
        value = os.environ.get(key, default)
        
        if required and value is None:
            raise SecurityError(
                f"Required environment variable not set: {key}",
                context=ErrorContext(
                    suggestions=[f"Set the {key} environment variable"]
                )
            )
        
        return value
    
    @classmethod
    def mask_sensitive_env(cls, env_dict: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive environment variables for logging."""
        masked = {}
        
        for key, value in env_dict.items():
            # Check if key contains sensitive patterns
            key_upper = key.upper()
            is_sensitive = any(pattern in key_upper for pattern in cls.SENSITIVE_VARS)
            
            if is_sensitive and value:
                # Show first and last 2 characters only
                if len(value) > 4:
                    masked[key] = f"{value[:2]}...{value[-2:]}"
                else:
                    masked[key] = "***"
            else:
                masked[key] = value
        
        return masked


class CryptoUtils:
    """Cryptographic utilities for Daglab."""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """Hash a password using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # iterations
        )
        
        return key.hex(), salt
    
    @staticmethod
    def verify_password(password: str, key_hex: str, salt: bytes) -> bool:
        """Verify a password against a hash."""
        computed_key, _ = CryptoUtils.hash_password(password, salt)
        return hmac.compare_digest(computed_key, key_hex)
    
    @staticmethod
    def hash_file(file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate hash of a file."""
        hasher = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()


# Default security manager instance
default_security_manager = SecurityManager(strict_mode=True)


# Convenience functions
def sanitize_input(value: str, **kwargs) -> str:
    """Sanitize user input."""
    return InputSanitizer.sanitize_string(value, **kwargs)


def safe_path_join(base: Path, *parts: Union[str, Path]) -> Path:
    """Safely join paths."""
    return PathTraversalPrevention.safe_join(base, *parts)


def run_command_safely(command: Union[str, List[str]], **kwargs) -> subprocess.CompletedProcess:
    """Run a command safely."""
    return default_security_manager.safe_subprocess_run(command, **kwargs)


from daglab.runtime.errors import ErrorContext