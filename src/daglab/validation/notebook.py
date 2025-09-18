"""
Notebook validation system for DagLab.

This module provides comprehensive validation for marimo notebooks,
including Python syntax checking, structure validation, import validation,
and template variable resolution.
"""

import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import marimo
from jinja2 import Environment, Template, TemplateSyntaxError, meta


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    
    severity: str  # "error", "warning", "info"
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    cell_id: Optional[str] = None
    code_snippet: Optional[str] = None
    fix_suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Format the issue for display."""
        parts = [f"[{self.severity.upper()}]"]
        if self.cell_id:
            parts.append(f"Cell {self.cell_id}")
        if self.line_number:
            parts.append(f"Line {self.line_number}")
            if self.column_number:
                parts.append(f"Col {self.column_number}")
        parts.append(self.message)
        
        result = " ".join(parts)
        if self.code_snippet:
            result += f"\n    {self.code_snippet}"
        if self.fix_suggestion:
            result += f"\n    Suggestion: {self.fix_suggestion}"
        return result


@dataclass
class ValidationResult:
    """Contains the complete validation result for a notebook."""
    
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "warning")
    
    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "info")
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)
        if issue.severity == "error":
            self.is_valid = False
    
    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.is_valid = self.is_valid and other.is_valid
        self.issues.extend(other.issues)
        self.metadata.update(other.metadata)
    
    def summary(self) -> str:
        """Get a summary of the validation result."""
        if self.is_valid:
            return "✅ Validation passed"
        else:
            return (f"❌ Validation failed: "
                   f"{self.error_count} errors, "
                   f"{self.warning_count} warnings, "
                   f"{self.info_count} info messages")


class NotebookValidator:
    """Comprehensive validator for marimo notebooks."""
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the validator.
        
        Args:
            strict_mode: If True, warnings are treated as errors
        """
        self.strict_mode = strict_mode
        self._known_imports = self._get_standard_imports()
        self._daglab_helpers = self._get_daglab_helpers()
    
    def validate(self, notebook_path: Path) -> ValidationResult:
        """
        Perform comprehensive validation on a notebook.
        
        Args:
            notebook_path: Path to the marimo notebook
            
        Returns:
            ValidationResult containing all issues found
        """
        result = ValidationResult()
        
        # Read notebook content
        try:
            content = notebook_path.read_text()
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Failed to read notebook: {e}"
            ))
            return result
        
        # Parse as Python module
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Invalid Python syntax: {e}",
                line_number=e.lineno,
                column_number=e.offset,
                code_snippet=e.text.strip() if e.text else None
            ))
            return result
        
        # Run individual validators
        result.merge(self.validate_python_syntax(content))
        result.merge(self.validate_marimo_structure(tree, content))
        result.merge(self.validate_imports(tree))
        result.merge(self.validate_cells(tree, content))
        
        # Check for template variables if it's a template
        if "{{" in content or "{%" in content:
            result.merge(self.validate_template_variables(content))
        
        # Apply strict mode
        if self.strict_mode:
            for issue in result.issues:
                if issue.severity == "warning":
                    issue.severity = "error"
            result.is_valid = result.error_count == 0
        
        return result
    
    def validate_python_syntax(self, content: str) -> ValidationResult:
        """Validate Python syntax is valid."""
        result = ValidationResult()
        
        # Check for syntax errors
        try:
            compile(content, "<string>", "exec")
        except SyntaxError as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Python syntax error: {e}",
                line_number=e.lineno,
                column_number=e.offset,
                code_snippet=e.text.strip() if e.text else None
            ))
            return result
        
        # Check for tokenization errors
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
        except tokenize.TokenError as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Tokenization error: {e}"
            ))
            return result
        
        # Check for common issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for tabs vs spaces
            if '\t' in line and '    ' in line:
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message="Mixed tabs and spaces for indentation",
                    line_number=i,
                    code_snippet=line.rstrip(),
                    fix_suggestion="Use consistent indentation (4 spaces recommended)"
                ))
            
            # Check for trailing whitespace
            if line.rstrip() != line:
                result.add_issue(ValidationIssue(
                    severity="info",
                    message="Trailing whitespace",
                    line_number=i,
                    fix_suggestion="Remove trailing whitespace"
                ))
        
        return result
    
    def validate_marimo_structure(self, tree: ast.Module, content: str) -> ValidationResult:
        """Verify marimo app structure."""
        result = ValidationResult()
        
        # Check for marimo.App() instantiation
        app_found = False
        app_var_name = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "marimo" and
                    node.func.attr == "App"):
                    app_found = True
                    
                    # Find the variable it's assigned to
                    parent = self._find_parent_assign(tree, node)
                    if parent and isinstance(parent.targets[0], ast.Name):
                        app_var_name = parent.targets[0].id
        
        if not app_found:
            result.add_issue(ValidationIssue(
                severity="error",
                message="No marimo.App() instantiation found",
                fix_suggestion="Add 'app = marimo.App()' to your notebook"
            ))
            return result
        
        if not app_var_name:
            result.add_issue(ValidationIssue(
                severity="error",
                message="marimo.App() not assigned to a variable",
                fix_suggestion="Assign marimo.App() to a variable, e.g., 'app = marimo.App()'"
            ))
            return result
        
        # Check for cell decorators
        cell_count = 0
        cell_functions = []
        
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Check if it has the @app.cell decorator
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Attribute) and
                        isinstance(decorator.value, ast.Name) and
                        decorator.value.id == app_var_name and
                        decorator.attr == "cell"):
                        cell_count += 1
                        cell_functions.append(node.name)
                        break
        
        if cell_count == 0:
            result.add_issue(ValidationIssue(
                severity="warning",
                message="No marimo cells found",
                fix_suggestion=f"Add cells using @{app_var_name}.cell decorator"
            ))
        
        result.metadata["cell_count"] = cell_count
        result.metadata["cell_functions"] = cell_functions
        
        # Check for proper cell structure
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in cell_functions:
                # Check for proper return statement
                has_return = any(isinstance(child, ast.Return) for child in ast.walk(node))
                if not has_return:
                    result.add_issue(ValidationIssue(
                        severity="info",
                        message=f"Cell '{node.name}' has no return statement",
                        line_number=node.lineno,
                        fix_suggestion="Consider returning values that other cells might need"
                    ))
        
        return result
    
    def validate_imports(self, tree: ast.Module) -> ValidationResult:
        """Check all imports are valid."""
        result = ValidationResult()
        imports = []
        
        # Collect all imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports.append((full_name, node.lineno))
        
        # Check each import
        for import_name, line_no in imports:
            # Check if it's a known standard library or common package
            base_module = import_name.split('.')[0]
            
            # Special handling for daglab imports
            if base_module == "daglab":
                if not self._is_valid_daglab_import(import_name):
                    result.add_issue(ValidationIssue(
                        severity="warning",
                        message=f"Unknown daglab import: {import_name}",
                        line_number=line_no,
                        fix_suggestion="Check if this daglab module exists"
                    ))
            # Check for typos in common imports
            elif base_module in self._get_common_typos():
                correct = self._get_common_typos()[base_module]
                result.add_issue(ValidationIssue(
                    severity="error",
                    message=f"Likely typo in import: {base_module}",
                    line_number=line_no,
                    fix_suggestion=f"Did you mean '{correct}'?"
                ))
        
        result.metadata["imports"] = [imp[0] for imp in imports]
        return result
    
    def validate_cells(self, tree: ast.Module, content: str) -> ValidationResult:
        """Check cell structure and dependencies."""
        result = ValidationResult()
        
        # Find all cell functions
        cells = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Check if it's a marimo cell
                is_cell = any(
                    isinstance(d, ast.Attribute) and
                    d.attr == "cell"
                    for d in node.decorator_list
                )
                if is_cell:
                    cells.append(node)
        
        # Analyze each cell
        for i, cell in enumerate(cells):
            cell_id = f"cell_{i+1}"
            
            # Check for unused variables
            defined_vars = set()
            used_vars = set()
            
            for node in ast.walk(cell):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        defined_vars.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        used_vars.add(node.id)
            
            # Check for large cells
            cell_lines = cell.end_lineno - cell.lineno + 1
            if cell_lines > 50:
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message=f"Cell '{cell.name}' is large ({cell_lines} lines)",
                    line_number=cell.lineno,
                    cell_id=cell_id,
                    fix_suggestion="Consider breaking into smaller cells"
                ))
            
            # Check for complex cells (high cyclomatic complexity)
            complexity = self._calculate_complexity(cell)
            if complexity > 10:
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message=f"Cell '{cell.name}' has high complexity ({complexity})",
                    line_number=cell.lineno,
                    cell_id=cell_id,
                    fix_suggestion="Consider simplifying the logic"
                ))
        
        result.metadata["total_cells"] = len(cells)
        return result
    
    def validate_template_variables(self, content: str) -> ValidationResult:
        """Ensure all template variables are properly defined."""
        result = ValidationResult()
        
        # Create Jinja2 environment
        env = Environment()
        
        try:
            # Parse template
            ast_tree = env.parse(content)
            
            # Find all variables
            undeclared = meta.find_undeclared_variables(ast_tree)
            
            # Common variables that should be available
            expected_vars = {
                "job_name", "asset_keys", "config", "metadata",
                "run_config", "tags", "dagster_instance"
            }
            
            # Check for undeclared variables
            for var in undeclared:
                if var not in expected_vars:
                    result.add_issue(ValidationIssue(
                        severity="warning",
                        message=f"Template variable '{var}' may not be defined",
                        fix_suggestion=f"Ensure '{var}' is passed when rendering template"
                    ))
            
            # Find all filters used
            filters_used = set()
            
            def find_filters(node):
                if hasattr(node, 'filters'):
                    for filter_node in node.filters:
                        filters_used.add(filter_node.name)
                for child in node.iter_child_nodes():
                    find_filters(child)
            
            find_filters(ast_tree)
            
            # Check for unknown filters
            known_filters = {'safe', 'escape', 'upper', 'lower', 'title', 
                           'trim', 'truncate', 'default', 'length'}
            for filter_name in filters_used:
                if filter_name not in known_filters:
                    result.add_issue(ValidationIssue(
                        severity="info",
                        message=f"Using custom filter '{filter_name}'",
                        fix_suggestion="Ensure this filter is registered"
                    ))
            
        except TemplateSyntaxError as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Template syntax error: {e}",
                line_number=e.lineno if hasattr(e, 'lineno') else None
            ))
        
        return result
    
    def _find_parent_assign(self, tree: ast.Module, target: ast.AST) -> Optional[ast.Assign]:
        """Find the assignment node that contains the target."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for value in ast.walk(node.value):
                    if value is target:
                        return node
        return None
    
    def _get_standard_imports(self) -> Set[str]:
        """Get set of standard library module names."""
        return {
            'os', 'sys', 'json', 'math', 'random', 'datetime', 'time',
            'pathlib', 'typing', 'collections', 'itertools', 'functools',
            're', 'ast', 'inspect', 'importlib', 'logging', 'warnings'
        }
    
    def _get_daglab_helpers(self) -> Set[str]:
        """Get set of known daglab helper functions."""
        return {
            'run_job', 'run_asset', 'discover', 'attach_metadata',
            'validate_config', 'track_performance', 'manage_state'
        }
    
    def _is_valid_daglab_import(self, import_name: str) -> bool:
        """Check if a daglab import is valid."""
        valid_modules = {
            'daglab.helpers.notebook',
            'daglab.client',
            'daglab.config',
            'daglab.templates'
        }
        
        # Check exact matches
        if import_name in valid_modules:
            return True
        
        # Check if it's a submodule of a valid module
        for module in valid_modules:
            if import_name.startswith(module + '.'):
                return True
        
        # Check if it's importing from helpers
        if import_name.startswith('daglab.helpers.notebook.'):
            helper_name = import_name.split('.')[-1]
            return helper_name in self._daglab_helpers
        
        return False
    
    def _get_common_typos(self) -> Dict[str, str]:
        """Get mapping of common import typos to correct names."""
        return {
            'numpy': 'numpy',
            'numy': 'numpy',
            'numoy': 'numpy',
            'panda': 'pandas',
            'pands': 'pandas',
            'matlotlib': 'matplotlib',
            'matplot': 'matplotlib',
            'request': 'requests',
            'beatifulsoup': 'beautifulsoup4',
            'beatifulsoup4': 'beautifulsoup4',
            'sklear': 'sklearn',
            'sickit-learn': 'scikit-learn'
        }
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Each decision point adds complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or operators add complexity
                complexity += len(child.values) - 1
        
        return complexity


def validate_notebook(
    notebook_path: Union[str, Path],
    strict: bool = False
) -> ValidationResult:
    """
    Convenience function to validate a notebook.
    
    Args:
        notebook_path: Path to the notebook
        strict: If True, treat warnings as errors
        
    Returns:
        ValidationResult
    """
    path = Path(notebook_path)
    validator = NotebookValidator(strict_mode=strict)
    return validator.validate(path)