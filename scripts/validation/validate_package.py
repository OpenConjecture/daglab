#!/usr/bin/env python3
"""Validate DagLab package structure and metadata."""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

try:
    import toml
except ImportError:
    import tomllib as toml

console = Console()


class ValidationError(Exception):
    """Package validation error."""
    pass


class PackageValidator:
    """Validate package structure and metadata."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src" / "daglab"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_all(self) -> bool:
        """Run all validations."""
        validations = [
            ("Project structure", self.validate_structure),
            ("Package metadata", self.validate_metadata),
            ("Python modules", self.validate_modules),
            ("Dependencies", self.validate_dependencies),
            ("Documentation", self.validate_documentation),
            ("Tests", self.validate_tests),
            ("Build files", self.validate_build_files),
        ]
        
        results = {}
        for name, validator in validations:
            try:
                validator()
                results[name] = True
                console.print(f"[green]✓[/green] {name} validation passed")
            except ValidationError as e:
                results[name] = False
                console.print(f"[red]✗[/red] {name} validation failed: {e}")
                self.errors.append(f"{name}: {e}")
        
        return all(results.values())
    
    def validate_structure(self) -> None:
        """Validate project structure."""
        required_dirs = [
            "src/daglab",
            "tests",
            "docs",
            "examples",
            "scripts",
        ]
        
        required_files = [
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "CHANGELOG.md",
            ".gitignore",
            "src/daglab/__init__.py",
            "src/daglab/py.typed",
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                raise ValidationError(f"Missing required directory: {dir_path}")
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                raise ValidationError(f"Missing required file: {file_path}")
    
    def validate_metadata(self) -> None:
        """Validate package metadata in pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        
        try:
            with open(pyproject_path, "rb") as f:
                data = toml.load(f)
        except Exception as e:
            raise ValidationError(f"Failed to load pyproject.toml: {e}")
        
        # Check required fields
        required_fields = {
            "build-system": ["requires", "build-backend"],
            "project": ["name", "description", "readme", "requires-python", 
                       "license", "authors", "classifiers", "dependencies"],
        }
        
        for section, fields in required_fields.items():
            if section not in data:
                raise ValidationError(f"Missing section in pyproject.toml: [{section}]")
            
            for field in fields:
                if field not in data[section]:
                    raise ValidationError(f"Missing field in pyproject.toml: {section}.{field}")
        
        # Validate specific values
        project = data["project"]
        
        if project["name"] != "daglab":
            raise ValidationError(f"Invalid project name: {project['name']}")
        
        # Check Python version requirement
        python_req = project["requires-python"]
        if not python_req.startswith(">=3.11"):
            self.warnings.append(f"Python requirement might be too restrictive: {python_req}")
    
    def validate_modules(self) -> None:
        """Validate Python module structure."""
        # Check all __init__.py files exist
        expected_modules = [
            "core",
            "compute", 
            "storage",
            "integrations",
            "runtime",
            "helpers",
        ]
        
        for module in expected_modules:
            module_path = self.src_dir / module / "__init__.py"
            if not module_path.exists():
                raise ValidationError(f"Missing module: daglab.{module}")
        
        # Check for common issues in Python files
        python_files = list(self.src_dir.rglob("*.py"))
        
        for py_file in python_files:
            if py_file.name == "__pycache__":
                continue
                
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse to check for syntax errors
                ast.parse(content)
                
                # Check for common issues
                if "print(" in content and "# pragma: no cover" not in content:
                    self.warnings.append(f"Found print statement in {py_file.relative_to(self.project_root)}")
                
            except SyntaxError as e:
                raise ValidationError(f"Syntax error in {py_file}: {e}")
    
    def validate_dependencies(self) -> None:
        """Validate dependency specifications."""
        pyproject_path = self.project_root / "pyproject.toml"
        
        with open(pyproject_path, "rb") as f:
            data = toml.load(f)
        
        # Check core dependencies
        deps = data["project"]["dependencies"]
        
        # Validate dependency format
        dep_pattern = re.compile(r"^[a-zA-Z0-9\-_]+(\[.*\])?[><=!~]+[0-9\.]+")
        
        for dep in deps:
            if not dep_pattern.match(dep):
                self.warnings.append(f"Unusual dependency format: {dep}")
        
        # Check optional dependencies
        optional = data["project"].get("optional-dependencies", {})
        
        for group, group_deps in optional.items():
            for dep in group_deps:
                if not dep_pattern.match(dep):
                    self.warnings.append(f"Unusual dependency format in [{group}]: {dep}")
    
    def validate_documentation(self) -> None:
        """Validate documentation files."""
        docs_dir = self.project_root / "docs"
        
        # Check for basic documentation
        required_docs = ["index.md", "installation.md", "quickstart.md", "api.md"]
        
        for doc in required_docs:
            doc_path = docs_dir / doc
            if not doc_path.exists():
                self.warnings.append(f"Missing documentation: {doc}")
        
        # Check README
        readme = self.project_root / "README.md"
        with open(readme, "r") as f:
            content = f.read()
        
        # Check for required sections
        required_sections = ["Installation", "Usage", "License"]
        for section in required_sections:
            if f"## {section}" not in content and f"# {section}" not in content:
                self.warnings.append(f"README missing section: {section}")
    
    def validate_tests(self) -> None:
        """Validate test structure."""
        tests_dir = self.project_root / "tests"
        
        # Check for test files
        test_files = list(tests_dir.rglob("test_*.py"))
        
        if len(test_files) < 5:
            self.warnings.append(f"Only {len(test_files)} test files found")
        
        # Check for conftest.py
        if not (tests_dir / "conftest.py").exists():
            self.warnings.append("Missing tests/conftest.py")
    
    def validate_build_files(self) -> None:
        """Validate build configuration files."""
        # Check MANIFEST.in
        manifest = self.project_root / "MANIFEST.in"
        if manifest.exists():
            with open(manifest, "r") as f:
                content = f.read()
            
            # Check for common includes
            expected = ["LICENSE", "README.md", "CHANGELOG.md"]
            for file in expected:
                if f"include {file}" not in content:
                    self.warnings.append(f"MANIFEST.in should include {file}")
        
        # Check .gitignore
        gitignore = self.project_root / ".gitignore"
        if gitignore.exists():
            with open(gitignore, "r") as f:
                content = f.read()
            
            # Check for common Python ignores
            expected_ignores = ["__pycache__", "*.egg-info", "dist/", "build/", ".tox/"]
            for pattern in expected_ignores:
                if pattern not in content:
                    self.warnings.append(f".gitignore should include {pattern}")


