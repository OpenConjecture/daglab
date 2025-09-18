"""Tests for the security module."""

import hashlib
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from daglab.helpers.security import (
    CryptoUtils,
    EnvironmentSecurity,
    FileOperationSecurity,
    PathTraversalPrevention,
    SecurityManager,
    default_security_manager,
    run_command_safely,
    safe_path_join,
    sanitize_input,
)
from daglab.runtime.errors import SecurityError


class TestSecurityManager:
    """Test SecurityManager class."""
    
    def test_initialization(self):
        """Test SecurityManager initialization."""
        manager = SecurityManager(strict_mode=True)
        assert manager.strict_mode is True
        assert 'ls' in manager._trusted_commands
        assert 'LD_PRELOAD' in manager._forbidden_env_vars
    
    def test_sanitize_command_string(self):
        """Test command sanitization from string."""
        manager = SecurityManager(strict_mode=False)
        
        command = "ls -la /tmp"
        sanitized = manager.sanitize_command(command)
        assert sanitized == ['ls', '-la', '/tmp']
    
    def test_sanitize_command_list(self):
        """Test command sanitization from list."""
        manager = SecurityManager(strict_mode=False)
        
        command = ['echo', 'hello world']
        sanitized = manager.sanitize_command(command)
        assert sanitized == ['echo', 'hello world']
    
    def test_empty_command(self):
        """Test empty command raises error."""
        manager = SecurityManager()
        
        with pytest.raises(SecurityError, match="Empty command"):
            manager.sanitize_command([])
        
        with pytest.raises(SecurityError, match="Empty command"):
            manager.sanitize_command("")
    
    def test_untrusted_command_strict_mode(self):
        """Test untrusted commands in strict mode."""
        manager = SecurityManager(strict_mode=True)
        
        with pytest.raises(SecurityError, match="not in trusted command list"):
            manager.sanitize_command(['rm', '-rf', '/'])
    
    def test_trusted_command_strict_mode(self):
        """Test trusted commands in strict mode."""
        manager = SecurityManager(strict_mode=True)
        
        sanitized = manager.sanitize_command(['ls', '-la'])
        assert sanitized == ['ls', '-la']
    
    def test_dangerous_characters_strict_mode(self):
        """Test dangerous characters in strict mode."""
        manager = SecurityManager(strict_mode=True)
        
        with pytest.raises(SecurityError, match="dangerous characters"):
            manager.sanitize_command(['echo', 'test; rm -rf /'])
    
    def test_dangerous_characters_non_strict(self):
        """Test dangerous characters are quoted in non-strict mode."""
        manager = SecurityManager(strict_mode=False)
        
        sanitized = manager.sanitize_command(['echo', 'test; dangerous'])
        # The dangerous argument should be quoted
        assert any("'" in arg or '"' in arg for arg in sanitized if 'dangerous' in arg)
    
    def test_safe_subprocess_run(self, tmp_path):
        """Test safe subprocess execution."""
        manager = SecurityManager(strict_mode=False)
        
        result = manager.safe_subprocess_run(['echo', 'test'])
        assert result.stdout.strip() == 'test'
        assert result.returncode == 0
    
    def test_safe_subprocess_run_with_cwd(self, tmp_path):
        """Test subprocess with working directory."""
        manager = SecurityManager(strict_mode=False)
        
        result = manager.safe_subprocess_run(['pwd'], cwd=tmp_path)
        assert str(tmp_path) in result.stdout
    
    def test_safe_subprocess_run_timeout(self):
        """Test subprocess timeout."""
        manager = SecurityManager(strict_mode=False)
        
        with pytest.raises(SecurityError, match="Command timed out"):
            manager.safe_subprocess_run(['sleep', '5'], timeout=0.1)
    
    def test_safe_subprocess_run_failure(self):
        """Test subprocess failure handling."""
        manager = SecurityManager(strict_mode=False)
        
        with pytest.raises(SecurityError, match="Command failed"):
            manager.safe_subprocess_run(['ls', '/nonexistent_directory_12345'])
    
    def test_sanitize_environment(self):
        """Test environment sanitization."""
        manager = SecurityManager(strict_mode=False)
        
        env = {
            'SAFE_VAR': 'value',
            'ANOTHER_VAR': 'test',
            'PATH': '/usr/bin',  # Forbidden in strict mode
        }
        
        sanitized = manager.sanitize_environment(env)
        assert 'SAFE_VAR' in sanitized
        assert 'ANOTHER_VAR' in sanitized
        assert 'PATH' in sanitized  # Not strict mode
    
    def test_sanitize_environment_strict(self):
        """Test environment sanitization in strict mode."""
        manager = SecurityManager(strict_mode=True)
        
        env = {'LD_PRELOAD': 'malicious.so'}
        
        with pytest.raises(SecurityError, match="Forbidden environment variable"):
            manager.sanitize_environment(env)
    
    def test_sanitize_environment_invalid_name(self):
        """Test invalid environment variable names."""
        manager = SecurityManager()
        
        env = {'INVALID-VAR': 'value'}
        
        with pytest.raises(SecurityError, match="Invalid environment variable name"):
            manager.sanitize_environment(env)
    
    def test_sanitize_environment_null_bytes(self):
        """Test null byte removal."""
        manager = SecurityManager()
        
        env = {'VAR': 'value\x00with\x00nulls'}
        sanitized = manager.sanitize_environment(env)
        
        assert '\x00' not in sanitized['VAR']
        assert sanitized['VAR'] == 'valuewithnulls'
    
    def test_sanitize_environment_length_limit(self):
        """Test environment value length limit."""
        manager = SecurityManager()
        
        long_value = 'x' * 40000
        env = {'VAR': long_value}
        sanitized = manager.sanitize_environment(env)
        
        assert len(sanitized['VAR']) == 32768


