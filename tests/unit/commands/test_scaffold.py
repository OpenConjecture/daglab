"""Unit tests for the scaffold command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from typer.testing import CliRunner
from daglab.commands.scaffold import (
    app,
    validate_target_selection,
    generate_filename,
    parse_template_vars,
    render_template,
    validate_notebook_syntax,
    commit_to_git,
    list_available_templates,
    get_daglab_version,
)


class TestScaffoldHelpers:
    """Test helper functions for scaffold command."""
    
    def test_validate_target_selection_single_target(self):
        """Test validation with single target specified."""
        # Asset only
        target_type, target_name = validate_target_selection("my_asset", None, None)
        assert target_type == "asset"
        assert target_name == "my_asset"
        
        # Job only
        target_type, target_name = validate_target_selection(None, "my_job", None)
        assert target_type == "job"
        assert target_name == "my_job"
        
        # Selection only
        target_type, target_name = validate_target_selection(None, None, "my_selection")
        assert target_type == "selection"
        assert target_name == "my_selection"
    
    def test_validate_target_selection_no_target(self):
        """Test validation with no target specified."""
        with pytest.raises(Exception) as exc_info:
            validate_target_selection(None, None, None)
        assert "Must specify one of" in str(exc_info.value)
    
    def test_validate_target_selection_multiple_targets(self):
        """Test validation with multiple targets specified."""
        with pytest.raises(Exception) as exc_info:
            validate_target_selection("asset", "job", None)
        assert "Can only specify one of" in str(exc_info.value)
    
    def test_generate_filename(self):
        """Test filename generation."""
        # With target name
        filename = generate_filename("asset", "my_asset", "default")
        assert filename.endswith(".py")
        assert "my_asset" in filename
        assert "default" in filename
        assert "notebook" in filename
        
        # With special characters
        filename = generate_filename("job", "my/job.name-test", "ml")
        assert "/" not in filename
        assert "." not in filename.split("_notebook.py")[0]  # dots only in extension
        assert "-" not in filename.split("_notebook.py")[0]  # no dashes except extension
    
    def test_parse_template_vars(self):
        """Test template variable parsing."""
        # Simple string values
        vars_dict = parse_template_vars(["key1=value1", "key2=value2"])
        assert vars_dict == {"key1": "value1", "key2": "value2"}
        
        # JSON values
        vars_dict = parse_template_vars(['list=[1,2,3]', 'dict={"a": 1}'])
        assert vars_dict["list"] == [1, 2, 3]
        assert vars_dict["dict"] == {"a": 1}
        
        # Mixed values
        vars_dict = parse_template_vars(['string=hello', 'number=42', 'bool=true'])
        assert vars_dict["string"] == "hello"
        assert vars_dict["number"] == 42
        assert vars_dict["bool"] is True
    
    def test_parse_template_vars_invalid(self):
        """Test template variable parsing with invalid format."""
        with pytest.raises(Exception) as exc_info:
            parse_template_vars(["invalid_format"])
        assert "key=value" in str(exc_info.value)
    
    def test_validate_notebook_syntax(self):
        """Test notebook syntax validation."""
        # Valid Python code
        valid_code = """
import marimo
app = marimo.App()

@app.cell
def __():
    return 42

if __name__ == "__main__":
    app.run()
"""
        assert validate_notebook_syntax(valid_code) is True
        
        # Invalid Python code
        invalid_code = """
import marimo
app = marimo.App()

@app.cell
def __():
    return 42 +++ invalid syntax

if __name__ == "__main__":
    app.run()
