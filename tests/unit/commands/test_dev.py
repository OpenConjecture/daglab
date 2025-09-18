"""Tests for dev command."""

import os
import sys
import time
from unittest.mock import Mock, patch, MagicMock
import pytest
from typer.testing import CliRunner

from daglab.commands.dev import app, DevEnvironment
from daglab.helpers.process import ProcessManager, ProcessState, ProcessInfo
from daglab.helpers.ports import PortManager
from daglab.helpers.browser import BrowserManager


@pytest.fixture
def runner():
    """CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def mock_process_manager():
    """Mock process manager."""
    with patch('daglab.commands.dev.ProcessManager') as mock:
        manager = Mock()
        mock.return_value = manager
        
        # Setup default behaviors
        manager.register.return_value = ProcessInfo(
            name="test",
            command=["test"],
            state=ProcessState.STOPPED
        )
        manager.start.return_value = True
        manager.stop.return_value = True
        manager.wait_for_ready.return_value = True
        manager.get_status.return_value = {
            "dagster": {
                "state": "running",
                "pid": 1234,
                "cpu_percent": 2.5,
                "memory_mb": 150.0,
                "uptime": "00:05:00"
            },
            "marimo": {
                "state": "running",
                "pid": 1235,
                "cpu_percent": 1.2,
                "memory_mb": 120.0,
                "uptime": "00:05:00"
            }
        }
        
        yield manager


@pytest.fixture
def mock_port_manager():
    """Mock port manager."""
    with patch('daglab.commands.dev.PortManager') as mock:
        manager = Mock()
        mock.return_value = manager
        
        # Setup default behaviors
        manager.allocate_port.side_effect = lambda name, preferred, range_name: preferred
        manager.is_port_available.return_value = True
        
        yield manager


@pytest.fixture
def mock_browser_manager():
    """Mock browser manager."""
    with patch('daglab.commands.dev.BrowserManager') as mock:
        manager = Mock()
        mock.return_value = manager
        
        # Setup default behaviors
        manager.open_url.return_value = True
        manager.open_multiple.return_value = 2
        manager.detect_browsers.return_value = ["chrome", "firefox"]
        
        yield manager


class TestDevCommand:
    """Test dev command functionality."""
    
    def test_dev_help(self, runner):
        """Test dev command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Development environment tools" in result.stdout
        
    def test_dev_default_options(self, runner, mock_process_manager, mock_port_manager, mock_browser_manager):
        """Test dev command with default options."""
        with patch('daglab.commands.dev.DevEnvironment.check_dependencies', return_value=[]):
            with patch('daglab.commands.dev.DevEnvironment.run_interactive'):
                result = runner.invoke(app)
                
                assert result.exit_code == 0
                
    def test_dev_custom_ports(self, runner, mock_process_manager, mock_port_manager, mock_browser_manager):
        """Test dev command with custom ports."""
        with patch('daglab.commands.dev.DevEnvironment.check_dependencies', return_value=[]):
            with patch('daglab.commands.dev.DevEnvironment.run_interactive'):
                result = runner.invoke(app, ["--dagster-port", "4000", "--marimo-port", "3000"])
                
                assert result.exit_code == 0
                
    def test_dev_ci_mode(self, runner, mock_process_manager, mock_port_manager, mock_browser_manager):
        """Test dev command in CI mode."""
        with patch('daglab.commands.dev.DevEnvironment.check_dependencies', return_value=[]):
            result = runner.invoke(app, ["--ci"])
            
            assert result.exit_code == 0
            assert "Environment started successfully" in result.stdout
            assert "Dagster UI:" in result.stdout
            assert "Marimo Editor:" in result.stdout
            
    def test_dev_missing_dependencies(self, runner):
        """Test dev command with missing dependencies."""
        with patch('daglab.commands.dev.DevEnvironment.check_dependencies', return_value=["dagster", "marimo"]):
            result = runner.invoke(app)
            
            assert result.exit_code == 1
            assert "Missing required dependencies" in result.stdout
            assert "dagster" in result.stdout
            assert "marimo" in result.stdout