class TestPathTraversalPrevention:
    """Test PathTraversalPrevention class."""
    
    def test_safe_join(self, tmp_path):
        """Test safe path joining."""
        base = tmp_path / "base"
        base.mkdir()
        
        # Normal join
        result = PathTraversalPrevention.safe_join(base, "subdir", "file.txt")
        assert str(result).startswith(str(base))
        assert result == base / "subdir" / "file.txt"
    
    def test_safe_join_removes_leading_slash(self, tmp_path):
        """Test that leading slashes are removed."""
        base = tmp_path / "base"
        base.mkdir()
        
        result = PathTraversalPrevention.safe_join(base, "/etc/passwd")
        assert str(result) == str(base / "etc" / "passwd")
    
    def test_safe_join_traversal_detection(self, tmp_path):
        """Test path traversal detection."""
        base = tmp_path / "base"
        base.mkdir()
        
        with pytest.raises(SecurityError, match="Path traversal detected"):
            PathTraversalPrevention.safe_join(base, "../outside")
    
    def test_safe_join_complex_traversal(self, tmp_path):
        """Test complex path traversal attempts."""
        base = tmp_path / "base"
        base.mkdir()
        (base / "subdir").mkdir()
        
        with pytest.raises(SecurityError, match="Path traversal detected"):
            PathTraversalPrevention.safe_join(base, "subdir", "../../outside")
    
    def test_is_safe_path(self, tmp_path):
        """Test path safety checking."""
        base = tmp_path / "base"
        base.mkdir()
        
        safe_path = base / "subdir" / "file.txt"
        assert PathTraversalPrevention.is_safe_path(safe_path, base) is True
        
        unsafe_path = tmp_path / "outside.txt"
        assert PathTraversalPrevention.is_safe_path(unsafe_path, base) is False


class TestFileOperationSecurity:
    """Test FileOperationSecurity class."""
    
    def test_initialization(self, tmp_path):
        """Test FileOperationSecurity initialization."""
        ops = FileOperationSecurity(base_path=tmp_path)
        assert ops.base_path == tmp_path
        
        ops_no_base = FileOperationSecurity()
        assert ops_no_base.base_path is None
    
    def test_safe_read(self, tmp_path):
        """Test safe file reading."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        
        content = ops.safe_read("test.txt")
        assert content == "Hello World"
    
    def test_safe_read_absolute_path(self, tmp_path):
        """Test reading with absolute path."""
        ops = FileOperationSecurity()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")
        
        content = ops.safe_read(test_file)
        assert content == "Content"
    
    def test_safe_read_traversal_prevention(self, tmp_path):
        """Test read with path traversal prevention."""
        base = tmp_path / "base"
        base.mkdir()
        ops = FileOperationSecurity(base_path=base)
        
        # Create file outside base
        outside = tmp_path / "outside.txt"
        outside.write_text("Secret")
        
        with pytest.raises(SecurityError, match="Path traversal detected"):
            ops.safe_read("../outside.txt")
    
    def test_safe_read_file_size_limit(self, tmp_path):
        """Test file size limit."""
        ops = FileOperationSecurity()
        
        # Create a large file (mock)
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1000)
        
        # Mock stat to return large size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=200 * 1024 * 1024)  # 200MB
            
            with pytest.raises(SecurityError, match="File too large"):
                ops.safe_read(large_file)
    
    def test_safe_write(self, tmp_path):
        """Test safe file writing."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        ops.safe_write("output.txt", "Test content")
        
        written_file = tmp_path / "output.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Test content"
    
    def test_safe_write_atomic(self, tmp_path):
        """Test atomic write operation."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        # Write initial content
        ops.safe_write("atomic.txt", "Initial")
        
        # Mock an error during write
        with patch('builtins.open', side_effect=Exception("Write failed")) as mock_open:
            # Allow the temp file creation
            original_open = open
            mock_open.side_effect = lambda path, mode: (
                original_open(path, mode) if '.tmp' in str(path)
                else Exception("Write failed")
            )
            
            with pytest.raises(SecurityError, match="Failed to write file"):
                ops.safe_write("atomic.txt", "Updated")
        
        # Original file should still have initial content
        assert (tmp_path / "atomic.txt").read_text() == "Initial"
    
    def test_safe_write_create_parents(self, tmp_path):
        """Test creating parent directories."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        ops.safe_write("deep/nested/file.txt", "Content", create_parents=True)
        
        assert (tmp_path / "deep" / "nested" / "file.txt").exists()
    
    def test_safe_delete_file(self, tmp_path):
        """Test safe file deletion."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        # Create and delete a file
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("Delete this")
        
        ops.safe_delete("delete_me.txt")
        assert not test_file.exists()
    
    def test_safe_delete_directory(self, tmp_path):
        """Test safe directory deletion."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        # Create empty directory
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()
        
        ops.safe_delete("empty_dir")
        assert not test_dir.exists()
    
    def test_safe_delete_non_empty_dir_fails(self, tmp_path):
        """Test that non-empty directory deletion fails."""
        ops = FileOperationSecurity(base_path=tmp_path)
        
        # Create non-empty directory
        test_dir = tmp_path / "non_empty"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        
        with pytest.raises(SecurityError, match="Failed to delete"):
            ops.safe_delete("non_empty")


