"""Tests for security utilities."""

import pytest
from pathlib import Path
import tempfile
import os
import subprocess

from daglab.helpers.security import (
    sanitize_input,
    sanitize_path,
    prevent_path_traversal,
    prevent_command_injection,
    safe_file_read,
    safe_file_write,
    hash_password,
    verify_password,
    generate_secure_token,
    run_command_safely,
    safe_temp_file,
    SecurityError
)


class TestInputSanitization:
    """Test input sanitization functions."""
    
    def test_general_sanitization(self):
        """Test general input sanitization."""
        # Basic sanitization
        result = sanitize_input("Hello World", context="general")
        assert result == "Hello World"
        
        # Remove control characters
        result = sanitize_input("Hello\x00\x01World", context="general")
        assert "Hello" in result and "World" in result
        assert "\x00" not in result
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        # Remove path separators
        result = sanitize_input("../../../etc/passwd", context="filename")
        assert result == "etcpasswd"
        
        # Remove special characters
        result = sanitize_input("file<>:|?*.txt", context="filename")
        assert "<" not in result and ">" not in result
        assert ":" not in result and "|" not in result
        assert "?" not in result and "*" not in result
    
    def test_command_sanitization(self):
        """Test command argument sanitization."""
        # Valid command
        result = sanitize_input("ls -la", context="command")
        assert "ls -la" in result
        
        # Unmatched quotes
        with pytest.raises(SecurityError, match="unmatched quotes"):
            sanitize_input("echo 'hello", context="command")
    
    def test_sql_sanitization(self):
        """Test SQL sanitization."""
        # Basic SQL
        result = sanitize_input("SELECT * FROM users WHERE id = 1", context="sql")
        assert "users" in result
        
        # SQL injection attempt
        with pytest.raises(SecurityError, match="dangerous keyword"):
            sanitize_input("'; DROP TABLE users; --", context="sql")
    
    def test_encoding_validation(self):
        """Test encoding validation."""
        # Valid UTF-8
        result = sanitize_input("Hello 世界", context="general")
        assert result == "Hello 世界"
        
        # Invalid encoding
        with pytest.raises(SecurityError):
            sanitize_input("Hello\x80\x81", context="general", encoding="ascii")
    
    def test_null_byte_detection(self):
        """Test null byte detection."""
        with pytest.raises(SecurityError, match="null bytes"):
            sanitize_input("file\x00.txt", context="general")


class TestPathSanitization:
    """Test path sanitization functions."""
    
    def test_basic_path_sanitization(self):
        """Test basic path sanitization."""
        result = sanitize_path("/tmp/test.txt")
        assert isinstance(result, Path)
        assert result == Path("/tmp/test.txt").resolve()
    
    def test_null_byte_in_path(self):
        """Test null byte detection in paths."""
        with pytest.raises(SecurityError, match="null bytes"):
            sanitize_path("/tmp/file\x00.txt")
    
    def test_dangerous_path_patterns(self):
        """Test dangerous path pattern detection."""
        dangerous_paths = [
            "../../../etc/passwd",
            "~/sensitive_file",
            "${HOME}/file",
            "$(whoami)/file",
            "`id`/file",
            "file|cat",
            "file>output",
            "file;rm -rf /",
        ]
        
        for path in dangerous_paths:
            with pytest.raises(SecurityError, match="dangerous pattern"):
                sanitize_path(path)
    
    def test_multiple_slash_normalization(self):
        """Test normalization of multiple slashes."""
        result = sanitize_path("/tmp///test//file.txt")
        assert str(result).count("//") == 0


