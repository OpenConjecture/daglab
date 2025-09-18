"""Tests for export command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from typer.testing import CliRunner

from daglab.commands.export import app, display_export_results
from daglab.helpers.export import ExportEngine, ExportFormat


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_notebook(tmp_path):
    """Create a temporary notebook file."""
    notebook_path = tmp_path / "test_notebook.py"
    notebook_path.write_text("""
# @title: Test Notebook
# @description: A test notebook for export
# @author: Test Author

import marimo

@app.cell
def cell1():
    x = 1
    y = 2
    return x + y

@app.cell
def cell2():
    import pandas as pd
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    return df
""")
    return notebook_path


class TestExportCommand:
    """Test export command functionality."""
    
    def test_export_help(self, runner):
        """Test export command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Export notebooks to various formats" in result.stdout
    
    @patch('daglab.commands.export.ExportEngine')
    def test_export_html_default(self, mock_engine_class, runner, temp_notebook):
        """Test default HTML export."""
        # Setup mock
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(temp_notebook.with_suffix(".html")),
            "format": "HTML",
            "size": 1024,
        }
        
        result = runner.invoke(app, [str(temp_notebook)])
        
        assert result.exit_code == 0
        mock_engine.export.assert_called_once()
        call_args = mock_engine.export.call_args[1]
        assert call_args["format"] == ExportFormat.HTML
        assert call_args["notebook_path"] == temp_notebook
    
    @patch('daglab.commands.export.ExportEngine')
    def test_export_pdf(self, mock_engine_class, runner, temp_notebook):
        """Test PDF export."""
        # Setup mock
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".pdf"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(temp_notebook.with_suffix(".pdf")),
            "format": "PDF",
            "size": 2048,
        }
        
        result = runner.invoke(app, [
            str(temp_notebook),
            "--format", "pdf",
        ])
        
        assert result.exit_code == 0
        mock_engine.export.assert_called_once()
        call_args = mock_engine.export.call_args[1]
        assert call_args["format"] == ExportFormat.PDF
    
    @patch('daglab.commands.export.ExportEngine')
    def test_export_with_output_path(self, mock_engine_class, runner, temp_notebook, tmp_path):
        """Test export with custom output path."""
        output_path = tmp_path / "output" / "report.html"
        
        # Setup mock
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(output_path),
            "format": "HTML",
            "size": 1024,
        }
        
        result = runner.invoke(app, [
            str(temp_notebook),
            "--output", str(output_path),
        ])
        
        assert result.exit_code == 0
        call_args = mock_engine.export.call_args[1]
        assert call_args["output_path"] == output_path
    
    @patch('daglab.commands.export.ExportEngine')
    @patch('daglab.commands.export.create_storage_provider')
    def test_export_with_cloud_upload(
        self, mock_storage_factory, mock_engine_class, runner, temp_notebook
    ):
        """Test export with cloud upload."""
        # Setup mocks
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(temp_notebook.with_suffix(".html")),
            "format": "HTML",
            "size": 1024,
        }
        
        mock_storage = Mock()
        mock_storage_factory.return_value = mock_storage
        mock_storage.upload.return_value = {
            "url": "https://bucket.s3.amazonaws.com/exports/test_notebook.html",
            "key": "exports/test_notebook.html",
        }
        mock_storage.generate_signed_url.return_value = "https://signed-url.example.com"
        
        result = runner.invoke(app, [
            str(temp_notebook),
            "--cloud", "s3",
            "--bucket", "my-bucket",
        ])
        
        assert result.exit_code == 0
        mock_storage_factory.assert_called_once_with("s3", bucket="my-bucket")
        mock_storage.upload.assert_called_once()
    
    @patch('daglab.commands.export.ExportEngine')
    def test_export_with_compression(self, mock_engine_class, runner, temp_notebook):
        """Test export with compression."""
        # Setup mock
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(temp_notebook.with_suffix(".html.gz")),
            "format": "HTML",
            "size": 512,
            "compressed": True,
            "compression_ratio": 50.0,
        }
        
        result = runner.invoke(app, [
            str(temp_notebook),
            "--compress",
        ])
        
        assert result.exit_code == 0
        call_args = mock_engine.export.call_args[1]
        assert call_args["compress"] is True
    
    @patch('daglab.commands.export.ExportEngine')
    @patch('daglab.commands.export.MetadataAttacher')
    def test_export_with_dagster_metadata(
        self, mock_attacher_class, mock_engine_class, runner, temp_notebook
    ):
        """Test export with Dagster metadata attachment."""
        # Setup mocks
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.return_value = {
            "path": str(temp_notebook),
            "output_path": str(temp_notebook.with_suffix(".html")),
            "format": "HTML",
            "size": 1024,
            "dagster_metadata": {
                "asset_key": "test_notebook",
                "dependencies": ["pandas"],
            },
        }
        
        mock_attacher = Mock()
        mock_attacher_class.return_value = mock_attacher
        mock_attacher.attach_export_metadata.return_value = {"success": True}
        
        result = runner.invoke(app, [
            str(temp_notebook),
            "--dagster-url", "http://localhost:3000",
            "--dagster-token", "test-token",
        ])
        
        assert result.exit_code == 0
        mock_attacher_class.assert_called_once_with(
            dagster_url="http://localhost:3000",
            auth_token="test-token",
        )
        mock_attacher.attach_export_metadata.assert_called_once()
    
    @patch('daglab.commands.export.ExportEngine')
    def test_batch_export(self, mock_engine_class, runner, tmp_path):
        """Test batch export of multiple notebooks."""
        # Create multiple notebooks
        notebook1 = tmp_path / "notebook1.py"
        notebook2 = tmp_path / "notebook2.py"
        notebook1.write_text("# Notebook 1")
        notebook2.write_text("# Notebook 2")
        
        # Setup mock
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_file_extension.return_value = ".html"
        mock_engine.export.side_effect = [
            {
                "path": str(notebook1),
                "output_path": str(notebook1.with_suffix(".html")),
                "format": "HTML",
                "size": 1024,
            },
            {
                "path": str(notebook2),
                "output_path": str(notebook2.with_suffix(".html")),
                "format": "HTML",
                "size": 2048,
            },
        ]
        
        result = runner.invoke(app, [
            str(tmp_path),
            "--batch",
        ])
        
        assert result.exit_code == 0
        assert mock_engine.export.call_count == 2
    
    def test_invalid_format(self, runner, temp_notebook):
        """Test invalid export format."""
        result = runner.invoke(app, [
            str(temp_notebook),
            "--format", "invalid",
        ])
        
        assert result.exit_code == 1
        assert "Invalid format" in result.stdout
    
    def test_nonexistent_notebook(self, runner):
        """Test export of non-existent notebook."""
        result = runner.invoke(app, [
            "nonexistent.py",
        ])
        
        assert result.exit_code == 2
        assert "does not exist" in result.stdout
    
    def test_display_export_results(self, capsys):
        """Test display_export_results function."""
        results = [
            {
                "path": "/path/to/notebook1.py",
                "output_path": "/path/to/notebook1.html",
                "format": "HTML",
                "cloud_url": "https://example.com/notebook1.html",
                "compressed": True,
                "compression_ratio": 45.5,
            },
            {
                "path": "/path/to/notebook2.py",
                "error": "Export failed: Invalid notebook",
            },
        ]
        
        display_export_results(results, verbose=True)
        
        captured = capsys.readouterr()
        assert "Export Results" in captured.out
        assert "✓ Success" in captured.out
        assert "✗ Failed" in captured.out
        assert "1 successful, 1 failed" in captured.out
    
    def test_batch_subcommand(self, runner, tmp_path):
        """Test batch subcommand."""
        # Create test directory
        notebooks_dir = tmp_path / "notebooks"
        notebooks_dir.mkdir()
        
        with patch('daglab.commands.export.export') as mock_export:
            result = runner.invoke(app, [
                "batch",
                str(notebooks_dir),
                "--format", "pdf",
            ])
            
            assert result.exit_code == 0
            mock_export.assert_called_once()
            call_args = mock_export.call_args[1]
            assert call_args["batch"] is True
            assert call_args["format"] == "pdf"
    
    def test_cloud_subcommand(self, runner, temp_notebook):
        """Test cloud subcommand."""
        with patch('daglab.commands.export.export') as mock_export:
            result = runner.invoke(app, [
                "cloud",
                str(temp_notebook),
                "s3",
                "my-bucket",
                "--key", "reports/notebook.html",
            ])
            
            assert result.exit_code == 0
            mock_export.assert_called_once()
            call_args = mock_export.call_args[1]
            assert call_args["cloud_provider"] == "s3"
            assert call_args["cloud_bucket"] == "my-bucket"
            assert call_args["cloud_key"] == "reports/notebook.html"


