"""Tests for notebook validation."""

import ast
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from daglab.validation.notebook import (
    NotebookValidator, ValidationIssue, ValidationResult, validate_notebook
)


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_empty_result_is_valid(self):
        """Empty result should be valid."""
        result = ValidationResult()
        assert result.is_valid
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.info_count == 0
    
    def test_add_error_invalidates_result(self):
        """Adding error should invalidate result."""
        result = ValidationResult()
        result.add_issue(ValidationIssue(severity="error", message="Test error"))
        assert not result.is_valid
        assert result.error_count == 1
    
    def test_add_warning_keeps_valid(self):
        """Adding warning should keep result valid."""
        result = ValidationResult()
        result.add_issue(ValidationIssue(severity="warning", message="Test warning"))
        assert result.is_valid
        assert result.warning_count == 1
    
    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult()
        result1.add_issue(ValidationIssue(severity="error", message="Error 1"))
        result1.metadata["key1"] = "value1"
        
        result2 = ValidationResult()
        result2.add_issue(ValidationIssue(severity="warning", message="Warning 1"))
        result2.metadata["key2"] = "value2"
        
        result1.merge(result2)
        
        assert not result1.is_valid  # Has error
        assert result1.error_count == 1
        assert result1.warning_count == 1
        assert result1.metadata == {"key1": "value1", "key2": "value2"}
    
    def test_summary_output(self):
        """Test summary generation."""
        result = ValidationResult()
        assert "✅" in result.summary()
        
        result.add_issue(ValidationIssue(severity="error", message="Test"))
        assert "❌" in result.summary()
        assert "1 errors" in result.summary()


class TestNotebookValidator:
    """Test NotebookValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return NotebookValidator()
    
    @pytest.fixture
    def temp_notebook(self):
        """Create temporary notebook file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            yield Path(f.name)
        # Cleanup
        Path(f.name).unlink()
    
    def test_validate_valid_marimo_notebook(self, validator, temp_notebook):
        """Test validating a valid marimo notebook."""
        content = dedent("""
            import marimo
            
            app = marimo.App()
            
            @app.cell
            def cell1():
                x = 1
                return x
            
            @app.cell
            def cell2(x):
                y = x + 1
                return y
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert result.is_valid
        assert result.error_count == 0
        assert result.metadata["cell_count"] == 2
    
    def test_validate_syntax_error(self, validator, temp_notebook):
        """Test detecting Python syntax errors."""
        content = "def invalid syntax:"
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert not result.is_valid
        assert result.error_count == 1
        assert "syntax" in result.issues[0].message.lower()
    
    def test_validate_no_marimo_app(self, validator, temp_notebook):
        """Test detecting missing marimo.App()."""
        content = dedent("""
            import marimo
            
            def some_function():
                pass
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert not result.is_valid
        assert any("marimo.App()" in issue.message for issue in result.issues)
    
    def test_validate_imports(self, validator, temp_notebook):
        """Test import validation."""
        content = dedent("""
            import marimo
            import os
            import numy  # Typo
            from daglab.helpers.notebook import run_job
            
            app = marimo.App()
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        # Should catch the typo
        assert any("numy" in issue.message for issue in result.issues)
        assert any("numpy" in issue.fix_suggestion for issue in result.issues 
                  if issue.fix_suggestion)
    
    def test_validate_mixed_indentation(self, validator, temp_notebook):
        """Test detecting mixed tabs and spaces."""
        content = dedent("""
            import marimo
            
            app = marimo.App()
            
            @app.cell
            def cell1():
            \tx = 1  # Tab
                y = 2  # Spaces
                return x, y
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert any("Mixed tabs and spaces" in issue.message for issue in result.issues)
    
    def test_validate_large_cell(self, validator, temp_notebook):
        """Test detecting large cells."""
        # Generate a large cell
        lines = ["import marimo", "", "app = marimo.App()", "", "@app.cell", "def large_cell():"]
        for i in range(60):
            lines.append(f"    var_{i} = {i}")
        lines.append("    return None")
        
        content = "\n".join(lines)
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert any("large" in issue.message.lower() for issue in result.issues)
    
    def test_validate_template_variables(self, validator, temp_notebook):
        """Test template variable validation."""
        content = dedent("""
            import marimo
            
            app = marimo.App()
            
            @app.cell
            def cell1():
                job_name = "{{ job_name }}"
                unknown_var = "{{ unknown_variable }}"
                return job_name
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert any("unknown_variable" in issue.message for issue in result.issues)
    
    def test_strict_mode(self, temp_notebook):
        """Test strict mode converts warnings to errors."""
        content = dedent("""
            import marimo
            
            app = marimo.App()
            
            @app.cell
            def cell1():
                x = 1    # Trailing whitespace
                return x
        """).strip()
        
        temp_notebook.write_text(content)
        
        # Normal mode
        validator = NotebookValidator(strict_mode=False)
        result = validator.validate(temp_notebook)
        assert result.is_valid  # Warnings don't invalidate
        
        # Strict mode
        validator_strict = NotebookValidator(strict_mode=True)
        result_strict = validator_strict.validate(temp_notebook)
        assert not result_strict.is_valid  # Warnings become errors
    
    def test_complex_cell_detection(self, validator, temp_notebook):
        """Test detecting high complexity cells."""
        content = dedent("""
            import marimo
            
            app = marimo.App()
            
            @app.cell
            def complex_cell():
                if True:
                    if True:
                        if True:
                            for i in range(10):
                                if i > 5:
                                    while True:
                                        try:
                                            if i % 2:
                                                break
                                        except:
                                            pass
                return None
        """).strip()
        
        temp_notebook.write_text(content)
        result = validator.validate(temp_notebook)
        
        assert any("complexity" in issue.message.lower() for issue in result.issues)
    
    def test_convenience_function(self, temp_notebook):
        """Test validate_notebook convenience function."""
        content = dedent("""
            import marimo
            app = marimo.App()
        """).strip()
        
        temp_notebook.write_text(content)
        result = validate_notebook(temp_notebook)
        
        assert isinstance(result, ValidationResult)