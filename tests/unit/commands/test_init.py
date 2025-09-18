"""Tests for the dagster init command."""

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml
from click.testing import CliRunner

from daglab.commands.dagster_init import (
    dagster_init_command,
    detect_dagster_project,
    is_port_available,
    get_available_port,
    create_daglab_config,
    create_project_structure,
    update_gitignore,
)


class TestProjectDetection:
    """Test Dagster project detection."""
    
    def test_detect_dagster_yaml(self, tmp_path):
        """Test detection via dagster.yaml."""
        (tmp_path / "dagster.yaml").touch()
        is_dagster, project_type = detect_dagster_project(tmp_path)
        assert is_dagster is True
        assert project_type == "dagster.yaml"
    
    def test_detect_workspace_yaml(self, tmp_path):
        """Test detection via workspace.yaml."""
        (tmp_path / "workspace.yaml").touch()
        is_dagster, project_type = detect_dagster_project(tmp_path)
        assert is_dagster is True
        assert project_type == "workspace.yaml"
    
    def test_detect_pyproject_toml(self, tmp_path):
        """Test detection via pyproject.toml with dagster dependency."""
        pyproject_content = """
[tool.poetry.dependencies]
dagster = "^1.5"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        
        with patch("daglab.commands.dagster_init.tomli.load") as mock_load:
            mock_load.return_value = {
                "tool": {"poetry": {"dependencies": {"dagster": "^1.5"}}}
            }
            is_dagster, project_type = detect_dagster_project(tmp_path)
            assert is_dagster is True
            assert project_type == "pyproject.toml"
    
    def test_no_dagster_project(self, tmp_path):
        """Test when no Dagster project is detected."""
        is_dagster, project_type = detect_dagster_project(tmp_path)
        assert is_dagster is False
        assert project_type == ""


class TestPortAvailability:
    """Test port availability functions."""
    
    def test_port_available(self):
        """Test checking if port is available."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.bind.return_value = None
            
            assert is_port_available(8888) is True
    
    def test_port_unavailable(self):
        """Test checking if port is unavailable."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.bind.side_effect = OSError()
            
            assert is_port_available(8888) is False
    
    def test_get_available_port(self):
        """Test finding available port."""
        with patch("daglab.commands.init.is_port_available") as mock_available:
            mock_available.side_effect = [False, False, True]
            port = get_available_port(8888)
            assert port == 8890
    
    def test_no_available_ports(self):
        """Test when no ports are available."""
        with patch("daglab.commands.init.is_port_available") as mock_available:
            mock_available.return_value = False
            with pytest.raises(RuntimeError, match="No available ports found"):
                get_available_port(65534)


class TestConfigCreation:
    """Test configuration creation."""
    
    def test_create_standard_config(self, tmp_path):
        """Test creating standard configuration."""
        config = create_daglab_config(
            tmp_path,
            "notebooks",
            3000,
            8888,
            "standard"
        )
        
        assert config["project"]["name"] == tmp_path.name
        assert config["project"]["type"] == "standard"
        assert config["project"]["notebooks_dir"] == "notebooks"
        assert config["server"]["port"] == 8888
        assert config["server"]["dagster_port"] == 3000
        assert config["notebooks"]["default_kernel"] == "python3"
    
    def test_create_ml_config(self, tmp_path):
        """Test creating ML configuration."""
        config = create_daglab_config(
            tmp_path,
            "notebooks",
            3000,
            8888,
            "ml"
        )
        
        assert "ml" in config
        assert "pandas" in config["ml"]["frameworks"]
        assert config["ml"]["data_dir"] == "data/"
        assert config["ml"]["models_dir"] == "models/"


class TestProjectStructure:
    """Test project structure creation."""
    
    def test_create_structure_no_examples(self, tmp_path):
        """Test creating structure without examples."""
        create_project_structure(
            tmp_path,
            "notebooks",
            create_examples=False,
            template="standard",
            force=False
        )
        
        assert (tmp_path / ".daglab").exists()
        assert (tmp_path / ".daglab" / "cache").exists()
        assert (tmp_path / ".daglab" / "logs").exists()
        assert (tmp_path / ".daglab" / "tmp").exists()
        assert (tmp_path / "notebooks").exists()
    
    @patch("shutil.copy2")
    def test_create_structure_with_examples(self, mock_copy, tmp_path):
        """Test creating structure with examples."""
        # Mock template directory existence
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.glob") as mock_glob:
                mock_glob.return_value = [Path("example.ipynb")]
                
                create_project_structure(
                    tmp_path,
                    "notebooks",
                    create_examples=True,
                    template="standard",
                    force=False
                )
                
                # Should try to copy example notebook
                assert mock_copy.called


class TestGitignoreUpdate:
    """Test .gitignore updates."""
    
    def test_update_existing_gitignore(self, tmp_path):
        """Test updating existing .gitignore."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("# Existing content\n*.pyc\n")
        
        update_gitignore(tmp_path)
        
        content = gitignore_path.read_text()
        assert ".daglab/" in content
        assert "# Existing content" in content
    
    def test_create_new_gitignore(self, tmp_path):
        """Test creating new .gitignore."""
        update_gitignore(tmp_path)
        
        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert ".daglab/" in content
        assert "dagster.db" in content


