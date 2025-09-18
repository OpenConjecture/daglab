"""Tests for the template engine."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jinja2 import TemplateNotFound, TemplateError

from daglab.templates.engine import TemplateEngine
from daglab.templates.context import TemplateContext


class TestTemplateEngine:
    """Test the template engine functionality."""

    @pytest.fixture
    def engine(self):
        """Create a template engine instance."""
        return TemplateEngine(enable_cache=False)

    @pytest.fixture
    def temp_template_dir(self):
        """Create a temporary template directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self):
        """Test template engine initialization."""
        engine = TemplateEngine(
            enable_cache=True,
            strict_undefined=True,
            trim_blocks=False,
            lstrip_blocks=False,
        )
        assert engine.env.cache_size == 400
        assert engine.env.trim_blocks is False
        assert engine.env.lstrip_blocks is False

    def test_add_template_dir(self, engine, temp_template_dir):
        """Test adding template directory."""
        engine.add_template_dir(temp_template_dir)
        assert temp_template_dir in engine.template_dirs

        # Test with non-existent directory
        with pytest.raises(ValueError, match="does not exist"):
            engine.add_template_dir("/non/existent/path")

    def test_custom_filters(self, engine):
        """Test custom Jinja2 filters."""
        # Test to_json filter
        assert engine._filter_to_json({"key": "value"}) == '{\n  "key": "value"\n}'
        
        # Test format_date filter
        date = datetime(2024, 1, 15, 10, 30)
        assert engine._filter_format_date(date, "%Y-%m-%d") == "2024-01-15"
        
        # Test slugify filter
        assert engine._filter_slugify("Hello World!") == "hello-world"
        assert engine._filter_slugify("Test___Case") == "test_case"
        
        # Test camel_to_snake filter
        assert engine._filter_camel_to_snake("CamelCase") == "camel_case"
        assert engine._filter_camel_to_snake("HTTPResponse") == "http_response"
        
        # Test snake_to_camel filter
        assert engine._filter_snake_to_camel("snake_case") == "SnakeCase"
        assert engine._filter_snake_to_camel("snake_case", False) == "snakeCase"
        
        # Test truncate_path filter
        assert engine._filter_truncate_path("/a/b/c/d/e.txt", 3) == "c/d/e.txt"
        assert engine._filter_truncate_path("/a/b.txt", 3) == "/a/b.txt"
        
        # Test indent_code filter
        code = "line1\nline2"
        assert engine._filter_indent_code(code, 2) == "  line1\n  line2"
        
        # Test escape_quotes filter
        assert engine._filter_escape_quotes('test "quote"', "double") == 'test \\"quote\\"'
        assert engine._filter_escape_quotes("test 'quote'", "single") == "test \\'quote\\'"

    def test_render_string(self, engine):
        """Test rendering template from string."""
        template_str = "Hello {{ name }}!"
        result = engine.render_string(template_str, {"name": "World"})
        assert result == "Hello World!"
        
        # Test with error
        with pytest.raises(TemplateError):
            engine.render_string("{{ undefined_var }}", {}, name="test")

    def test_render_notebook(self, engine, temp_template_dir):
        """Test rendering notebook template."""
        # Create a simple template
        template_path = temp_template_dir / "test.ipynb.j2"
        template_content = """{
  "cells": [
    {
      "cell_type": "markdown",
      "source": ["# {{ title }}"]
    }
  ],
  "nbformat": 4,
  "nbformat_minor": 4
}"""
        template_path.write_text(template_content)
        
        # Add template directory
        engine.add_template_dir(temp_template_dir)
        
        # Render template
        result = engine.render_notebook("test.ipynb.j2", {"title": "Test Notebook"})
        notebook = json.loads(result)
        
        assert notebook["cells"][0]["source"][0] == "# Test Notebook"
        assert notebook["nbformat"] == 4

    def test_render_notebook_validation(self, engine, temp_template_dir):
        """Test notebook validation during rendering."""
        # Create invalid JSON template
        template_path = temp_template_dir / "invalid.ipynb.j2"
        template_path.write_text('{"invalid": json}')
        
        engine.add_template_dir(temp_template_dir)
        
        with pytest.raises(TemplateError, match="Invalid notebook JSON"):
            engine.render_notebook("invalid.ipynb.j2", {}, validate=True)

    def test_list_templates(self, engine, temp_template_dir):
        """Test listing available templates."""
        # Create test templates
        (temp_template_dir / "test1.j2").write_text("test")
        (temp_template_dir / "test2.jinja2").write_text("test")
        (temp_template_dir / "test.txt").write_text("test")
        
        engine.add_template_dir(temp_template_dir)
        
        templates = engine.list_templates()
        assert "test1.j2" in templates
        assert "test2.jinja2" in templates
        
        # Test with extensions filter
        templates = engine.list_templates(extensions=[".j2"])
        assert "test1.j2" in templates
        assert "test2.jinja2" not in templates

    def test_get_template_not_found(self, engine):
        """Test template not found error."""
        with pytest.raises(TemplateNotFound, match="Available templates"):
            engine.get_template("non_existent.j2")

    def test_clear_cache(self, engine):
        """Test clearing template cache."""
        engine._template_cache["test"] = "cached"
        engine.clear_cache()
        assert "test" not in engine._template_cache