class TestDevEnvironment:
    """Test DevEnvironment class."""
    
    def test_init_defaults(self):
        """Test DevEnvironment initialization with defaults."""
        env = DevEnvironment()
        
        assert env.dagster_port == 3000
        assert env.marimo_port == 2718
        assert env.auto_reload is True
        assert env.open_browser is True
        assert env.env_file is None
        assert env.sandbox_mode is False
        assert env.ci_mode is False
        
    def test_init_custom_values(self):
        """Test DevEnvironment initialization with custom values."""
        env = DevEnvironment(
            dagster_port=4000,
            marimo_port=3000,
            auto_reload=False,
            open_browser=False,
            env_file="custom.env",
            sandbox_mode=True,
            ci_mode=True
        )
        
        assert env.dagster_port == 4000
        assert env.marimo_port == 3000
        assert env.auto_reload is False
        assert env.open_browser is False
        assert env.env_file == "custom.env"
        assert env.sandbox_mode is True
        assert env.ci_mode is True
        
    def test_ci_mode_from_env(self):
        """Test CI mode detection from environment."""
        with patch.dict(os.environ, {"CI": "true"}):
            env = DevEnvironment()
            assert env.ci_mode is True
            
    def test_load_environment_with_file(self, tmp_path):
        """Test loading environment from specific file."""
        env_file = tmp_path / "test.env"
        env_file.write_text("TEST_VAR=test_value\n")
        
        env = DevEnvironment(env_file=str(env_file))
        
        with patch('daglab.commands.dev.load_dotenv') as mock_load:
            env.load_environment()
            mock_load.assert_called_once_with(str(env_file))
            
    def test_load_environment_default(self, tmp_path, monkeypatch):
        """Test loading environment from default .env file."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("DEFAULT_VAR=default_value\n")
        
        env = DevEnvironment()
        
        with patch('daglab.commands.dev.load_dotenv') as mock_load:
            env.load_environment()
            mock_load.assert_called_once()
            
    def test_check_dependencies_all_present(self):
        """Test dependency check when all are present."""
        env = DevEnvironment()
        
        with patch.dict(sys.modules, {
            'dagster': MagicMock(),
            'marimo': MagicMock(),
            'psutil': MagicMock()
        }):
            missing = env.check_dependencies()
            assert missing == []
            
    def test_check_dependencies_some_missing(self):
        """Test dependency check when some are missing."""
        env = DevEnvironment()
        
        # Mock imports to raise ImportError for specific modules
        def mock_import(name, *args):
            if name in ['dagster', 'marimo']:
                raise ImportError(f"No module named '{name}'")
            return MagicMock()
            
        with patch('builtins.__import__', side_effect=mock_import):
            missing = env.check_dependencies()
            assert 'dagster' in missing
            assert 'marimo' in missing
            assert 'psutil' not in missing
            
    def test_allocate_ports_success(self):
        """Test successful port allocation."""
        env = DevEnvironment(dagster_port=3000, marimo_port=2718)
        
        with patch.object(env.port_manager, 'allocate_port') as mock_allocate:
            mock_allocate.side_effect = lambda name, preferred, range_name: preferred
            
            result = env.allocate_ports()
            
            assert result is True
            assert env.dagster_port == 3000
            assert env.marimo_port == 2718
            assert env.urls["dagster"] == "http://localhost:3000"
            assert env.urls["marimo"] == "http://localhost:2718"
            
    def test_allocate_ports_with_conflicts(self):
        """Test port allocation with conflicts."""
        env = DevEnvironment(dagster_port=3000, marimo_port=2718)
        
        with patch.object(env.port_manager, 'allocate_port') as mock_allocate:
            # Simulate port conflicts - return different ports
            mock_allocate.side_effect = [3001, 2719]
            
            result = env.allocate_ports()
            
            assert result is True
            assert env.dagster_port == 3001
            assert env.marimo_port == 2719
            assert env.urls["dagster"] == "http://localhost:3001"
            assert env.urls["marimo"] == "http://localhost:2719"
            
    def test_allocate_ports_failure(self):
        """Test port allocation failure."""
        env = DevEnvironment()
        
        with patch.object(env.port_manager, 'allocate_port') as mock_allocate:
            mock_allocate.side_effect = RuntimeError("No available ports")
            
            result = env.allocate_ports()
            
            assert result is False
            
    def test_setup_processes_basic(self):
        """Test basic process setup."""
        env = DevEnvironment(dagster_port=3000, marimo_port=2718)
        
        with patch.object(env.process_manager, 'register') as mock_register:
            env.setup_processes()
            
            assert mock_register.call_count == 2
            
            # Check Dagster registration
            dagster_call = mock_register.call_args_list[0]
            assert dagster_call[0][0] == "dagster"
            assert "-m" in dagster_call[0][1]
            assert "dagster" in dagster_call[0][1]
            assert "3000" in dagster_call[0][1]
            
            # Check Marimo registration
            marimo_call = mock_register.call_args_list[1]
            assert marimo_call[0][0] == "marimo"
            assert "-m" in marimo_call[0][1]
            assert "marimo" in marimo_call[0][1]
            assert "2718" in marimo_call[0][1]
            
    def test_setup_processes_with_options(self):
        """Test process setup with various options."""
        env = DevEnvironment(
            dagster_port=3000,
            marimo_port=2718,
            auto_reload=True,
            sandbox_mode=True,
            ci_mode=True
        )
        
        with patch.object(env.process_manager, 'register') as mock_register:
            env.setup_processes()
            
            # Check Dagster has auto-reload and sandbox options
            dagster_call = mock_register.call_args_list[0]
            dagster_cmd = dagster_call[0][1]
            assert "--reload" in dagster_cmd
            assert "--graphql-sandbox" in dagster_cmd
            
            # Check Marimo has headless option
            marimo_call = mock_register.call_args_list[1]
            marimo_cmd = marimo_call[0][1]
            assert "--headless" in marimo_cmd
            
    def test_start_success(self):
        """Test successful environment start."""
        env = DevEnvironment(open_browser=False)
        env.allocate_ports()
        
        with patch.object(env.process_manager, 'start', return_value=True):
            with patch.object(env.process_manager, 'wait_for_ready', return_value=True):
                result = env.start()
                
                assert result is True
                assert env.is_running is True
                assert env.start_time is not None
                
    def test_start_process_failure(self):
        """Test environment start with process failure."""
        env = DevEnvironment()
        env.allocate_ports()
        
        with patch.object(env.process_manager, 'start', side_effect=[False, True]):
            result = env.start()
            
            assert result is False
            
    def test_start_readiness_failure(self):
        """Test environment start with readiness check failure."""
        env = DevEnvironment()
        env.allocate_ports()
        
        with patch.object(env.process_manager, 'start', return_value=True):
            with patch.object(env.process_manager, 'wait_for_ready', return_value=False):
                result = env.start()
                
                assert result is False
                
    def test_start_with_browser_opening(self):
        """Test environment start with browser opening."""
        env = DevEnvironment(open_browser=True, ci_mode=False)
        env.allocate_ports()
        
        with patch.object(env.process_manager, 'start', return_value=True):
            with patch.object(env.process_manager, 'wait_for_ready', return_value=True):
                with patch.object(env.browser_manager, 'open_multiple') as mock_open:
                    result = env.start()
                    
                    assert result is True
                    mock_open.assert_called_once()
                    urls = mock_open.call_args[0][0]
                    assert len(urls) == 2
                    assert "dagster" in urls[0]
                    assert "marimo" in urls[1]
                    
    def test_display_status(self, capsys):
        """Test status display."""
        env = DevEnvironment()
        env.urls = {
            "dagster": "http://localhost:3000",
            "marimo": "http://localhost:2718"
        }
        env.start_time = time.time()
        
        with patch.object(env.process_manager, 'get_status') as mock_status:
            mock_status.return_value = {
                "dagster": {
                    "state": "running",
                    "pid": 1234,
                    "cpu_percent": 2.5,
                    "memory_mb": 150.0
                },
                "marimo": {
                    "state": "stopped",
                    "pid": None,
                    "cpu_percent": 0,
                    "memory_mb": 0
                }
            }
            
            env.display_status()
            
            captured = capsys.readouterr()
            assert "Development Environment" in captured.out
            assert "Dagster" in captured.out
            assert "Marimo" in captured.out
            assert "running" in captured.out
            assert "stopped" in captured.out
            
    def test_stop(self):
        """Test environment stop."""
        env = DevEnvironment()
        env.is_running = True
        
        with patch.object(env.process_manager, 'shutdown_all') as mock_shutdown:
            with patch.object(env.port_manager, 'release_all') as mock_release:
                env.stop()
                
                assert env.is_running is False
                mock_shutdown.assert_called_once()
                mock_release.assert_called_once()
                
    def test_run_interactive_success(self):
        """Test interactive mode success."""
        env = DevEnvironment()
        
        with patch.object(env, 'start', return_value=True):
            with patch.object(env, 'display_status'):
                with patch.object(env, 'stop'):
                    # Simulate Ctrl+C after brief delay
                    def side_effect():
                        time.sleep(0.1)
                        raise KeyboardInterrupt()
                        
                    with patch('time.sleep', side_effect=side_effect):
                        env.run_interactive()
                        
                        env.start.assert_called_once()
                        env.display_status.assert_called_once()
                        env.stop.assert_called_once()
                        
    def test_run_interactive_start_failure(self):
        """Test interactive mode with start failure."""
        env = DevEnvironment()
        
        with patch.object(env, 'start', return_value=False):
            with patch.object(env, 'display_status') as mock_display:
                with patch.object(env, 'stop') as mock_stop:
                    env.run_interactive()
                    
                    env.start.assert_called_once()
                    mock_display.assert_not_called()
                    mock_stop.assert_not_called()