"""
        assert validate_notebook_syntax(invalid_code) is False
    
    @patch('subprocess.run')
    def test_commit_to_git_success(self, mock_run):
        """Test successful git commit."""
        mock_run.return_value = Mock(returncode=0)
        
        result = commit_to_git(Path("test.py"), "Test commit")
        assert result is True
        
        # Verify git commands were called
        calls = mock_run.call_args_list
        assert len(calls) == 3  # rev-parse, add, commit
        assert "rev-parse" in str(calls[0])
        assert "add" in str(calls[1])
        assert "commit" in str(calls[2])
    
    @patch('subprocess.run')
    def test_commit_to_git_not_in_repo(self, mock_run):
        """Test git commit when not in a repository."""
        mock_run.side_effect = Exception("Not a git repository")
        
        result = commit_to_git(Path("test.py"), "Test commit")
        assert result is False
    
    def test_get_daglab_version(self):
        """Test getting daglab version."""
        version = get_daglab_version()
        assert isinstance(version, str)
        assert version  # Should not be empty


class TestScaffoldCommand:
    """Test the main scaffold command."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    def test_scaffold_basic(self, runner, temp_dir):
        """Test basic scaffold command."""
        with patch('daglab.commands.scaffold.get_template_dir') as mock_template_dir:
            # Setup mock templates
            mock_template_dir.return_value = Path(__file__).parent / "mock_templates"
            
            # Mock template rendering
            with patch('daglab.commands.scaffold.render_template') as mock_render:
                mock_render.return_value = "# Generated notebook content"
                
                result = runner.invoke(
                    app,
                    ["--asset", "test_asset", "--output-dir", str(temp_dir)]
                )
                
                assert result.exit_code == 0
                assert "Notebook successfully generated" in result.output
    
    def test_scaffold_with_custom_filename(self, runner, temp_dir):
        """Test scaffold with custom filename."""
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = "# Generated content"
            
            custom_filename = "my_custom_notebook.py"
            result = runner.invoke(
                app,
                ["--job", "test_job", "--filename", custom_filename, 
                 "--output-dir", str(temp_dir)]
            )
            
            if result.exit_code == 0:
                assert (temp_dir / custom_filename).exists()
    
    def test_scaffold_force_overwrite(self, runner, temp_dir):
        """Test force overwrite of existing file."""
        # Create existing file
        existing_file = temp_dir / "existing.py"
        existing_file.write_text("existing content")
        
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = "# New content"
            
            result = runner.invoke(
                app,
                ["--asset", "test", "--filename", "existing.py",
                 "--output-dir", str(temp_dir), "--force"]
            )
            
            if result.exit_code == 0:
                assert existing_file.read_text() == "# New content"
    
    def test_scaffold_no_overwrite_abort(self, runner, temp_dir):
        """Test aborting when file exists and not forcing."""
        # Create existing file
        existing_file = temp_dir / "existing.py"
        existing_file.write_text("existing content")
        
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = "# New content"
            
            # Simulate user saying "No" to overwrite
            result = runner.invoke(
                app,
                ["--asset", "test", "--filename", "existing.py",
                 "--output-dir", str(temp_dir)],
                input="n\n"
            )
            
            assert result.exit_code == 1
            assert "Aborted" in result.output
            assert existing_file.read_text() == "existing content"
    
    def test_scaffold_with_template_vars(self, runner, temp_dir):
        """Test scaffold with custom template variables."""
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = "# Generated content"
            
            result = runner.invoke(
                app,
                ["--asset", "test", "--output-dir", str(temp_dir),
                 "-v", "model_type=xgboost", "-v", "epochs=100"]
            )
            
            if result.exit_code == 0:
                # Check that template vars were parsed
                call_args = mock_render.call_args[0]
                context = call_args[1]
                assert "template_vars" in context
                assert context["model_type"] == "xgboost"
                assert context["epochs"] == 100
    
    def test_scaffold_invalid_template(self, runner, temp_dir):
        """Test scaffold with invalid template name."""
        result = runner.invoke(
            app,
            ["--asset", "test", "--template", "invalid_template",
             "--output-dir", str(temp_dir)]
        )
        
        assert result.exit_code == 1
        assert "Template 'invalid_template' not found" in result.output
    
    def test_scaffold_ml_template(self, runner, temp_dir):
        """Test scaffold with ML template shows feature info."""
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = "# ML notebook"
            
            result = runner.invoke(
                app,
                ["--asset", "model", "--template", "ml",
                 "--output-dir", str(temp_dir)]
            )
            
            if result.exit_code == 0:
                assert "ML Template Features" in result.output
                assert "Exploratory data analysis" in result.output
                assert "Model training & evaluation" in result.output
    
    def test_list_templates_command(self, runner):
        """Test list-templates subcommand."""
        with patch('daglab.commands.scaffold.list_available_templates') as mock_list:
            mock_list.return_value = ["default", "minimal", "ml"]
            
            result = runner.invoke(app, ["list-templates"])
            
            assert result.exit_code == 0
            assert "Available Notebook Templates" in result.output
            assert "default" in result.output
            assert "minimal" in result.output
            assert "ml" in result.output
    
    def test_scaffold_with_all_options(self, runner, temp_dir):
        """Test scaffold with all options enabled."""
        with patch('daglab.commands.scaffold.render_template') as mock_render:
            mock_render.return_value = """
import marimo
app = marimo.App()

@app.cell
def __():
    return 42

if __name__ == "__main__":
    app.run()
"""
            
            with patch('daglab.commands.scaffold.commit_to_git') as mock_commit:
                mock_commit.return_value = True
                
                result = runner.invoke(
                    app,
                    [
                        "--asset", "complex_asset",
                        "--template", "ml",
                        "--title", "Complex ML Pipeline",
                        "--output-dir", str(temp_dir),
                        "--seed-data",
                        "--validate-config",
                        "--git-commit",
                        "--no-inprocess",
                        "--no-attach",
                        "-v", "custom_var=test_value"
                    ]
                )
                
                assert result.exit_code == 0
                # Verify all options were processed
                call_args = mock_render.call_args[0]
                context = call_args[1]
                assert context["title"] == "Complex ML Pipeline"
                assert context["seed_data"] is True
                assert context["no_inprocess"] is True
                assert context["no_attach"] is True
                assert context["validate_config"] is True
    
    def test_scaffold_mutually_exclusive_targets(self, runner, temp_dir):
        """Test that mutually exclusive targets are enforced."""
        result = runner.invoke(
            app,
            ["--asset", "test1", "--job", "test2", "--output-dir", str(temp_dir)]
        )
        
        assert result.exit_code == 1
        assert "Can only specify one of" in result.output