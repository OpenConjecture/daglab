"""Tests for the migrate command."""

import json
import nbformat
from pathlib import Path
import pytest
from typer.testing import CliRunner

from daglab.commands.migrate import app, NotebookMigrator


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_notebook(tmp_path):
    """Create a sample Jupyter notebook for testing."""
    nb = nbformat.v4.new_notebook()
    
    # Add metadata
    nb.metadata = {
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        }
    }
    
    # Add cells
    nb.cells = [
        nbformat.v4.new_markdown_cell("# Test Notebook\nThis is a test."),
        nbformat.v4.new_code_cell("import pandas as pd\nimport numpy as np"),
        nbformat.v4.new_code_cell("%matplotlib inline\nimport matplotlib.pyplot as plt"),
        nbformat.v4.new_code_cell("data = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})"),
        nbformat.v4.new_markdown_cell("## Results\nHere are the results:"),
        nbformat.v4.new_code_cell("%%time\nresult = data.sum()"),
        nbformat.v4.new_code_cell("# Regular code\nprint(result)"),
    ]
    
    # Add output to one cell
    nb.cells[6].outputs = [
        {
            "name": "stdout",
            "output_type": "stream",
            "text": "x    6\ny    15\ndtype: int64\n"
        }
    ]
    
    # Save notebook
    nb_path = tmp_path / "test_notebook.ipynb"
    with open(nb_path, 'w') as f:
        nbformat.write(nb, f)
    
    return nb_path


@pytest.fixture
def complex_notebook(tmp_path):
    """Create a complex notebook with widgets and magic commands."""
    nb = nbformat.v4.new_notebook()
    
    nb.cells = [
        nbformat.v4.new_code_cell("import ipywidgets as widgets"),
        nbformat.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbformat.v4.new_code_cell("%%bash\nls -la"),
        nbformat.v4.new_code_cell("slider = widgets.IntSlider(value=50)"),
        nbformat.v4.new_code_cell("%pwd"),
        nbformat.v4.new_code_cell("!pip install something"),
    ]
    
    nb_path = tmp_path / "complex_notebook.ipynb"
    with open(nb_path, 'w') as f:
        nbformat.write(nb, f)
    
    return nb_path


@pytest.fixture
def notebook_directory(tmp_path):
    """Create a directory with multiple notebooks."""
    nb_dir = tmp_path / "notebooks"
    nb_dir.mkdir()
    
    # Create several notebooks
    for i in range(3):
        nb = nbformat.v4.new_notebook()
        nb.cells = [
            nbformat.v4.new_markdown_cell(f"# Notebook {i}"),
            nbformat.v4.new_code_cell(f"x = {i}"),
        ]
        
        nb_path = nb_dir / f"notebook_{i}.ipynb"
        with open(nb_path, 'w') as f:
            nbformat.write(nb, f)
    
    # Create a subdirectory with more notebooks
    sub_dir = nb_dir / "analysis"
    sub_dir.mkdir()
    
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell("import pandas as pd")]
    
    nb_path = sub_dir / "analysis.ipynb"
    with open(nb_path, 'w') as f:
        nbformat.write(nb, f)
    
    return nb_dir