class TestTemplateContext:
    """Test the template context builder."""

    @pytest.fixture
    def context_builder(self):
        """Create a context builder instance."""
        return TemplateContext()

    def test_base_context(self, context_builder):
        """Test base context creation."""
        base = context_builder._base_context
        
        assert "daglab_version" in base
        assert "generation_time" in base
        assert "environment" in base
        assert "project_root" in base
        assert "python_version" in base

    def test_build_metadata_context(self, context_builder):
        """Test metadata context building."""
        context = context_builder.build_metadata_context(
            notebook_name="test_notebook",
            author="Test Author",
            description="Test description",
            tags=["test", "demo"],
            custom_metadata={"custom": "value"},
        )
        
        metadata = context["metadata"]
        assert metadata["name"] == "test_notebook"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "Test description"
        assert metadata["tags"] == ["test", "demo"]
        assert metadata["custom"] == "value"
        assert "created_at" in metadata
        assert "kernel_spec" in metadata

    def test_build_config_context(self, context_builder):
        """Test configuration context building."""
        # Test Dagster config
        context = context_builder.build_config_context(
            target_type="dagster",
            job_name="test_job",
            asset_name="test_asset",
            schedule={"cron": "0 0 * * *"},
            resources={"io_manager": "fs_io_manager"},
        )
        
        assert context["target_type"] == "dagster"
        dagster_config = context["config"]["dagster"]
        assert dagster_config["job_name"] == "test_job"
        assert dagster_config["asset_name"] == "test_asset"
        assert dagster_config["schedule"]["cron"] == "0 0 * * *"
        assert dagster_config["resources"]["io_manager"] == "fs_io_manager"
        
        # Test Marimo config
        context = context_builder.build_config_context(target_type="marimo")
        assert context["target_type"] == "marimo"
        assert "marimo" in context["config"]

    def test_build_target_context(self, context_builder):
        """Test target-specific context building."""
        context = context_builder.build_target_context(
            imports=["import pandas as pd"],
            parameters={"param1": "value1"},
            outputs={"output1": "path1"},
            dependencies=["dep1", "dep2"],
        )
        
        assert context["imports"] == ["import pandas as pd"]
        assert context["parameters"]["param1"] == "value1"
        assert context["outputs"]["output1"] == "path1"
        assert context["dependencies"] == ["dep1", "dep2"]

    def test_build_complete_context(self, context_builder):
        """Test building complete context."""
        context = context_builder.build_complete_context(
            notebook_name="complete_test",
            target_type="dagster",
            author="Test",
            custom_context={"extra": "value"},
        )
        
        # Check all sections are present
        assert "metadata" in context
        assert "config" in context
        assert "imports" in context
        assert "extra" in context
        assert context["extra"] == "value"

    def test_validate_context(self, context_builder):
        """Test context validation."""
        valid_context = {
            "metadata": {"name": "test", "author": "author"},
            "config": {},
            "imports": [],
        }
        
        is_valid, missing = context_builder.validate_context(valid_context)
        assert is_valid
        assert not missing
        
        # Test with missing keys
        invalid_context = {"metadata": {"name": "test"}}
        is_valid, missing = context_builder.validate_context(invalid_context)
        assert not is_valid
        assert "metadata.author" in missing
        assert "config" in missing
        assert "imports" in missing

    def test_merge_contexts(self, context_builder):
        """Test merging contexts."""
        context1 = {"a": 1, "b": {"c": 2}}
        context2 = {"b": {"d": 3}, "e": 4}
        
        merged = context_builder.merge_contexts(context1, context2)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 2
        assert merged["b"]["d"] == 3
        assert merged["e"] == 4

    def test_add_custom_variables(self, context_builder):
        """Test adding custom variables."""
        context = {"existing": "value"}
        variables = {"var1": "value1", "var2": "value2"}
        
        result = context_builder.add_custom_variables(context, variables)
        assert result["custom"]["var1"] == "value1"
        assert result["custom"]["var2"] == "value2"
        assert result["existing"] == "value"