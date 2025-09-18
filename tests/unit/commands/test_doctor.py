"""
Unit tests for the doctor command.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from src.daglab.commands.doctor import (
    CheckCategory,
    CheckResult,
    DiagnosticReport,
    DoctorCommand,
    Severity,
)


class TestCheckResult:
    """Test CheckResult dataclass."""
    
    def test_check_result_creation(self):
        """Test creating a CheckResult."""
        result = CheckResult(
            name="Test Check",
            category=CheckCategory.SYSTEM,
            severity=Severity.OK,
            message="Everything is fine",
            details="No issues found",
            fix_suggestion="Nothing to fix",
            can_auto_fix=False
        )
        
        assert result.name == "Test Check"
        assert result.category == CheckCategory.SYSTEM
        assert result.severity == Severity.OK
        assert result.message == "Everything is fine"
        assert result.details == "No issues found"
        assert result.fix_suggestion == "Nothing to fix"
        assert result.can_auto_fix is False


class TestDiagnosticReport:
    """Test DiagnosticReport functionality."""
    
    def test_add_result(self):
        """Test adding results to report."""
        report = DiagnosticReport()
        result = CheckResult(
            name="Test",
            category=CheckCategory.SYSTEM,
            severity=Severity.OK,
            message="OK"
        )
        
        report.add_result(result)
        assert len(report.results) == 1
        assert report.results[0] == result
    
    def test_get_summary(self):
        """Test summary calculation."""
        report = DiagnosticReport()
        
        # Add various results
        report.add_result(CheckResult("Test1", CheckCategory.SYSTEM, Severity.OK, "OK"))
        report.add_result(CheckResult("Test2", CheckCategory.SYSTEM, Severity.OK, "OK"))
        report.add_result(CheckResult("Test3", CheckCategory.SYSTEM, Severity.WARNING, "Warning"))
        report.add_result(CheckResult("Test4", CheckCategory.SYSTEM, Severity.ERROR, "Error"))
        
        summary = report.get_summary()
        
        assert summary["ok"] == 2
        assert summary["warning"] == 1
        assert summary["error"] == 1
        assert summary["info"] == 0
    
    def test_get_health_score(self):
        """Test health score calculation."""
        report = DiagnosticReport()
        
        # Perfect health
        assert report.get_health_score() == 100.0
        
        # Add some results
        report.add_result(CheckResult("Test1", CheckCategory.SYSTEM, Severity.OK, "OK"))
        report.add_result(CheckResult("Test2", CheckCategory.SYSTEM, Severity.OK, "OK"))
        assert report.get_health_score() == 100.0  # Capped at 100
        
        # Add warnings and errors
        report.add_result(CheckResult("Test3", CheckCategory.SYSTEM, Severity.WARNING, "Warning"))
        report.add_result(CheckResult("Test4", CheckCategory.SYSTEM, Severity.ERROR, "Error"))
        
        score = report.get_health_score()
        assert 0 <= score <= 100
        assert score < 100  # Should be reduced by warnings and errors
    
    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = DiagnosticReport()
        report.add_result(CheckResult(
            name="Test",
            category=CheckCategory.SYSTEM,
            severity=Severity.OK,
            message="OK",
            details="Details",
            fix_suggestion="Fix",
            can_auto_fix=True
        ))
        
        data = report.to_dict()
        
        assert "health_score" in data
        assert "summary" in data
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Test"
        assert data["results"][0]["severity"] == "ok"


class TestDoctorCommand:
    """Test DoctorCommand functionality."""
    
    @pytest.fixture
    def doctor(self, tmp_path):
        """Create a DoctorCommand instance with tmp directory."""
        with patch("src.daglab.commands.doctor.Path.cwd", return_value=tmp_path):
            return DoctorCommand()
    
    def test_check_python_version(self, doctor):
        """Test Python version check."""
        doctor._check_python_version()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Python Version"
        assert result.category == CheckCategory.SYSTEM
        
        # Should be OK for Python 3.10+
        if sys.version_info >= (3, 10):
            assert result.severity == Severity.OK
        else:
            assert result.severity == Severity.ERROR
    
    @patch("src.daglab.commands.doctor.import_module")
    def test_check_dagster_installed(self, mock_import, doctor):
        """Test Dagster installation check when installed."""
        # Mock successful import
        mock_dagster = MagicMock()
        mock_dagster.__version__ = "1.5.0"
        
        with patch.dict('sys.modules', {'dagster': mock_dagster}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                doctor._check_dagster()
        
        # Should have 2 results: package and CLI
        assert len(doctor.report.results) == 2
        
        # Check package result
        pkg_result = doctor.report.results[0]
        assert pkg_result.name == "Dagster"
        assert pkg_result.severity == Severity.OK
        assert "1.5.0" in pkg_result.message
        
        # Check CLI result
        cli_result = doctor.report.results[1]
        assert cli_result.name == "Dagster CLI"
        assert cli_result.severity == Severity.OK
    
    def test_check_dagster_not_installed(self, doctor):
        """Test Dagster installation check when not installed."""
        with patch.dict('sys.modules', {'dagster': None}):
            with patch("builtins.__import__", side_effect=ImportError):
                doctor._check_dagster()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Dagster"
        assert result.severity == Severity.ERROR
        assert result.can_auto_fix is True
        assert "pip install" in result.fix_command
    
    @patch("src.daglab.commands.doctor.import_module")
    def test_check_marimo_installed(self, mock_import, doctor):
        """Test Marimo installation check when installed."""
        # Mock successful import
        mock_marimo = MagicMock()
        mock_marimo.__version__ = "0.8.0"
        
        with patch.dict('sys.modules', {'marimo': mock_marimo}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                doctor._check_marimo()
        
        # Should have 2 results: package and CLI
        assert len(doctor.report.results) == 2
        
        # Check package result
        pkg_result = doctor.report.results[0]
        assert pkg_result.name == "Marimo"
        assert pkg_result.severity == Severity.OK
        assert "0.8.0" in pkg_result.message
    
    def test_check_configuration_missing(self, doctor, tmp_path):
        """Test configuration check when file is missing."""
        doctor._check_configuration()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Configuration File"
        assert result.severity == Severity.ERROR
        assert result.can_auto_fix is True
        assert "daglab init" in result.fix_command
    
    def test_check_configuration_valid(self, doctor, tmp_path):
        """Test configuration check with valid file."""
        # Create valid config
        config = {
            'project': {'name': 'test'},
            'dagster': {'port': 3000},
            'marimo': {'port': 2718}
        }
        config_path = tmp_path / "daglab.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        doctor._check_configuration()
        
        # Should have at least one OK result
        ok_results = [r for r in doctor.report.results if r.severity == Severity.OK]
        assert len(ok_results) > 0
        assert any(r.name == "Configuration File" for r in ok_results)
    
    def test_check_configuration_invalid_yaml(self, doctor, tmp_path):
        """Test configuration check with invalid YAML."""
        config_path = tmp_path / "daglab.yaml"
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        doctor._check_configuration()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Configuration File"
        assert result.severity == Severity.ERROR
        assert "Invalid YAML" in result.message
    
    @patch("socket.socket")
    def test_check_network(self, mock_socket_class, doctor, tmp_path):
        """Test network connectivity check."""
        # Create config with custom port
        config = {'dagster': {'port': 3001}}
        config_path = tmp_path / "daglab.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        # Mock socket
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0  # Success
        mock_socket_class.return_value = mock_socket
        
        doctor._check_network()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Dagster Connection"
        assert result.severity == Severity.OK
        assert "3001" in result.message
    
    @patch("socket.socket")
    def test_check_ports(self, mock_socket_class, doctor):
        """Test port availability check."""
        # Mock socket - port available
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1  # Connection refused = port available
        mock_socket_class.return_value = mock_socket
        
        doctor._check_ports()
        
        # Should check both Dagster and Marimo ports
        assert len(doctor.report.results) == 2
        for result in doctor.report.results:
            assert result.severity == Severity.OK
            assert "available" in result.message
    
    def test_check_directories(self, doctor, tmp_path):
        """Test directory structure check."""
        # Create some directories
        (tmp_path / "dagster_home").mkdir()
        (tmp_path / "notebooks").mkdir()
        
        doctor._check_directories()
        
        # Should have results for all required directories
        assert len(doctor.report.results) > 0
        
        # Check that existing directories are OK
        ok_dirs = [r for r in doctor.report.results if "dagster_home" in r.name]
        assert len(ok_dirs) > 0
        assert ok_dirs[0].severity == Severity.OK
    
    @patch("subprocess.run")
    def test_check_git_clean(self, mock_run, doctor, tmp_path):
        """Test Git repository check with clean working directory."""
        # Create .git directory
        (tmp_path / ".git").mkdir()
        
        # Mock git status - clean
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        doctor._check_git()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Git Repository"
        assert result.severity == Severity.OK
        assert "Clean" in result.message
    
    def test_check_git_not_repo(self, doctor, tmp_path):
        """Test Git check when not a repository."""
        doctor._check_git()
        
        assert len(doctor.report.results) == 1
        result = doctor.report.results[0]
        assert result.name == "Git Repository"
        assert result.severity == Severity.INFO
        assert result.can_auto_fix is True
        assert "git init" in result.fix_command
    
    @patch.dict(os.environ, {"DAGSTER_HOME": "/tmp/dagster"})
    def test_check_environment_with_vars(self, doctor):
        """Test environment check with variables set."""
        doctor._check_environment()
        
        # Should have result for DAGSTER_HOME
        dagster_results = [r for r in doctor.report.results if "DAGSTER_HOME" in r.name]
        assert len(dagster_results) > 0
        assert dagster_results[0].severity == Severity.OK
        assert "/tmp/dagster" in dagster_results[0].details
    
    @patch("subprocess.run")
    def test_check_deep_dependencies(self, mock_run, doctor):
        """Test deep dependency analysis."""
        # Mock outdated packages
        outdated = [
            {"name": "dagster", "version": "1.4.0", "latest_version": "1.5.0"},
            {"name": "marimo", "version": "0.7.0", "latest_version": "0.8.0"}
        ]
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(outdated)
        )
        
        doctor._check_deep_dependencies()
        
        # Should have warnings for outdated packages
        warnings = [r for r in doctor.report.results if r.severity == Severity.WARNING]
        assert len(warnings) == 2
        assert all(r.can_auto_fix for r in warnings)
        assert all("pip install --upgrade" in r.fix_command for r in warnings)
    
    @patch("subprocess.run")
    def test_apply_fixes(self, mock_run, doctor, capsys):
        """Test applying automatic fixes."""
        # Add some fixable results
        doctor.report.add_result(CheckResult(
            name="Test Fix",
            category=CheckCategory.SYSTEM,
            severity=Severity.ERROR,
            message="Needs fixing",
            can_auto_fix=True,
            fix_command="echo fixed"
        ))
        
        mock_run.return_value = Mock(returncode=0)
        
        doctor._apply_fixes()
        
        # Check that fix was attempted
        mock_run.assert_called_once()
        
        # Check output
        captured = capsys.readouterr()
        assert "Applying automatic fixes" in captured.out
        assert "Fixed: echo fixed" in captured.out
    
    def test_output_json(self, doctor, capsys):
        """Test JSON output."""
        doctor.report.add_result(CheckResult(
            name="Test",
            category=CheckCategory.SYSTEM,
            severity=Severity.OK,
            message="OK"
        ))
        
        doctor._output_json()
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        assert "health_score" in data
        assert "summary" in data
        assert "results" in data
        assert len(data["results"]) == 1
    
    @patch("src.daglab.commands.doctor.Console")
    def test_run_complete_flow(self, mock_console, doctor):
        """Test complete run flow."""
        # Mock all check methods
        doctor._check_python_version = MagicMock()
        doctor._check_dagster = MagicMock()
        doctor._check_marimo = MagicMock()
        doctor._check_configuration = MagicMock()
        doctor._check_network = MagicMock()
        doctor._check_ports = MagicMock()
        doctor._check_directories = MagicMock()
        doctor._check_git = MagicMock()
        doctor._check_environment = MagicMock()
        doctor._check_deep_dependencies = MagicMock()
        doctor._apply_fixes = MagicMock()
        doctor._output_human_readable = MagicMock()
        
        # Run with all options
        doctor.run(fix=True, check_deps=True, json_output=False)
        
        # Verify all checks were called
        doctor._check_python_version.assert_called_once()
        doctor._check_dagster.assert_called_once()
        doctor._check_marimo.assert_called_once()
        doctor._check_configuration.assert_called_once()
        doctor._check_network.assert_called_once()
        doctor._check_ports.assert_called_once()
        doctor._check_directories.assert_called_once()
        doctor._check_git.assert_called_once()
        doctor._check_environment.assert_called_once()
        doctor._check_deep_dependencies.assert_called_once()
        doctor._apply_fixes.assert_called_once()
        doctor._output_human_readable.assert_called_once()


class TestDoctorCLI:
    """Test the CLI interface."""
    
    @patch("src.daglab.commands.doctor.DoctorCommand")
    def test_doctor_cli_basic(self, mock_doctor_class):
        """Test basic CLI invocation."""
        from click.testing import CliRunner
        from src.daglab.commands.doctor import doctor
        
        mock_doctor = MagicMock()
        mock_doctor_class.return_value = mock_doctor
        
        runner = CliRunner()
        result = runner.invoke(doctor)
        
        assert result.exit_code == 0
        mock_doctor.run.assert_called_once_with(
            fix=False,
            check_deps=False,
            json_output=False
        )
    
    @patch("src.daglab.commands.doctor.DoctorCommand")
    def test_doctor_cli_with_options(self, mock_doctor_class):
        """Test CLI with all options."""
        from click.testing import CliRunner
        from src.daglab.commands.doctor import doctor
        
        mock_doctor = MagicMock()
        mock_doctor_class.return_value = mock_doctor
        
        runner = CliRunner()
        result = runner.invoke(doctor, ['--fix', '--check-deps', '--json'])
        
        assert result.exit_code == 0
        mock_doctor.run.assert_called_once_with(
            fix=True,
            check_deps=True,
            json_output=True
        )