def show_file_tree(project_root: Path) -> None:
    """Show project file tree."""
    tree = Tree("[bold]DagLab Project Structure[/bold]")
    
    def add_tree_nodes(tree_node: Tree, path: Path, max_depth: int = 3, current_depth: int = 0):
        if current_depth >= max_depth:
            return
        
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        
        for item in items:
            if item.name.startswith(".") and item.name not in [".gitignore", ".gitattributes"]:
                continue
            
            if item.is_dir():
                if item.name in ["__pycache__", ".tox", "dist", "build", ".egg-info"]:
                    continue
                
                subtree = tree_node.add(f"[bold cyan]{item.name}/[/bold cyan]")
                add_tree_nodes(subtree, item, max_depth, current_depth + 1)
            else:
                emoji = "📄" if item.suffix in [".py", ".toml", ".txt"] else "📃"
                tree_node.add(f"{emoji} {item.name}")
    
    add_tree_nodes(tree, project_root, max_depth=3)
    console.print(tree)


@click.command()
@click.option("--show-tree/--no-tree", default=True, help="Show project file tree")
@click.option("--strict/--no-strict", default=False, 
              help="Treat warnings as errors")
def validate(show_tree: bool, strict: bool) -> None:
    """Validate DagLab package structure and metadata."""
    project_root = Path(__file__).parent.parent.parent
    
    console.print(Panel.fit(
        "[bold blue]DagLab Package Validator[/bold blue]\n"
        "Checking package structure and metadata",
        border_style="blue"
    ))
    
    # Show file tree if requested
    if show_tree:
        console.print()
        show_file_tree(project_root)
        console.print()
    
    # Run validation
    validator = PackageValidator(project_root)
    
    console.print("[bold]Running validations...[/bold]\n")
    success = validator.validate_all()
    
    # Show results
    console.print()
    
    if validator.warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in validator.warnings:
            console.print(f"  ⚠️  {warning}")
        console.print()
    
    if validator.errors:
        console.print("[bold red]Errors:[/bold red]")
        for error in validator.errors:
            console.print(f"  ❌ {error}")
        console.print()
    
    # Summary
    if success and not (strict and validator.warnings):
        console.print("[bold green]✅ Package validation passed![/bold green]")
        sys.exit(0)
    else:
        console.print("[bold red]❌ Package validation failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    validate()