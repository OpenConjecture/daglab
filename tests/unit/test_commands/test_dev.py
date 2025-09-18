"""Tests for dev command - Phase 5."""

import pytest
from typer.testing import CliRunner
from daglab.commands.dev import app


class TestDevCommand:
    """Test dev command stub."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_dev_command_exists(self):
        """Test that dev command exists and shows placeholder."""
        result = self.runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Coming in Phase 5" in result.stdout
        assert "Development Environment" in result.stdout
    
    def test_dev_with_dagster_port_option(self):
        """Test dev command accepts dagster-port option."""
        result = self.runner.invoke(app, ["--dagster-port", "4000"])
        assert result.exit_code == 0
        assert "dagster_port=4000" in result.stdout
    
    def test_dev_with_marimo_port_option(self):
        """Test dev command accepts marimo-port option."""
        result = self.runner.invoke(app, ["--marimo-port", "3000"])
        assert result.exit_code == 0
        assert "marimo_port=3000" in result.stdout
    
    def test_dev_with_no_auto_reload_flag(self):
        """Test dev command accepts no-auto-reload flag."""
        result = self.runner.invoke(app, ["--no-auto-reload"])
        assert result.exit_code == 0
        assert "Coming in Phase 5" in result.stdout
    
    def test_dev_help(self):
        """Test dev help output."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "dagster-port" in result.stdout
        assert "marimo-port" in result.stdout
        assert "auto-reload" in result.stdout
