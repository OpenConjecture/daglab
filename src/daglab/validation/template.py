"""
Template validation system for DagLab.

This module provides validation for Jinja2 templates used in notebook generation,
including syntax checking, structure validation, variable usage, and inheritance chains.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from jinja2 import (
    Environment, FileSystemLoader, Template, TemplateSyntaxError,
    meta, nodes, sandbox
)

from .notebook import ValidationIssue, ValidationResult


class TemplateValidator:
    """Validator for Jinja2 templates."""
    
    def __init__(self, template_dirs: Optional[List[Path]] = None):
        """
        Initialize the template validator.
        
        Args:
            template_dirs: List of directories containing templates
        """
        self.template_dirs = template_dirs or []
        self.env = self._create_environment()
        self._required_blocks = {'content', 'imports', 'setup'}
        self._optional_blocks = {'helpers', 'cleanup', 'metadata'}
    
    def validate(self, template_path: Path) -> ValidationResult:
        """
        Perform comprehensive validation on a template.
        
        Args:
            template_path: Path to the template file
            
        Returns:
            ValidationResult containing all issues found
        """
        result = ValidationResult()
        
        # Read template content
        try:
            content = template_path.read_text()
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Failed to read template: {e}"
            ))
            return result
        
        # Run validators
        result.merge(self.validate_template_syntax(content))
        result.merge(self.validate_template_structure(content))
        result.merge(self.validate_variable_usage(content))
        
        # Check inheritance if extends is used
        if "{% extends" in content:
            result.merge(self.validate_inheritance(content, template_path))
        
        # Test rendering with sample data
        result.merge(self.test_template_rendering(content))
        
        return result
    
    def validate_template_syntax(self, content: str) -> ValidationResult:
        """Check Jinja2 syntax is valid."""
        result = ValidationResult()
        
        try:
            # Parse the template
            self.env.parse(content)
        except TemplateSyntaxError as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Template syntax error: {e.message}",
                line_number=e.lineno,
                fix_suggestion="Check Jinja2 syntax documentation"
            ))
            return result
        
        # Check for common syntax issues
        lines = content.split('\n')
        
        # Check for unclosed tags
        tag_stack = []
        tag_pattern = re.compile(r'{%\s*(\w+).*?%}')
        end_tag_pattern = re.compile(r'{%\s*end(\w+).*?%}')
        
        for i, line in enumerate(lines, 1):
            # Find opening tags
            for match in tag_pattern.finditer(line):
                tag = match.group(1)
                if tag in ('if', 'for', 'block', 'macro', 'call'):
                    tag_stack.append((tag, i))
            
            # Find closing tags
            for match in end_tag_pattern.finditer(line):
                tag = match.group(1)
                if tag_stack and tag_stack[-1][0] == tag:
                    tag_stack.pop()
                else:
                    result.add_issue(ValidationIssue(
                        severity="error",
                        message=f"Unexpected closing tag 'end{tag}'",
                        line_number=i,
                        code_snippet=line.strip()
                    ))
        
        # Check for unclosed tags
        for tag, line_no in tag_stack:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Unclosed '{tag}' tag",
                line_number=line_no,
                fix_suggestion=f"Add '{{% end{tag} %}}' to close the block"
            ))
        
        # Check for common mistakes
        if "{{ }}" in content:
            result.add_issue(ValidationIssue(
                severity="warning",
                message="Empty variable substitution found",
                fix_suggestion="Remove empty {{ }} or add a variable"
            ))
        
        if re.search(r'{%[^%]*[{}][^%]*%}', content):
            result.add_issue(ValidationIssue(
                severity="warning",
                message="Possible syntax error: mismatched braces inside tag",
                fix_suggestion="Check for stray { or } inside {% %} tags"
            ))
        
        return result
    
    def validate_template_structure(self, content: str) -> ValidationResult:
        """Verify required blocks and structure."""
        result = ValidationResult()
        
        # Parse template AST
        try:
            ast = self.env.parse(content)
        except Exception:
            # Syntax errors handled elsewhere
            return result
        
        # Find all blocks
        blocks = set()
        extends = None
        
        for node in ast.body:
            if isinstance(node, nodes.Block):
                blocks.add(node.name)
            elif isinstance(node, nodes.Extends):
                extends = node.template.value if hasattr(node.template, 'value') else str(node.template)
        
        # Check required blocks (only if not extending)
        if not extends:
            missing_blocks = self._required_blocks - blocks
            for block in missing_blocks:
                result.add_issue(ValidationIssue(
                    severity="error",
                    message=f"Required block '{block}' is missing",
                    fix_suggestion=f"Add '{{% block {block} %}}'...'{{% endblock %}}'"
                ))
        
        # Check block content
        for node in ast.body:
            if isinstance(node, nodes.Block) and node.name == "imports":
                # Validate imports block has proper structure
                if not node.body:
                    result.add_issue(ValidationIssue(
                        severity="warning",
                        message="Empty imports block",
                        fix_suggestion="Add necessary imports or remove empty block"
                    ))
        
        # Check for recommended structure
        if "block metadata" not in content and not extends:
            result.add_issue(ValidationIssue(
                severity="info",
                message="No metadata block found",
                fix_suggestion="Consider adding a metadata block for notebook properties"
            ))
        
        result.metadata["blocks"] = list(blocks)
        result.metadata["extends"] = extends
        
        return result
    
    def validate_variable_usage(self, content: str) -> ValidationResult:
        """Check all variables are defined and used correctly."""
        result = ValidationResult()
        
        try:
            ast = self.env.parse(content)
        except Exception:
            return result
        
        # Find all variables
        undeclared = meta.find_undeclared_variables(ast)
        
        # Expected variables for notebook templates
        expected_vars = {
            # Standard template variables
            'job_name', 'asset_keys', 'config', 'metadata',
            'run_config', 'tags', 'dagster_instance',
            # Helper functions
            'run_job', 'run_asset', 'discover', 'attach_metadata',
            'validate_config', 'track_performance', 'manage_state',
            # Template metadata
            'template_name', 'template_version', 'author'
        }
        
        # Check for undefined variables
        undefined_vars = undeclared - expected_vars
        for var in undefined_vars:
            # Find line number
            line_no = None
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if f'{{{{ {var}' in line or f'{{{{ {var} ' in line:
                    line_no = i
                    break
            
            result.add_issue(ValidationIssue(
                severity="warning",
                message=f"Variable '{var}' may not be defined",
                line_number=line_no,
                fix_suggestion=f"Ensure '{var}' is provided when rendering"
            ))
        
        # Check for unused set variables
        set_vars = set()
        used_vars = set()
        
        def find_assignments(node):
            if isinstance(node, nodes.Assign):
                set_vars.add(node.target.name)
            for child in node.iter_child_nodes():
                find_assignments(child)
        
        def find_usage(node):
            if isinstance(node, nodes.Name):
                used_vars.add(node.name)
            for child in node.iter_child_nodes():
                find_usage(child)
        
        find_assignments(ast)
        find_usage(ast)
        
        unused = set_vars - used_vars
        for var in unused:
            result.add_issue(ValidationIssue(
                severity="info",
                message=f"Variable '{var}' is set but never used",
                fix_suggestion="Remove unused variable or use it"
            ))
        
        result.metadata["variables"] = list(undeclared)
        return result
    
    def validate_inheritance(self, content: str, template_path: Path) -> ValidationResult:
        """Check template inheritance chain is valid."""
        result = ValidationResult()
        
        # Extract parent template
        extends_match = re.search(r'{%\s*extends\s*["\'](.+?)["\'].*?%}', content)
        if not extends_match:
            return result
        
        parent_name = extends_match.group(1)
        
        # Try to find parent template
        parent_found = False
        parent_path = None
        
        # Check in template directories
        for template_dir in self.template_dirs:
            potential_path = template_dir / parent_name
            if potential_path.exists():
                parent_found = True
                parent_path = potential_path
                break
        
        # Check relative to current template
        if not parent_found:
            potential_path = template_path.parent / parent_name
            if potential_path.exists():
                parent_found = True
                parent_path = potential_path
        
        if not parent_found:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Parent template '{parent_name}' not found",
                fix_suggestion="Check template path or add parent template"
            ))
            return result
        
        # Validate parent template
        parent_result = TemplateValidator(self.template_dirs).validate(parent_path)
        if not parent_result.is_valid:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Parent template '{parent_name}' has validation errors"
            ))
        
        # Check block compatibility
        try:
            parent_content = parent_path.read_text()
            parent_ast = self.env.parse(parent_content)
            child_ast = self.env.parse(content)
            
            # Get blocks from parent and child
            parent_blocks = {
                node.name for node in parent_ast.body 
                if isinstance(node, nodes.Block)
            }
            child_blocks = {
                node.name for node in child_ast.body 
                if isinstance(node, nodes.Block)
            }
            
            # Check for undefined blocks
            undefined_blocks = child_blocks - parent_blocks
            for block in undefined_blocks:
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message=f"Block '{block}' not defined in parent template",
                    fix_suggestion="Check if this block name is correct"
                ))
            
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity="warning",
                message=f"Could not analyze parent template: {e}"
            ))
        
        result.metadata["parent_template"] = str(parent_path)
        return result
    
    def test_template_rendering(self, content: str) -> ValidationResult:
        """Test template rendering with sample data."""
        result = ValidationResult()
        
        # Sample data for testing
        test_data = {
            'job_name': 'test_job',
            'asset_keys': ['asset1', 'asset2'],
            'config': {'param1': 'value1', 'param2': 123},
            'metadata': {'author': 'test', 'version': '1.0'},
            'run_config': {},
            'tags': ['test', 'validation'],
            'dagster_instance': 'local',
            # Helper functions (mock implementations)
            'run_job': lambda x: f"Running job: {x}",
            'run_asset': lambda x: f"Running asset: {x}",
            'discover': lambda: "Discovering entities...",
            'attach_metadata': lambda x, y: f"Attaching {y} to {x}",
            'validate_config': lambda x: True,
            'track_performance': lambda: "Tracking performance...",
            'manage_state': lambda x: f"Managing state: {x}"
        }
        
        try:
            # Create template
            template = self.env.from_string(content)
            
            # Try to render
            rendered = template.render(**test_data)
            
            # Basic checks on rendered content
            if not rendered.strip():
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message="Template renders to empty content",
                    fix_suggestion="Check template logic and blocks"
                ))
            
            # Check for common rendering issues
            if "{{" in rendered or "{%" in rendered:
                result.add_issue(ValidationIssue(
                    severity="warning",
                    message="Unprocessed template syntax in output",
                    fix_suggestion="Some template variables may not be rendered"
                ))
            
            # Check if it's valid Python (for notebook templates)
            if rendered.strip():
                try:
                    compile(rendered, '<template>', 'exec')
                except SyntaxError as e:
                    result.add_issue(ValidationIssue(
                        severity="error",
                        message=f"Rendered template has Python syntax error: {e}",
                        line_number=e.lineno,
                        fix_suggestion="Check template output for valid Python"
                    ))
            
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity="error",
                message=f"Template rendering failed: {e}",
                fix_suggestion="Check template syntax and variable usage"
            ))
        
        return result
    
    def _create_environment(self) -> Environment:
        """Create Jinja2 environment with proper configuration."""
        loaders = []
        
        # Add template directories
        for template_dir in self.template_dirs:
            if template_dir.exists():
                loaders.append(FileSystemLoader(str(template_dir)))
        
        # Use sandbox environment for safety
        env = sandbox.SandboxedEnvironment(
            loader=FileSystemLoader(loaders) if loaders else None,
            autoescape=False,  # For Python code generation
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters if needed
        env.filters['python_repr'] = repr
        env.filters['json'] = lambda x: __import__('json').dumps(x)
        
        return env


def validate_template(
    template_path: Path,
    template_dirs: Optional[List[Path]] = None
) -> ValidationResult:
    """
    Convenience function to validate a template.
    
    Args:
        template_path: Path to the template
        template_dirs: Additional template directories
        
    Returns:
        ValidationResult
    """
    validator = TemplateValidator(template_dirs=template_dirs)
    return validator.validate(template_path)