class TestExportEngine:
    """Test ExportEngine functionality."""
    
    def test_get_file_extension(self):
        """Test file extension mapping."""
        engine = ExportEngine()
        assert engine.get_file_extension(ExportFormat.HTML) == ".html"
        assert engine.get_file_extension(ExportFormat.PDF) == ".pdf"
        assert engine.get_file_extension(ExportFormat.MD) == ".md"
        assert engine.get_file_extension(ExportFormat.PY) == ".py"
        assert engine.get_file_extension(ExportFormat.IPYNB) == ".ipynb"
        assert engine.get_file_extension(ExportFormat.DAGSTER) == "_assets.py"
    
    def test_extract_metadata(self, temp_notebook):
        """Test metadata extraction."""
        engine = ExportEngine()
        metadata = engine._extract_metadata(temp_notebook)
        
        assert metadata["title"] == "Test Notebook"
        assert metadata["path"] == str(temp_notebook)
        assert "description" in metadata
        assert "author" in metadata
    
    def test_extract_dependencies(self):
        """Test dependency extraction."""
        engine = ExportEngine()
        content = """
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import os
from daglab.core import Pipeline
"""
        
        deps = engine._extract_dependencies(content)
        assert "pandas" in deps
        assert "numpy" in deps
        assert "sklearn" in deps
        assert "daglab" in deps
        assert "os" not in deps  # Standard library
    
    def test_compress_file(self, tmp_path):
        """Test file compression."""
        # Create test file
        test_file = tmp_path / "test.html"
        test_file.write_text("Hello, World!" * 100)
        
        engine = ExportEngine()
        compressed = engine._compress_file(test_file)
        
        assert compressed.exists()
        assert compressed.suffix == ".gz"
        assert compressed.stat().st_size < test_file.stat().st_size