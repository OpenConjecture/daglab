"""Unit tests for DagLab CLI."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import tempfile
import shutil

from daglab.cli import app, get_version


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_help(self, runner):
        """Test that help is shown when no command is provided."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "DagLab" in result.stdout
        assert "Dagster + Marimo Integration Framework" in result.stdout
    
    def test_version_flag(self, runner):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "DagLab version" in result.stdout
    
    def test_help_flag(self, runner):
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Commands" in result.stdout
        assert "init" in result.stdout
        assert "doctor" in result.stdout


class TestInitCommand:
    """Test the init command."""
    
    def test_init_new_project(self, runner, temp_dir):
        """Test initializing a new project."""
        result = runner.invoke(app, ["init", "test-project", "--path", str(temp_dir)])
        
        assert result.exit_code == 0
        assert "Successfully initialized DagLab project!" in result.stdout
        
        # Check project structure
        project_dir = temp_dir / "test-project"
        assert project_dir.exists()
        assert (project_dir / ".daglab").exists()
        assert (project_dir / ".daglab" / "config.yaml").exists()
        assert (project_dir / "notebooks").exists()
        assert (project_dir / "tests").exists()
        
        # Check config content
        config_content = (project_dir / ".daglab" / "config.yaml").read_text()
        assert "project_name: test-project" in config_content
        assert "template: default" in config_content
    
    def test_init_current_directory(self, runner, temp_dir):
        """Test initializing in current directory."""
        with runner.isolated_filesystem(temp_dir=str(temp_dir)):
            result = runner.invoke(app, ["init"])
            
            assert result.exit_code == 0
            assert ".daglab" in Path.cwd().iterdir()
    
    def test_init_already_initialized(self, runner, temp_dir):
        """Test error when already initialized."""
        # First initialization
        runner.invoke(app, ["init", "test-project", "--path", str(temp_dir)])
        
        # Try to initialize again
        result = runner.invoke(app, ["init", "--path", str(temp_dir / "test-project")])
        
        assert result.exit_code == 1
        assert "DagLab already initialized" in result.stdout
    
    def test_init_with_template(self, runner, temp_dir):
        """Test initialization with custom template."""
        result = runner.invoke(app, ["init", "ml-project", "--path", str(temp_dir), "--template", "ml-pipeline"])
        
        assert result.exit_code == 0
        config_content = (temp_dir / "ml-project" / ".daglab" / "config.yaml").read_text()
        assert "template: ml-pipeline" in config_content


class TestDoctorCommand:
    """Test the doctor command."""
    
    def test_doctor_basic(self, runner):
        """Test basic doctor command."""
        result = runner.invoke(app, ["doctor"])
        
        assert "Running DagLab diagnostics" in result.stdout
        assert "Python Version" in result.stdout
        assert "System Check Results" in result.stdout
    
    def test_doctor_verbose(self, runner):
        """Test doctor with verbose flag."""
        result = runner.invoke(app, ["doctor", "--verbose"])
        
        assert "Running DagLab diagnostics" in result.stdout
    
    @patch('daglab.cli.sys.version_info', (3, 7, 0))
    def test_doctor_python_version_fail(self, runner):
        """Test doctor when Python version is too old."""
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 1
        assert "Some checks failed" in result.stdout
    
    def test_doctor_with_fix(self, runner):
        """Test doctor with --fix flag."""
        with patch('importlib.import_module', side_effect=ImportError("No module")):
            result = runner.invoke(app, ["doctor", "--fix"])
            
            assert "Attempting to fix issues" in result.stdout


class TestCleanCommand:
    """Test the clean command."""
    
    def test_clean_nothing_selected(self, runner):
        """Test clean with no options."""
        result = runner.invoke(app, ["clean"])
        
        assert result.exit_code == 0
        assert "Nothing selected to clean" in result.stdout
    
    def test_clean_cache(self, runner):
        """Test clean cache option."""
        result = runner.invoke(app, ["clean", "--cache"])
        
        assert result.exit_code == 0
        assert "Cleanup complete!" in result.stdout
    
    def test_clean_logs(self, runner):
        """Test clean logs option."""
        result = runner.invoke(app, ["clean", "--logs"])
        
        assert result.exit_code == 0
        assert "Cleanup complete!" in result.stdout
    
    def test_clean_all(self, runner):
        """Test clean all option."""
        result = runner.invoke(app, ["clean", "--all"])
        
        assert result.exit_code == 0
        assert "Cleanup complete!" in result.stdout
    
    def test_clean_dry_run(self, runner):
        """Test clean with dry run."""
        result = runner.invoke(app, ["clean", "--all", "--dry-run"])
        
        assert result.exit_code == 0
        assert "Dry run - would clean:" in result.stdout
        assert ".daglab/cache" in result.stdout