class TestPathTraversalPrevention:
    """Test path traversal prevention."""
    
    def test_valid_path_within_base(self):
        """Test valid path within base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "subdir" / "test.txt"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            
            result = prevent_path_traversal(test_file, base)
            assert result == test_file.resolve()
    
    def test_path_traversal_attempt(self):
        """Test path traversal attempt detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            with pytest.raises(SecurityError, match="Path traversal detected"):
                prevent_path_traversal("../../../etc/passwd", base)
    
    def test_symlink_handling(self):
        """Test symbolic link handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            real_file = base / "real.txt"
            real_file.write_text("test")
            
            link = base / "link.txt"
            link.symlink_to(real_file)
            
            # With symlinks allowed
            result = prevent_path_traversal(link, base, follow_symlinks=True)
            assert result == real_file.resolve()
            
            # With symlinks disallowed
            with pytest.raises(SecurityError, match="symbolic link"):
                prevent_path_traversal(link, base, follow_symlinks=False)


class TestCommandInjectionPrevention:
    """Test command injection prevention."""
    
    def test_valid_commands(self):
        """Test valid command parsing."""
        result = prevent_command_injection("ls -la /tmp")
        assert result == ["ls", "-la", "/tmp"]
    
    def test_command_injection_attempts(self):
        """Test command injection attempt detection."""
        dangerous_commands = [
            "ls; rm -rf /",
            "echo hello && cat /etc/passwd",
            "ls | grep secret",
            "echo `whoami`",
            "echo $(id)",
            "ls > /tmp/output",
            "cat < /etc/passwd",
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(SecurityError, match="dangerous character"):
                prevent_command_injection(cmd)
    
    def test_allowed_commands(self):
        """Test command whitelist."""
        allowed = ["ls", "echo", "grep"]
        
        # Allowed command
        result = prevent_command_injection("ls -la", allowed_commands=allowed)
        assert result[0] == "ls"
        
        # Disallowed command
        with pytest.raises(SecurityError, match="not in allowed list"):
            prevent_command_injection("rm -rf /", allowed_commands=allowed)
    
    def test_dangerous_command_detection(self):
        """Test detection of inherently dangerous commands."""
        dangerous = ["eval 'echo hacked'", "exec python", "bash -c 'id'"]
        
        for cmd in dangerous:
            with pytest.raises(SecurityError, match="dangerous command"):
                prevent_command_injection(cmd)


class TestSafeFileOperations:
    """Test safe file operations."""
    
    def test_safe_file_read(self):
        """Test safe file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World")
            
            # Valid read
            content = safe_file_read(test_file)
            assert content == "Hello World"
            
            # With base directory restriction
            content = safe_file_read(test_file, base_dir=tmpdir)
            assert content == "Hello World"
    
    def test_file_read_size_limit(self):
        """Test file size limit on reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "large.txt"
            test_file.write_text("x" * 1000)
            
            # Under size limit
            content = safe_file_read(test_file, max_size=2000)
            assert len(content) == 1000
            
            # Over size limit
            with pytest.raises(SecurityError, match="File too large"):
                safe_file_read(test_file, max_size=500)
    
    def test_safe_file_write(self):
        """Test safe file writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            
            # Initial write
            result = safe_file_write(test_file, "Hello World")
            assert result == test_file
            assert test_file.read_text() == "Hello World"
            
            # Overwrite protection
            with pytest.raises(SecurityError, match="already exists"):
                safe_file_write(test_file, "New content", overwrite=False)
            
            # Overwrite enabled
            safe_file_write(test_file, "New content", overwrite=True)
            assert test_file.read_text() == "New content"
    
    def test_safe_temp_file(self):
        """Test safe temporary file creation."""
        with safe_temp_file(suffix=".txt", prefix="test_") as temp_path:
            assert temp_path.exists()
            assert temp_path.name.startswith("test_")
            assert temp_path.suffix == ".txt"
            
            # Write to temp file
            temp_path.write_text("temporary data")
            assert temp_path.read_text() == "temporary data"
        
        # File should be deleted after context
        assert not temp_path.exists()


class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        
        hash1, salt1 = hash_password(password)
        hash2, salt2 = hash_password(password)
        
        # Different salts produce different hashes
        assert hash1 != hash2
        assert salt1 != salt2
        
        # Hash is consistent with same salt
        hash3, _ = hash_password(password, salt1)
        assert hash1 == hash3
    
    def test_password_verification(self):
        """Test password verification."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword123!"
        
        hash_hex, salt = hash_password(password)
        
        # Correct password
        assert verify_password(password, hash_hex, salt) is True
        
        # Wrong password
        assert verify_password(wrong_password, hash_hex, salt) is False
    
    def test_empty_password(self):
        """Test empty password handling."""
        with pytest.raises(SecurityError, match="cannot be empty"):
            hash_password("")


class TestTokenGeneration:
    """Test secure token generation."""
    
    def test_token_generation(self):
        """Test secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Tokens should be unique
        assert token1 != token2
        
        # Default length
        assert len(token1) > 30  # URL-safe encoding makes it longer
        
        # Custom length
        token3 = generate_secure_token(length=64)
        assert len(token3) > 60


class TestSafeCommandExecution:
    """Test safe command execution."""
    
    def test_safe_command_run(self):
        """Test safe command execution."""
        # Simple echo command
        result = run_command_safely(["echo", "Hello World"])
        assert result.returncode == 0
        assert "Hello World" in result.stdout
    
    def test_command_timeout(self):
        """Test command timeout."""
        # Command that would run forever
        with pytest.raises(SecurityError, match="timed out"):
            run_command_safely(["sleep", "10"], timeout=1)
    
    def test_environment_filtering(self):
        """Test environment variable filtering."""
        dangerous_env = {
            "PATH": "/usr/bin:/bin",
            "LD_PRELOAD": "/evil/library.so",  # Should be filtered
            "HOME": "/home/user",
            "PYTHONPATH": "/evil/path",  # Should be filtered
        }
        
        # The command should run without the dangerous vars
        result = run_command_safely(
            ["echo", "test"],
            env=dangerous_env
        )
        assert result.returncode == 0