class TestInitCommand:
    """Test the main init command."""
    
    def test_init_in_dagster_project(self, tmp_path):
        """Test initializing in existing Dagster project."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create a Dagster project
            Path("dagster.yaml").touch()
            
            result = runner.invoke(dagster_init_command, [])
            
            assert result.exit_code == 0
            assert "Detected Dagster project" in result.output
            assert "Daglab initialized successfully" in result.output
            assert Path("daglab.yaml").exists()
            assert Path(".daglab").exists()
    
    def test_init_no_dagster_project(self, tmp_path):
        """Test init without Dagster project (should suggest bootstrap)."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(dagster_init_command, [])
            
            assert "No Dagster project detected" in result.output
            assert "--bootstrap" in result.output
    
    def test_init_with_bootstrap(self, tmp_path):
        """Test init with bootstrap flag."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("daglab.commands.dagster_init.create_bootstrap_project") as mock_bootstrap:
                result = runner.invoke(dagster_init_command, ["--bootstrap"])
                
                assert result.exit_code == 0
                mock_bootstrap.assert_called_once()
                assert "Created Dagster project" in result.output
    
    def test_init_custom_ports(self, tmp_path):
        """Test init with custom ports."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("dagster.yaml").touch()
            
            result = runner.invoke(
                init_command,
                ["--dagster-port", "4000", "--daglab-port", "9999"]
            )
            
            assert result.exit_code == 0
            config = yaml.safe_load(Path("daglab.yaml").read_text())
            assert config["server"]["dagster_port"] == 4000
            assert config["server"]["daglab_port"] == 9999
    
    def test_init_port_conflict(self, tmp_path):
        """Test init with port conflicts."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("dagster.yaml").touch()
            
            with patch("daglab.commands.dagster_init.is_port_available") as mock_available:
                mock_available.side_effect = [False, True, True]
                with patch("daglab.commands.dagster_init.get_available_port") as mock_get_port:
                    mock_get_port.return_value = 3001
                    
                    result = runner.invoke(dagster_init_command, [])
                    
                    assert "Port 3000 is in use, using 3001 instead" in result.output
    
    def test_init_force_overwrite(self, tmp_path):
        """Test force overwrite of existing files."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("dagster.yaml").touch()
            Path("daglab.yaml").write_text("existing: config")
            
            result = runner.invoke(init_command, ["--force"])
            
            assert result.exit_code == 0
            config = yaml.safe_load(Path("daglab.yaml").read_text())
            assert "existing" not in config
    
    def test_init_decline_overwrite(self, tmp_path):
        """Test declining to overwrite existing files."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("dagster.yaml").touch()
            Path("daglab.yaml").write_text("existing: config")
            
            result = runner.invoke(init_command, [], input="n\n")
            
            assert "daglab.yaml already exists" in result.output
            assert "Aborted" in result.output
    
    def test_init_with_template(self, tmp_path):
        """Test init with different templates."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("dagster.yaml").touch()
            
            result = runner.invoke(init_command, ["--template", "ml"])
            
            assert result.exit_code == 0
            config = yaml.safe_load(Path("daglab.yaml").read_text())
            assert config["project"]["type"] == "ml"
            assert "ml" in config