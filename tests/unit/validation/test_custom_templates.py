"""Tests for custom template support."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from daglab.templates.custom import (
    CustomTemplateLoader, load_custom_template, render_custom_template
)
from daglab.validation.notebook import ValidationResult


class TestCustomTemplateLoader:
    """Test CustomTemplateLoader class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)
    
    @pytest.fixture
    def loader(self, temp_dir):
        """Create loader with temp directory."""
        return CustomTemplateLoader(custom_dirs=[temp_dir])
    
    def create_template(self, path: Path, content: str):
        """Helper to create template file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    
    def test_discover_templates(self, loader, temp_dir):
        """Test template discovery."""
        # Create some templates
        template1 = self.create_template(
            temp_dir / "template1.py.j2",
            "{% block content %}Test 1{% endblock %}"
        )
        
        template2 = self.create_template(
            temp_dir / "subdir" / "template2.py.j2",
            "{% block content %}Test 2{% endblock %}"
        )
        
        # Add metadata to template
        template3 = self.create_template(
            temp_dir / "template3.py.j2",
            dedent("""
                {# METADATA
                description: Test template with metadata
                author: Test Author
                version: 1.0.0
                #}
                {% block content %}Test 3{% endblock %}
            """).strip()
        )
        
        templates = loader.discover()
        
        # Should find all templates
        all_templates = templates["custom"] + templates["user"]
        assert len(all_templates) >= 3
        
        # Check metadata extraction
        template3_info = next(
            (t for t in all_templates if "template3" in t["name"]), None
        )
        assert template3_info is not None
        assert template3_info.get("description") == "Test template with metadata"
        assert template3_info.get("author") == "Test Author"
    
    def test_validate_all_templates(self, loader, temp_dir):
        """Test validating all discovered templates."""
        # Create valid template
        valid_template = self.create_template(
            temp_dir / "valid.py.j2",
            dedent("""
                {% block imports %}import marimo{% endblock %}
                {% block setup %}app = marimo.App(){% endblock %}
                {% block content %}pass{% endblock %}
            """).strip()
        )
        
        # Create invalid template
        invalid_template = self.create_template(
            temp_dir / "invalid.py.j2",
            "{% if unclosed"
        )
        
        results = loader.validate_all()
        
        # Check results
        assert str(valid_template) in results
        assert str(invalid_template) in results
        
        assert results[str(valid_template)].is_valid
        assert not results[str(invalid_template)].is_valid
    
    def test_register_filter(self, loader):
        """Test registering custom filters."""
        # Register filter
        def reverse_string(s):
            return s[::-1]
        
        loader.register_filter("reverse", reverse_string)
        
        # Check filter is registered
        assert "reverse" in loader.env.filters
        assert loader.env.filters["reverse"]("hello") == "olleh"
    
    def test_register_multiple_filters(self, loader):
        """Test registering multiple filters."""
        filters = {
            "double": lambda x: x * 2,
            "square": lambda x: x ** 2,
            "uppercase": lambda x: str(x).upper()
        }
        
        loader.register_filters(filters)
        
        for name, func in filters.items():
            assert name in loader.env.filters
    
    def test_load_template(self, loader, temp_dir):
        """Test loading templates."""
        # Create template
        template_path = self.create_template(
            temp_dir / "test.py.j2",
            "{{ message }}"
        )
        
        # Load with full name
        template1 = loader.load_template("test.py.j2")
        assert template1 is not None
        
        # Load without extension
        template2 = loader.load_template("test")
        assert template2 is not None
        
        # Load non-existent should raise
        with pytest.raises(Exception) as exc_info:
            loader.load_template("nonexistent.py.j2")
        assert "not found" in str(exc_info.value)
    
    def test_render_template(self, loader, temp_dir):
        """Test rendering templates."""
        # Create template
        self.create_template(
            temp_dir / "render_test.py.j2",
            dedent("""
                {% block imports %}
                import marimo
                {% endblock %}
                
                {% block setup %}
                app = marimo.App()
                {% endblock %}
                
                {% block content %}
                @app.cell
                def main():
                    job = "{{ job_name }}"
                    result = {{ run_job(job_name) }}
                    return job, result
                {% endblock %}
            """).strip()
        )
        
        # Render template
        context = {
            "job_name": "test_job"
        }
        
        rendered = loader.render_template("render_test.py.j2", context)
        
        assert "test_job" in rendered
        assert "import marimo" in rendered
        assert "@app.cell" in rendered
    
    def test_create_template(self, loader, temp_dir):
        """Test creating new templates."""
        content = dedent("""
            {% block imports %}import marimo{% endblock %}
            {% block setup %}app = marimo.App(){% endblock %}
            {% block content %}
            @app.cell
            def main():
                return "Created template"
            {% endblock %}
        """).strip()
        
        # Create template
        path = loader.create_template("new_template", content)
        
        assert path.exists()
        assert path.name == "new_template.py.j2"
        assert path.read_text() == content
        
        # Should be in cache
        assert "new_template.py.j2" in loader._template_cache
    
    def test_create_invalid_template(self, loader, temp_dir):
        """Test creating invalid template fails."""
        content = "{% if unclosed"
        
        with pytest.raises(ValueError) as exc_info:
            loader.create_template("bad_template", content)
        
        assert "validation failed" in str(exc_info.value).lower()
        
        # Should not create file
        bad_path = temp_dir / "bad_template.py.j2"
        assert not bad_path.exists()
    
    def test_inheritance_chain(self, loader, temp_dir):
        """Test getting template inheritance chain."""
        # Create base template
        self.create_template(
            temp_dir / "base.py.j2",
            dedent("""
                {% block imports %}# Base imports{% endblock %}
                {% block content %}# Base content{% endblock %}
            """).strip()
        )
        
        # Create child template
        self.create_template(
            temp_dir / "child.py.j2",
            dedent("""
                {% extends "base.py.j2" %}
                {% block content %}# Child content{% endblock %}
            """).strip()
        )
        
        # Get inheritance chain
        chain = loader.get_inheritance_chain("child.py.j2")
        
        assert len(chain) >= 1
        assert "child.py.j2" in chain[0]
    
    def test_default_context(self, loader, temp_dir):
        """Test default context includes helpers."""
        self.create_template(
            temp_dir / "context_test.py.j2",
            dedent("""
                {% if run_job %}Has run_job{% endif %}
                {% if discover %}Has discover{% endif %}
                {% if datetime %}Has datetime{% endif %}
            """).strip()
        )
        
        rendered = loader.render_template("context_test.py.j2", {})
        
        assert "Has run_job" in rendered
        assert "Has discover" in rendered
        assert "Has datetime" in rendered
    
    def test_default_filters(self, loader, temp_dir):
        """Test default filters are available."""
        self.create_template(
            temp_dir / "filter_test.py.j2",
            dedent("""
                Snake: {{ "Test String" | snake_case }}
                Camel: {{ "test_string" | camel_case }}
                JSON: {{ {"key": "value"} | to_json }}
                Repr: {{ "test" | python_repr }}
            """).strip()
        )
        
        rendered = loader.render_template("filter_test.py.j2", {})
        
        assert "test_string" in rendered  # snake_case
        assert "TestString" in rendered   # camel_case
        assert '{"key": "value"}' in rendered  # to_json
        assert "'test'" in rendered  # python_repr
    
    def test_convenience_functions(self, temp_dir):
        """Test convenience functions."""
        # Create template
        template_path = temp_dir / "convenience.py.j2"
        template_path.write_text("Hello {{ name }}")
        
        # Test load
        template = load_custom_template("convenience", custom_dirs=[temp_dir])
        assert template is not None
        
        # Test render
        rendered = render_custom_template(
            "convenience",
            {"name": "World"},
            custom_dirs=[temp_dir]
        )
        assert rendered == "Hello World"