class TestPlaceholderCommands:
    """Test placeholder commands (coming soon)."""
    
    def test_scaffold_command(self, runner):
        """Test scaffold command placeholder."""
        result = runner.invoke(app, ["scaffold", "test-notebook"])
        
        assert result.exit_code == 0
        assert "This feature is coming soon!" in result.stdout
        assert "scaffold" in result.stdout.lower()
    
    def test_discover_command(self, runner):
        """Test discover command placeholder."""
        result = runner.invoke(app, ["discover"])
        
        assert result.exit_code == 0
        assert "This feature is coming soon!" in result.stdout
        assert "discover" in result.stdout.lower()
    
    def test_run_command(self, runner):
        """Test run command placeholder."""
        result = runner.invoke(app, ["run", "my_asset"])
        
        assert result.exit_code == 0
        assert "This feature is coming soon!" in result.stdout
        assert "run" in result.stdout.lower()
    
    def test_export_command(self, runner):
        """Test export command placeholder."""
        result = runner.invoke(app, ["export", "notebook.py"])
        
        assert result.exit_code == 0
        assert "This feature is coming soon!" in result.stdout
        assert "export" in result.stdout.lower()
    
    def test_dev_command(self, runner):
        """Test dev command placeholder."""
        result = runner.invoke(app, ["dev"])
        
        assert result.exit_code == 0
        assert "This feature is coming soon!" in result.stdout
        assert "Development Mode" in result.stdout


class TestErrorHandling:
    """Test error handling in CLI."""
    
    def test_keyboard_interrupt(self, runner):
        """Test handling of keyboard interrupt."""
        with patch('daglab.cli.app', side_effect=KeyboardInterrupt()):
            from daglab.cli import cli
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 130
    
    def test_generic_exception(self, runner, monkeypatch):
        """Test handling of generic exceptions."""
        monkeypatch.setenv("DAGLAB_DEBUG", "0")
        
        with patch('daglab.cli.app', side_effect=Exception("Test error")):
            from daglab.cli import cli
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 1
    
    def test_debug_mode_exception(self, runner, monkeypatch):
        """Test exception handling in debug mode."""
        monkeypatch.setenv("DAGLAB_DEBUG", "1")
        
        with patch('daglab.cli.app', side_effect=Exception("Test error")):
            from daglab.cli import cli
            with pytest.raises(SystemExit):
                cli()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_version_installed(self):
        """Test get_version when package is installed."""
        with patch('daglab.cli.version', return_value="1.2.3"):
            assert get_version() == "1.2.3"
    
    def test_get_version_not_installed(self):
        """Test get_version when package is not installed."""
        with patch('daglab.cli.version', side_effect=PackageNotFoundError()):
            assert get_version() == "0.1.0-dev"


class TestCommandHelp:
    """Test individual command help texts."""
    
    def test_init_help(self, runner):
        """Test init command help."""
        result = runner.invoke(app, ["init", "--help"])
        
        assert result.exit_code == 0
        assert "Initialize a new DagLab project" in result.stdout
        assert "--dagster" in result.stdout
        assert "--template" in result.stdout
    
    def test_doctor_help(self, runner):
        """Test doctor command help."""
        result = runner.invoke(app, ["doctor", "--help"])
        
        assert result.exit_code == 0
        assert "Run diagnostics" in result.stdout
        assert "--verbose" in result.stdout
        assert "--fix" in result.stdout
    
    def test_clean_help(self, runner):
        """Test clean command help."""
        result = runner.invoke(app, ["clean", "--help"])
        
        assert result.exit_code == 0
        assert "Clean up artifacts" in result.stdout
        assert "--cache" in result.stdout
        assert "--logs" in result.stdout
        assert "--all" in result.stdout