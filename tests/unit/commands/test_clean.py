"""Tests for the clean command."""

import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from daglab.commands.clean import (
    clean,
    find_files_to_clean,
    format_size,
    is_protected,
    delete_files,
    display_files_summary,
    create_undo_script,
    CLEANUP_PATTERNS
)


class TestCleanCommand:
    """Test suite for the clean command."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create directory structure
            dirs = [
                "src", "tests", "docs", "config",
                "exports", "logs", ".daglab/tmp", ".daglab/cache",
                ".marimo", "build", "__pycache__"
            ]
            for dir_name in dirs:
                (base_path / dir_name).mkdir(parents=True)
            
            # Create test files
            test_files = {
                # Protected files (should never be deleted)
                "src/main.py": "# Main code",
                "config/settings.yaml": "settings: true",
                "docs/README.md": "# Documentation",
                
                # Files to clean (old)
                "exports/report.html": "<html>old report</html>",
                "logs/app.log": "old log entry",
                ".daglab/tmp/temp123.tmp": "temp data",
                ".daglab/cache/data.cache": "cache data",
                "__pycache__/module.pyc": "bytecode",
                "build/output.txt": "build output",
                
                # Recent files (should not be cleaned with default settings)
                "exports/recent.html": "<html>recent</html>",
                "logs/recent.log": "recent log"
            }
            
            # Create files with specific timestamps
            old_timestamp = (datetime.now() - timedelta(days=45)).timestamp()
            recent_timestamp = (datetime.now() - timedelta(days=5)).timestamp()
            
            for file_path, content in test_files.items():
                full_path = base_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                
                # Set old timestamp for files that should be cleaned
                if "recent" not in file_path and file_path not in ["src/main.py", "config/settings.yaml", "docs/README.md"]:
                    os.utime(full_path, (old_timestamp, old_timestamp))
                else:
                    os.utime(full_path, (recent_timestamp, recent_timestamp))
            
            yield base_path
    
    def test_format_size(self):
        """Test size formatting function."""
        assert format_size(0) == "0.0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_size(1536) == "1.5 KB"
    
    def test_is_protected(self):
        """Test protected file detection."""
        # Protected patterns
        assert is_protected(Path("main.py"))
        assert is_protected(Path("config.yaml"))
        assert is_protected(Path("README.md"))
        assert is_protected(Path("requirements.txt"))
        assert is_protected(Path(".env"))
        assert is_protected(Path(".gitignore"))
        
        # Protected directories
        assert is_protected(Path("src/module.pyc"))  # In src directory
        assert is_protected(Path("tests/test.log"))  # In tests directory
        assert is_protected(Path("docs/guide.html"))  # In docs directory
        
        # Not protected
        assert not is_protected(Path("exports/report.html"))
        assert not is_protected(Path("logs/app.log"))
        assert not is_protected(Path(".cache/data"))
    
    def test_find_files_to_clean(self, temp_project):
        """Test finding files that match cleanup patterns."""
        os.chdir(temp_project)
        
        # Find files older than 30 days
        files_by_category = find_files_to_clean(temp_project, older_than_days=30)
        
        # Check that old files are found
        assert len(files_by_category["html_exports"]) > 0
        assert len(files_by_category["logs"]) > 0
        assert len(files_by_category["temp_files"]) > 0
        assert len(files_by_category["cache"]) > 0
        assert len(files_by_category["build_artifacts"]) > 0
        
        # Check that recent files are not included
        html_files = [str(f[0]) for f in files_by_category["html_exports"]]
        assert any("report.html" in f for f in html_files)
        assert not any("recent.html" in f for f in html_files)
        
        # Check that protected files are never included
        all_files = []
        for category_files in files_by_category.values():
            all_files.extend([str(f[0]) for f in category_files])
        
        assert not any("main.py" in f for f in all_files)
        assert not any("settings.yaml" in f for f in all_files)
        assert not any("README.md" in f for f in all_files)
    
    def test_find_files_with_notebooks(self, temp_project):
        """Test finding files with notebook flag."""
        os.chdir(temp_project)
        
        # Without notebooks flag
        files_no_nb = find_files_to_clean(temp_project, include_notebooks=False)
        assert "notebooks" not in files_no_nb or len(files_no_nb.get("notebooks", [])) == 0
        
        # With notebooks flag
        files_with_nb = find_files_to_clean(temp_project, include_notebooks=True)
        # Would find .marimo directory if it had old files
    
    def test_display_files_summary(self, temp_project, capsys):
        """Test file summary display."""
        test_files = {
            "html_exports": [
                (Path("export1.html"), 1024, datetime.now()),
                (Path("export2.html"), 2048, datetime.now())
            ],
            "logs": [
                (Path("app.log"), 5000, datetime.now())
            ]
        }
        
        with patch('daglab.commands.clean.console'):
            total_files, total_size = display_files_summary(test_files)
        
        assert total_files == 3
        assert total_size == 8072  # 1024 + 2048 + 5000
    
    def test_delete_files_dry_run(self, temp_project):
        """Test dry run mode doesn't delete files."""
        os.chdir(temp_project)
        
        # Create a test file
        test_file = temp_project / "test_delete.tmp"
        test_file.write_text("test")
        
        files_to_delete = {
            "temp_files": [(test_file, 4, datetime.now())]
        }
        
        deleted_count, deleted_size, errors = delete_files(files_to_delete, dry_run=True)
        
        assert deleted_count == 1
        assert deleted_size == 4
        assert len(errors) == 0
        assert test_file.exists()  # File should still exist
    
    def test_delete_files_actual(self, temp_project):
        """Test actual file deletion."""
        os.chdir(temp_project)
        
        # Create test files
        test_file = temp_project / "test_delete.tmp"
        test_file.write_text("test")
        test_dir = temp_project / "test_cache_dir"
        test_dir.mkdir()
        (test_dir / "cache.dat").write_text("cache")
        
        files_to_delete = {
            "temp_files": [(test_file, 4, datetime.now())],
            "cache": [(test_dir, 100, datetime.now())]
        }
        
        deleted_count, deleted_size, errors = delete_files(files_to_delete, dry_run=False)
        
        assert deleted_count == 2
        assert deleted_size == 104
        assert len(errors) == 0
        assert not test_file.exists()  # File should be deleted
        assert not test_dir.exists()   # Directory should be deleted
    
    def test_delete_files_permission_error(self, temp_project):
        """Test handling of permission errors."""
        os.chdir(temp_project)
        
        test_file = temp_project / "readonly.tmp"
        test_file.write_text("test")
        
        files_to_delete = {
            "temp_files": [(test_file, 4, datetime.now())]
        }
        
        # Mock permission error
        with patch('pathlib.Path.unlink', side_effect=PermissionError("Access denied")):
            deleted_count, deleted_size, errors = delete_files(files_to_delete, dry_run=False)
        
        assert deleted_count == 0
        assert deleted_size == 0
        assert len(errors) == 1
        assert "Permission denied" in errors[0]
    
    def test_create_undo_script(self, temp_project):
        """Test undo script creation."""
        os.chdir(temp_project)
        
        test_files = {
            "html_exports": [
                (Path("export1.html"), 1024, datetime.now()),
                (Path("export2.html"), 2048, datetime.now())
            ]
        }
        
        undo_file = create_undo_script(test_files)
        
        assert undo_file.exists()
        assert undo_file.parent.name == "undo"
        
        content = undo_file.read_text()
        assert "export1.html" in content
        assert "export2.html" in content
        assert "1024" in content
        assert "2048" in content
    
    def test_clean_command_no_files(self, temp_project):
        """Test clean command when no files to clean."""
        runner = CliRunner()
        
        # Change to temp directory with no old files
        with runner.isolated_filesystem():
            result = runner.invoke(clean, ['--older-than', '1'])
            
            assert result.exit_code == 0
            assert "No files to clean" in result.output
    
    def test_clean_command_with_confirmation(self, temp_project):
        """Test clean command with user confirmation."""
        runner = CliRunner()
        os.chdir(temp_project)
        
        # Test declining confirmation
        result = runner.invoke(clean, ['--older-than', '30'], input='n\n')
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        
        # Verify files still exist
        assert (temp_project / "exports" / "report.html").exists()
    
    def test_clean_command_yes_flag(self, temp_project):
        """Test clean command with --yes flag."""
        runner = CliRunner()
        os.chdir(temp_project)
        
        # Get initial file count
        initial_html = list((temp_project / "exports").glob("*.html"))
        
        result = runner.invoke(clean, ['--older-than', '30', '--yes'])
        assert result.exit_code == 0
        assert "Cleaned" in result.output
        
        # Check that old files were deleted
        remaining_html = list((temp_project / "exports").glob("*.html"))
        assert len(remaining_html) < len(initial_html)
    
    def test_clean_command_dry_run(self, temp_project):
        """Test clean command in dry-run mode."""
        runner = CliRunner()
        os.chdir(temp_project)
        
        # Count files before dry run
        html_before = list((temp_project / "exports").glob("*.html"))
        
        result = runner.invoke(clean, ['--older-than', '30', '--dry-run'])
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output
        assert "Would delete" in result.output
        
        # Verify no files were deleted
        html_after = list((temp_project / "exports").glob("*.html"))
        assert len(html_before) == len(html_after)
    
    def test_clean_command_with_notebooks(self, temp_project):
        """Test clean command with notebook cleanup."""
        runner = CliRunner()
        os.chdir(temp_project)
        
        # Create old notebook checkpoint
        checkpoint_dir = temp_project / ".ipynb_checkpoints"
        checkpoint_dir.mkdir()
        checkpoint_file = checkpoint_dir / "notebook-checkpoint.ipynb"
        checkpoint_file.write_text("{}")
        
        # Set old timestamp
        old_time = (datetime.now() - timedelta(days=45)).timestamp()
        os.utime(checkpoint_file, (old_time, old_time))
        
        result = runner.invoke(clean, ['--notebooks', '--yes'])
        assert result.exit_code == 0
    
    def test_clean_command_custom_age(self, temp_project):
        """Test clean command with custom age threshold."""
        runner = CliRunner()
        os.chdir(temp_project)
        
        # Test with 60 days (should find fewer files)
        result = runner.invoke(clean, ['--older-than', '60', '--dry-run'])
        assert result.exit_code == 0
        
        # Test with 1 day (should find more files) 
        result2 = runner.invoke(clean, ['--older-than', '1', '--dry-run'])
        assert result2.exit_code == 0