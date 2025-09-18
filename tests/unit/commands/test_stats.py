"""Tests for the stats command."""

import json
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from typer.testing import CliRunner

from daglab.commands.stats import app, StatsCollector, StatsFormatter
from daglab.helpers.state import StateManager


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def state_manager(tmp_path):
    """Create a temporary state manager."""
    db_path = tmp_path / "test_state.db"
    return StateManager(db_path=db_path, namespace="stats")


@pytest.fixture
def mock_stats_data(state_manager):
    """Populate state with mock statistics data."""
    # Add command history
    commands = []
    base_time = datetime.now() - timedelta(days=10)
    
    for i in range(50):
        cmd = {
            "command": "new" if i % 3 == 0 else "run" if i % 2 == 0 else "list",
            "timestamp": (base_time + timedelta(hours=i * 4)).isoformat(),
            "success": i % 7 != 0,  # Some failures
            "duration": 0.5 + (i % 10) * 0.1,
        }
        commands.append(cmd)
    
    state_manager.set("command_history", commands)
    
    # Add notebook history
    notebooks = []
    for i in range(20):
        nb = {
            "created_at": (base_time + timedelta(days=i // 2)).isoformat(),
            "template": "ml" if i % 3 == 0 else "analysis" if i % 2 == 0 else "custom",
            "cell_count": 10 + i % 20,
        }
        notebooks.append(nb)
    
    state_manager.set("notebook_history", notebooks)
    
    # Add error log
    errors = []
    for i in range(10):
        err = {
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "type": "NetworkError" if i % 3 == 0 else "ValidationError",
        }
        errors.append(err)
    
    state_manager.set("error_log", errors)
    
    return state_manager


class TestStatsCollector:
    """Test the StatsCollector class."""
    
    def test_get_time_range(self):
        """Test time range calculation."""
        collector = StatsCollector()
        
        # Test today
        start, end = collector._get_time_range("today")
        assert start.date() == datetime.now().date()
        assert end > start
        
        # Test week
        start, end = collector._get_time_range("week")
        assert (end - start).days >= 6
        
        # Test all
        start, end = collector._get_time_range("all")
        assert start.year == 2020
    
    def test_collect_command_stats(self, mock_stats_data):
        """Test command statistics collection."""
        collector = StatsCollector()
        collector.state_manager = mock_stats_data
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        
        stats = collector.collect_command_stats(start, end)
        
        assert "total_commands" in stats
        assert "command_counts" in stats
        assert "success_rate" in stats
        assert stats["total_commands"] > 0
        assert 0 <= stats["success_rate"] <= 1
    
    def test_collect_notebook_stats(self, mock_stats_data):
        """Test notebook statistics collection."""
        collector = StatsCollector()
        collector.state_manager = mock_stats_data
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        
        stats = collector.collect_notebook_stats(start, end)
        
        assert "total_notebooks" in stats
        assert "template_usage" in stats
        assert "avg_cells_per_notebook" in stats
        assert stats["total_notebooks"] > 0
    
    def test_collect_error_stats(self, mock_stats_data):
        """Test error statistics collection."""
        collector = StatsCollector()
        collector.state_manager = mock_stats_data
        
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()
        
        stats = collector.collect_error_stats(start, end)
        
        assert "total_errors" in stats
        assert "error_types" in stats
        assert stats["total_errors"] > 0


class TestStatsFormatter:
    """Test the StatsFormatter class."""
    
    def test_format_json(self):
        """Test JSON formatting."""
        stats = {
            "command_stats": {"total_commands": 10},
            "notebook_stats": {"total_notebooks": 5},
        }
        
        formatted = StatsFormatter.format_json(stats)
        parsed = json.loads(formatted)
        
        assert parsed["command_stats"]["total_commands"] == 10
        assert parsed["notebook_stats"]["total_notebooks"] == 5
    
    def test_format_csv(self, tmp_path):
        """Test CSV export."""
        stats = {
            "command_stats": {
                "total_commands": 10,
                "success_rate": 0.9,
            },
            "notebook_stats": {
                "total_notebooks": 5,
            },
        }
        
        csv_path = tmp_path / "test_stats.csv"
        StatsFormatter.format_csv(stats, csv_path)
        
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "command_stats" in content
        assert "total_commands" in content
        assert "10" in content


class TestStatsCommand:
    """Test the stats command CLI."""
    
    def test_stats_default(self, runner, mock_stats_data, monkeypatch):
        """Test default stats command."""
        # Monkeypatch the state manager to use our mock
        def mock_state_manager(*args, **kwargs):
            return mock_stats_data
        
        import daglab.commands.stats
        monkeypatch.setattr(daglab.commands.stats, "StateManager", mock_state_manager)
        
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        # Output should contain statistics
        assert "Total" in result.output or "Statistics" in result.output
    
    def test_stats_json_format(self, runner, mock_stats_data, monkeypatch):
        """Test JSON format output."""
        def mock_state_manager(*args, **kwargs):
            return mock_stats_data
        
        import daglab.commands.stats
        monkeypatch.setattr(daglab.commands.stats, "StateManager", mock_state_manager)
        
        result = runner.invoke(app, ["--format", "json"])
        assert result.exit_code == 0
        
        # Should be valid JSON
        try:
            json.loads(result.output)
        except json.JSONDecodeError:
            # Output might contain other text, try to extract JSON
            lines = result.output.strip().split('\n')
            json_start = next(i for i, line in enumerate(lines) if line.strip().startswith('{'))
            json_text = '\n'.join(lines[json_start:])
            json.loads(json_text)
    
    def test_stats_with_period(self, runner, mock_stats_data, monkeypatch):
        """Test stats with different time periods."""
        def mock_state_manager(*args, **kwargs):
            return mock_stats_data
        
        import daglab.commands.stats
        monkeypatch.setattr(daglab.commands.stats, "StateManager", mock_state_manager)
        
        for period in ["today", "week", "month", "year"]:
            result = runner.invoke(app, ["--period", period])
            assert result.exit_code == 0
    
    def test_stats_with_since(self, runner, mock_stats_data, monkeypatch):
        """Test stats with since date."""
        def mock_state_manager(*args, **kwargs):
            return mock_stats_data
        
        import daglab.commands.stats
        monkeypatch.setattr(daglab.commands.stats, "StateManager", mock_state_manager)
        
        since_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        result = runner.invoke(app, ["--since", since_date])
        assert result.exit_code == 0
    
    def test_stats_invalid_since(self, runner):
        """Test stats with invalid since date."""
        result = runner.invoke(app, ["--since", "invalid-date"])
        assert result.exit_code == 1
        assert "Invalid date format" in result.output
    
    def test_stats_reset_command(self, runner, mock_stats_data, monkeypatch):
        """Test stats reset subcommand."""
        def mock_state_manager(*args, **kwargs):
            return mock_stats_data
        
        import daglab.commands.stats
        monkeypatch.setattr(daglab.commands.stats, "StateManager", mock_state_manager)
        
        # Test with confirmation
        result = runner.invoke(app, ["reset"], input="y\n")
        assert result.exit_code == 0
        assert "Statistics have been reset" in result.output
        
        # Test with cancellation
        result = runner.invoke(app, ["reset"], input="n\n")
        assert result.exit_code == 0
        assert "Reset cancelled" in result.output
    
    def test_stats_trends_command(self, runner):
        """Test trends subcommand."""
        result = runner.invoke(app, ["trends", "cpu"])
        assert result.exit_code == 0
        assert "Trend analysis complete" in result.output
        
        # Test with different metrics
        for metric in ["memory", "errors", "commands"]:
            result = runner.invoke(app, ["trends", metric, "--days", "14"])
            assert result.exit_code == 0