class TestNotebookMigrator:
    """Test the NotebookMigrator class."""
    
    def test_analyze_notebook(self, sample_notebook):
        """Test notebook analysis."""
        migrator = NotebookMigrator()
        analysis = migrator.analyze_notebook(sample_notebook)
        
        assert analysis["total_cells"] == 7
        assert analysis["code_cells"] == 5
        assert analysis["markdown_cells"] == 2
        assert analysis["has_outputs"] is True
        assert len(analysis["magic_commands"]) > 0
        assert "pandas" in analysis["imports"]
        assert analysis["complexity"] == "simple"
    
    def test_analyze_complex_notebook(self, complex_notebook):
        """Test analysis of complex notebook."""
        migrator = NotebookMigrator()
        analysis = migrator.analyze_notebook(complex_notebook)
        
        assert analysis["widgets"] is True
        assert len(analysis["magic_commands"]) >= 4
        assert analysis["complexity"] in ["moderate", "complex"]
    
    def test_convert_magic_commands(self):
        """Test magic command conversion."""
        migrator = NotebookMigrator()
        
        # Test single line magic
        source = "%matplotlib inline\nx = 1"
        converted = migrator.convert_magic_commands(source)
        assert "mo.matplotlib_setup()" in converted
        assert "x = 1" in converted
        
        # Test cell magic
        source = "%%time\nresult = compute()"
        converted = migrator.convert_magic_commands(source)
        assert "@mo.timed" in converted
        
        # Test unmapped magic
        source = "%unknown_magic arg"
        converted = migrator.convert_magic_commands(source)
        assert "TODO: Migrate magic command" in converted
    
    def test_convert_cell(self):
        """Test cell conversion."""
        migrator = NotebookMigrator()
        
        # Test markdown cell
        md_cell = {"cell_type": "markdown", "source": "# Title"}
        converted = migrator.convert_cell(md_cell, 0)
        assert converted["type"] == "markdown"
        assert converted["source"] == "# Title"
        
        # Test code cell
        code_cell = {"cell_type": "code", "source": "x = 1"}
        converted = migrator.convert_cell(code_cell, 0)
        assert converted["type"] == "code"
        assert "import marimo as mo" in converted["source"]
        
        # Test code cell with magic
        magic_cell = {"cell_type": "code", "source": "%pwd\nprint('hello')"}
        converted = migrator.convert_cell(magic_cell, 1)
        assert "Path.cwd()" in converted["source"]
    
    def test_migrate_notebook(self, sample_notebook, tmp_path):
        """Test full notebook migration."""
        migrator = NotebookMigrator()
        target = tmp_path / "migrated.marimo.py"
        
        result = migrator.migrate_notebook(sample_notebook, target)
        
        assert target.exists()
        assert result["cells_migrated"] == 7
        
        # Load and verify migrated notebook
        with open(target, 'r') as f:
            marimo_nb = json.load(f)
        
        assert marimo_nb["version"] == "0.1.0"
        assert len(marimo_nb["cells"]) == 7
        assert marimo_nb["metadata"]["migrated_from"] == str(sample_notebook)
    
    def test_create_dagster_asset(self, tmp_path):
        """Test Dagster asset creation."""
        migrator = NotebookMigrator()
        nb_path = tmp_path / "notebook.marimo.py"
        
        asset_code = migrator.create_dagster_asset(nb_path, "my-analysis")
        
        assert "@asset" in asset_code
        assert "my_analysis" in asset_code  # Converted to valid Python name
        assert str(nb_path) in asset_code