class TestEnvironmentSecurity:
    """Test EnvironmentSecurity class."""
    
    def test_get_safe_env_valid(self):
        """Test getting valid environment variable."""
        os.environ['TEST_VAR'] = 'test_value'
        
        value = EnvironmentSecurity.get_safe_env('TEST_VAR')
        assert value == 'test_value'
        
        # Cleanup
        del os.environ['TEST_VAR']
    
    def test_get_safe_env_default(self):
        """Test default value for missing env var."""
        value = EnvironmentSecurity.get_safe_env('MISSING_VAR', default='default')
        assert value == 'default'
    
    def test_get_safe_env_required(self):
        """Test required environment variable."""
        with pytest.raises(SecurityError, match="Required environment variable not set"):
            EnvironmentSecurity.get_safe_env('MISSING_REQUIRED', required=True)
    
    def test_get_safe_env_invalid_name(self):
        """Test invalid environment variable name."""
        with pytest.raises(SecurityError, match="Invalid environment variable name"):
            EnvironmentSecurity.get_safe_env('INVALID-NAME')
    
    def test_mask_sensitive_env(self):
        """Test masking sensitive environment variables."""
        env_dict = {
            'NORMAL_VAR': 'visible',
            'PASSWORD': 'secret123',
            'API_KEY': 'abcdef123456',
            'SHORT_TOKEN': 'ab',
            'DATABASE_PASSWORD': 'db_secret',
        }
        
        masked = EnvironmentSecurity.mask_sensitive_env(env_dict)
        
        assert masked['NORMAL_VAR'] == 'visible'
        assert masked['PASSWORD'] == 'se...23'
        assert masked['API_KEY'] == 'ab...56'
        assert masked['SHORT_TOKEN'] == '***'
        assert masked['DATABASE_PASSWORD'] == 'db...et'


class TestCryptoUtils:
    """Test CryptoUtils class."""
    
    def test_generate_token(self):
        """Test token generation."""
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()
        
        # Tokens should be unique
        assert token1 != token2
        
        # Test custom length
        token = CryptoUtils.generate_token(16)
        # URL-safe base64 encoding increases length
        assert len(token) > 16
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "my_secure_password"
        
        hash1, salt1 = CryptoUtils.hash_password(password)
        hash2, salt2 = CryptoUtils.hash_password(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2
        assert salt1 != salt2
        
        # Same password and salt should produce same hash
        hash3, _ = CryptoUtils.hash_password(password, salt1)
        assert hash1 == hash3
    
    def test_verify_password(self):
        """Test password verification."""
        password = "test_password"
        wrong_password = "wrong_password"
        
        hash_hex, salt = CryptoUtils.hash_password(password)
        
        # Correct password should verify
        assert CryptoUtils.verify_password(password, hash_hex, salt) is True
        
        # Wrong password should not verify
        assert CryptoUtils.verify_password(wrong_password, hash_hex, salt) is False
    
    def test_hash_file(self, tmp_path):
        """Test file hashing."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        
        # Calculate hash
        file_hash = CryptoUtils.hash_file(test_file)
        
        # Verify it's a valid SHA256 hash
        assert len(file_hash) == 64  # SHA256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in file_hash)
        
        # Same content should produce same hash
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Hello World")
        assert CryptoUtils.hash_file(test_file2) == file_hash
        
        # Different content should produce different hash
        test_file3 = tmp_path / "test3.txt"
        test_file3.write_text("Different content")
        assert CryptoUtils.hash_file(test_file3) != file_hash


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_sanitize_input(self):
        """Test sanitize_input function."""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" not in result
    
    def test_safe_path_join_function(self, tmp_path):
        """Test safe_path_join function."""
        result = safe_path_join(tmp_path, "subdir", "file.txt")
        assert str(result).startswith(str(tmp_path))
    
    def test_run_command_safely_function(self):
        """Test run_command_safely function."""
        # This uses the default security manager
        with pytest.raises(SecurityError):
            # 'rm' is not in the trusted commands list
            run_command_safely(['rm', '-rf', '/'])
    
    def test_default_security_manager(self):
        """Test that default_security_manager is properly initialized."""
        assert default_security_manager.strict_mode is True
        assert isinstance(default_security_manager, SecurityManager)