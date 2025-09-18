"""Tests for template validation."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from daglab.validation.template import TemplateValidator, validate_template
from daglab.validation.notebook import ValidationResult


class TestTemplateValidator:
    """Test TemplateValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return TemplateValidator()
    
    @pytest.fixture
    def temp_template(self):
        """Create temporary template file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py.j2', delete=False) as f:
            yield Path(f.name)
        # Cleanup
        Path(f.name).unlink()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)
    
    def test_validate_valid_template(self, validator, temp_template):
        """Test validating a valid template."""
        content = dedent("""
            {% block imports %}
            import marimo
            {% endblock %}
            
            {% block setup %}
            app = marimo.App()
            {% endblock %}
            
            {% block content %}
            @app.cell
            def main():
                return "{{ job_name }}"
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert result.is_valid
        assert result.error_count == 0
        assert "imports" in result.metadata["blocks"]
        assert "setup" in result.metadata["blocks"]
        assert "content" in result.metadata["blocks"]
    
    def test_validate_syntax_error(self, validator, temp_template):
        """Test detecting template syntax errors."""
        content = "{% if unclosed"
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert not result.is_valid
        assert result.error_count == 1
        assert "syntax error" in result.issues[0].message.lower()
    
    def test_validate_missing_blocks(self, validator, temp_template):
        """Test detecting missing required blocks."""
        content = dedent("""
            {% block imports %}
            import marimo
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert not result.is_valid
        assert any("content" in issue.message for issue in result.issues)
        assert any("setup" in issue.message for issue in result.issues)
    
    def test_validate_undefined_variables(self, validator, temp_template):
        """Test detecting undefined variables."""
        content = dedent("""
            {% block imports %}import marimo{% endblock %}
            {% block setup %}app = marimo.App(){% endblock %}
            {% block content %}
            @app.cell
            def main():
                job = "{{ job_name }}"  # OK - expected
                unknown = "{{ some_unknown_var }}"  # Should warn
                return job
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert any("some_unknown_var" in issue.message for issue in result.issues)
    
    def test_validate_unclosed_tags(self, validator, temp_template):
        """Test detecting unclosed tags."""
        content = dedent("""
            {% block imports %}
            import marimo
            {% endblock %}
            
            {% for item in items %}
            {{ item }}
            {# Missing endfor #}
            
            {% block content %}
            pass
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert not result.is_valid
        assert any("Unclosed" in issue.message for issue in result.issues)
    
    def test_validate_inheritance(self, validator, temp_dir):
        """Test template inheritance validation."""
        # Create parent template
        parent_path = temp_dir / "base.py.j2"
        parent_content = dedent("""
            {% block imports %}
            import marimo
            {% endblock %}
            
            {% block setup %}
            app = marimo.App()
            {% endblock %}
            
            {% block content %}
            # Base content
            {% endblock %}
        """).strip()
        parent_path.write_text(parent_content)
        
        # Create child template
        child_path = temp_dir / "child.py.j2"
        child_content = dedent("""
            {% extends "base.py.j2" %}
            
            {% block content %}
            @app.cell
            def main():
                return "Child content"
            {% endblock %}
            
            {% block undefined_block %}
            # This block doesn't exist in parent
            {% endblock %}
        """).strip()
        child_path.write_text(child_content)
        
        # Validate with template directory
        validator_with_dirs = TemplateValidator([temp_dir])
        result = validator_with_dirs.validate(child_path)
        
        assert "parent_template" in result.metadata
        assert any("undefined_block" in issue.message for issue in result.issues)
    
    def test_validate_empty_template(self, validator, temp_template):
        """Test validating empty template."""
        content = ""
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert not result.is_valid
        assert any("content" in issue.message for issue in result.issues)
    
    def test_test_rendering(self, validator, temp_template):
        """Test template rendering validation."""
        content = dedent("""
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
                assets = {{ asset_keys | tojson }}
                {{ run_job(job_name) }}
                return job, assets
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        # Should successfully render with test data
        assert result.is_valid or result.warning_count > 0
    
    def test_rendering_produces_invalid_python(self, validator, temp_template):
        """Test when rendered template produces invalid Python."""
        content = dedent("""
            {% block imports %}import marimo{% endblock %}
            {% block setup %}app = marimo.App(){% endblock %}
            {% block content %}
            @app.cell
            def main():
                # This will produce invalid Python
                {% for i in range(5) %}
                print({{ i }}  # Missing closing paren
                {% endfor %}
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert not result.is_valid
        assert any("Python syntax error" in issue.message for issue in result.issues)
    
    def test_custom_filters(self, validator, temp_template):
        """Test using custom filters."""
        content = dedent("""
            {% block imports %}import marimo{% endblock %}
            {% block setup %}app = marimo.App(){% endblock %}
            {% block content %}
            @app.cell
            def main():
                # Using unknown filter
                value = "{{ some_value | custom_filter }}"
                return value
            {% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validator.validate(temp_template)
        
        assert any("custom_filter" in issue.message for issue in result.issues)
    
    def test_convenience_function(self, temp_template):
        """Test validate_template convenience function."""
        content = dedent("""
            {% block imports %}import marimo{% endblock %}
            {% block setup %}app = marimo.App(){% endblock %}
            {% block content %}pass{% endblock %}
        """).strip()
        
        temp_template.write_text(content)
        result = validate_template(temp_template)
        
        assert isinstance(result, ValidationResult)