class TestMigrateCommand:
    """Test the migrate command CLI."""
    
    def test_migrate_single_file(self, runner, sample_notebook, tmp_path):
        """Test migrating a single notebook."""
        target = tmp_path / "output"
        
        result = runner.invoke(app, [str(sample_notebook), "--target", str(target)])
        
        assert result.exit_code == 0
        assert "Successfully migrated 1/1 notebooks" in result.output
        
        # Check output exists
        expected_output = target / "test_notebook.marimo.py"
        assert expected_output.exists()
    
    def test_migrate_directory(self, runner, notebook_directory, tmp_path):
        """Test migrating a directory of notebooks."""
        target = tmp_path / "marimo_output"
        
        result = runner.invoke(app, [str(notebook_directory), "--target", str(target)])
        
        assert result.exit_code == 0
        assert "Successfully migrated 4/4 notebooks" in result.output
        
        # Check structure is preserved
        assert (target / "notebook_0.marimo.py").exists()
        assert (target / "analysis" / "analysis.marimo.py").exists()
    
    def test_migrate_dry_run(self, runner, sample_notebook):
        """Test dry run mode."""
        result = runner.invoke(app, [str(sample_notebook), "--dry-run"])
        
        assert result.exit_code == 0
        assert "Notebook Analysis" in result.output
        assert "Dry run complete" in result.output
    
    def test_migrate_interactive_proceed(self, runner, sample_notebook, tmp_path):
        """Test interactive mode with proceed."""
        target = tmp_path / "output"
        
        result = runner.invoke(
            app,
            [str(sample_notebook), "--target", str(target), "--interactive"],
            input="y\n"
        )
        
        assert result.exit_code == 0
        assert "Successfully migrated" in result.output
    
    def test_migrate_interactive_cancel(self, runner, sample_notebook, tmp_path):
        """Test interactive mode with cancel."""
        target = tmp_path / "output"
        
        result = runner.invoke(
            app,
            [str(sample_notebook), "--target", str(target), "--interactive"],
            input="n\n"
        )
        
        assert result.exit_code == 0
        assert "Migration cancelled" in result.output
    
    def test_migrate_with_assets(self, runner, sample_notebook, tmp_path):
        """Test migration with asset creation."""
        target = tmp_path / "output"
        
        result = runner.invoke(
            app,
            [str(sample_notebook), "--target", str(target), "--create-assets"]
        )
        
        assert result.exit_code == 0
        assert "Created 1 Dagster assets" in result.output
        
        assets_file = target / "__dagster_assets__.py"
        assert assets_file.exists()
        assert "@asset" in assets_file.read_text()
    
    def test_migrate_preserve_outputs(self, runner, sample_notebook, tmp_path):
        """Test preserving outputs during migration."""
        target = tmp_path / "output"
        
        result = runner.invoke(
            app,
            [str(sample_notebook), "--target", str(target), "--preserve-outputs"]
        )
        
        assert result.exit_code == 0
        
        # Check that outputs are preserved
        output_file = target / "test_notebook.marimo.py"
        with open(output_file, 'r') as f:
            content = json.load(f)
        
        # Find cell with output
        has_output = any(
            "outputs" in cell 
            for cell in content["cells"] 
            if cell.get("type") == "code"
        )
        assert has_output
    
    def test_migrate_force_overwrite(self, runner, sample_notebook, tmp_path):
        """Test force overwrite option."""
        target = tmp_path / "output"
        target.mkdir()
        
        # Create existing file
        existing = target / "test_notebook.marimo.py"
        existing.write_text("existing content")
        
        # Without force - should skip
        result = runner.invoke(app, [str(sample_notebook), "--target", str(target)])
        assert "Target exists" in result.output or "file exists" in result.output
        
        # With force - should overwrite
        result = runner.invoke(
            app,
            [str(sample_notebook), "--target", str(target), "--force"]
        )
        
        assert result.exit_code == 0
        assert existing.read_text() != "existing content"
    
    def test_check_command(self, runner, sample_notebook, complex_notebook):
        """Test the check subcommand."""
        # Check simple notebook
        result = runner.invoke(app, ["check", str(sample_notebook)])
        assert result.exit_code == 0
        assert "Compatibility Score" in result.output
        
        # Check complex notebook
        result = runner.invoke(app, ["check", str(complex_notebook)])
        assert result.exit_code == 0
        assert "magic commands need conversion" in result.output
        assert "Contains widgets" in result.output
    
    def test_migrate_invalid_source(self, runner):
        """Test with invalid source path."""
        result = runner.invoke(app, ["/nonexistent/path"])
        assert result.exit_code == 1
        assert "does not exist" in result.output
    
    def test_migrate_non_notebook_file(self, runner, tmp_path):
        """Test with non-notebook file."""
        text_file = tmp_path / "not_a_notebook.txt"
        text_file.write_text("just text")
        
        result = runner.invoke(app, [str(text_file)])
        assert result.exit_code == 1
        assert "must be a .ipynb notebook" in result.output