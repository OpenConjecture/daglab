"""Migrate command for Jupyter notebook migration - Phase 5."""

import json
import re
import ast
import nbformat
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..helpers.feedback import UserFeedback
from ..helpers.notebook import NotebookManager
from ..runtime.errors import ValidationError, ErrorContext

console = Console()
app = typer.Typer(help="Migrate Jupyter notebooks to Marimo [Phase 5]")


class NotebookMigrator:
    """Handles Jupyter to Marimo notebook migration."""
    
    def __init__(self):
        self.feedback = UserFeedback()
        self.notebook_manager = NotebookManager()
        self.magic_command_map = {
            "%matplotlib": "mo.matplotlib_setup()",
            "%load_ext": "# Extension loading handled by marimo",
            "%%time": "@mo.timed\n",
            "%%timeit": "@mo.benchmark\n",
            "%pwd": "Path.cwd()",
            "%cd": "os.chdir",
            "%env": "os.environ",
        }
    
    def analyze_notebook(self, path: Path) -> Dict[str, Any]:
        """Analyze a Jupyter notebook for migration."""
        try:
            with open(path, 'r') as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as e:
            raise ValidationError(
                f"Failed to read notebook: {e}",
                context=ErrorContext(
                    operation="read_notebook",
                    resource=str(path),
                    suggestions=["Ensure the file is a valid Jupyter notebook"]
                )
            )
        
        analysis = {
            "path": path,
            "version": nb.nbformat,
            "total_cells": len(nb.cells),
            "code_cells": sum(1 for c in nb.cells if c.cell_type == "code"),
            "markdown_cells": sum(1 for c in nb.cells if c.cell_type == "markdown"),
            "has_outputs": any(c.get("outputs") for c in nb.cells if c.cell_type == "code"),
            "magic_commands": [],
            "imports": [],
            "widgets": False,
            "complexity": "simple",
        }
        
        # Analyze code cells
        for cell in nb.cells:
            if cell.cell_type == "code":
                source = cell.source
                
                # Check for magic commands
                for line in source.split('\n'):
                    if line.strip().startswith('%') or line.strip().startswith('%%'):
                        analysis["magic_commands"].append(line.strip())
                
                # Extract imports
                try:
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                analysis["imports"].append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                analysis["imports"].append(node.module)
                except:
                    pass
                
                # Check for widgets
                if "ipywidgets" in source or "widgets" in source:
                    analysis["widgets"] = True
        
        # Determine complexity
        if analysis["total_cells"] > 50 or analysis["widgets"] or len(analysis["magic_commands"]) > 10:
            analysis["complexity"] = "complex"
        elif analysis["total_cells"] > 20 or len(analysis["magic_commands"]) > 5:
            analysis["complexity"] = "moderate"
        
        return analysis
    
    def convert_magic_commands(self, source: str) -> str:
        """Convert Jupyter magic commands to Marimo equivalents."""
        lines = source.split('\n')
        converted = []
        
        for line in lines:
            if line.strip().startswith('%') or line.strip().startswith('%%'):
                # Find matching conversion
                converted_line = line
                for magic, replacement in self.magic_command_map.items():
                    if line.strip().startswith(magic):
                        converted_line = replacement
                        if line.strip() != magic:  # Has arguments
                            args = line.strip()[len(magic):].strip()
                            converted_line = f"{replacement}({args})"
                        break
                
                # Add comment for unmapped magic commands
                if converted_line == line:
                    converted_line = f"# TODO: Migrate magic command: {line}"
                
                converted.append(converted_line)
            else:
                converted.append(line)
        
        return '\n'.join(converted)
    
    def convert_cell(self, cell: Dict[str, Any], cell_index: int) -> Dict[str, Any]:
        """Convert a Jupyter cell to Marimo format."""
        if cell.cell_type == "markdown":
            return {
                "id": f"md_{cell_index}",
                "type": "markdown",
                "source": cell.source,
            }
        
        elif cell.cell_type == "code":
            # Convert magic commands
            source = self.convert_magic_commands(cell.source)
            
            # Add marimo imports if needed
            if cell_index == 0 and "import marimo as mo" not in source:
                source = "import marimo as mo\n\n" + source
            
            result = {
                "id": f"cell_{cell_index}",
                "type": "code",
                "source": source,
            }
            
            # Preserve outputs if requested
            if cell.get("outputs"):
                result["outputs"] = cell.outputs
            
            return result
        
        else:
            # Other cell types (raw, etc.)
            return {
                "id": f"other_{cell_index}",
                "type": "comment",
                "source": f"# Unsupported cell type: {cell.cell_type}\n{cell.get('source', '')}",
            }
    
    def migrate_notebook(self, source: Path, target: Path, preserve_outputs: bool = False) -> Dict[str, Any]:
        """Migrate a single notebook."""
        # Read source notebook
        with open(source, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Create marimo notebook structure
        marimo_nb = {
            "version": "0.1.0",
            "metadata": {
                "migrated_from": str(source),
                "migration_date": datetime.now().isoformat(),
                "original_kernel": nb.metadata.get("kernelspec", {}).get("name", "python3"),
            },
            "cells": [],
        }
        
        # Convert cells
        for i, cell in enumerate(nb.cells):
            converted = self.convert_cell(cell, i)
            if preserve_outputs or converted["type"] != "code":
                marimo_nb["cells"].append(converted)
            else:
                # Strip outputs for code cells
                converted.pop("outputs", None)
                marimo_nb["cells"].append(converted)
        
        # Write marimo notebook
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w') as f:
            json.dump(marimo_nb, f, indent=2)
        
        return {
            "source": source,
            "target": target,
            "cells_migrated": len(marimo_nb["cells"]),
            "outputs_preserved": preserve_outputs,
        }
    
    def create_dagster_asset(self, notebook_path: Path, asset_name: str) -> str:
        """Create a Dagster asset from a notebook."""
        asset_code = f'''
from dagster import asset, AssetIn
from daglab.runtime.notebook import run_marimo_notebook

@asset(
    name="{asset_name}",
    description="Asset created from migrated notebook: {notebook_path.name}",
    compute_kind="marimo",
)
def {asset_name.replace('-', '_')}(context):
    """Execute the migrated notebook as a Dagster asset."""
    return run_marimo_notebook(
        notebook_path="{notebook_path}",
        context=context,
    )
'''
        return asset_code
    
    def generate_migration_report(self, results: List[Dict[str, Any]]) -> Table:
        """Generate a migration report table."""
        table = Table(title="Migration Report", box=box.ROUNDED)
        table.add_column("Notebook", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Cells", justify="right")
        table.add_column("Issues", style="yellow")
        
        for result in results:
            status = "✅ Success" if result.get("success", True) else "❌ Failed"
            issues = result.get("issues", [])
            issue_text = ", ".join(issues) if issues else "None"
            
            table.add_row(
                result["source"].name,
                status,
                str(result.get("cells_migrated", 0)),
                issue_text,
            )
        
        return table


@app.callback(invoke_without_command=True)
def migrate(
    ctx: typer.Context,
    source: Path = typer.Argument(
        ...,
        help="Source path (file or directory with .ipynb files)"
    ),
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target directory for converted notebooks"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be migrated without converting"
    ),
    preserve_outputs: bool = typer.Option(
        False,
        "--preserve-outputs",
        help="Preserve cell outputs in migration"
    ),
    create_assets: bool = typer.Option(
        False,
        "--create-assets",
        help="Create Dagster assets from notebooks"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive migration with prompts"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files"
    ),
) -> None:
    """Migrate Jupyter notebooks to Marimo format.
    
    Convert existing Jupyter notebooks to Marimo notebooks while
    preserving functionality and improving integration with Dagster.
    
    Examples:
        daglab migrate notebook.ipynb
        daglab migrate notebooks/ --target marimo_notebooks/
        daglab migrate analysis.ipynb --dry-run
        daglab migrate ml_pipeline.ipynb --create-assets
    """
    if ctx.invoked_subcommand is None:
        migrator = NotebookMigrator()
        feedback = UserFeedback()
        
        # Validate source
        if not source.exists():
            feedback.error(f"Source path does not exist: {source}")
            raise typer.Exit(1)
        
        # Determine target directory
        if target is None:
            if source.is_file():
                target = source.parent / "marimo_notebooks"
            else:
                target = source.parent / f"{source.name}_marimo"
        
        # Collect notebooks to migrate
        notebooks = []
        if source.is_file():
            if source.suffix == ".ipynb":
                notebooks.append(source)
            else:
                feedback.error("Source file must be a .ipynb notebook")
                raise typer.Exit(1)
        else:
            notebooks = list(source.glob("**/*.ipynb"))
        
        if not notebooks:
            feedback.warning("No Jupyter notebooks found to migrate")
            return
        
        feedback.info(f"Found {len(notebooks)} notebook(s) to migrate")
        
        # Analyze notebooks
        if dry_run or interactive:
            with feedback.progress("Analyzing notebooks...") as progress:
                analyses = []
                for nb in notebooks:
                    progress.update(f"Analyzing {nb.name}...")
                    try:
                        analysis = migrator.analyze_notebook(nb)
                        analyses.append(analysis)
                    except Exception as e:
                        feedback.error(f"Failed to analyze {nb}: {e}")
                        if not force:
                            raise typer.Exit(1)
            
            # Show analysis
            analysis_table = Table(title="Notebook Analysis", box=box.ROUNDED)
            analysis_table.add_column("Notebook", style="cyan")
            analysis_table.add_column("Cells", justify="right")
            analysis_table.add_column("Complexity", style="yellow")
            analysis_table.add_column("Magic Commands", justify="right")
            analysis_table.add_column("Has Outputs", justify="center")
            
            for analysis in analyses:
                analysis_table.add_row(
                    analysis["path"].name,
                    str(analysis["total_cells"]),
                    analysis["complexity"],
                    str(len(analysis["magic_commands"])),
                    "✓" if analysis["has_outputs"] else "✗",
                )
            
            console.print(analysis_table)
            
            if dry_run:
                feedback.info("Dry run complete. No files were modified.")
                return
            
            if interactive and not feedback.confirm("Proceed with migration?"):
                feedback.info("Migration cancelled")
                return
        
        # Perform migration
        results = []
        assets_code = []
        
        with feedback.progress("Migrating notebooks...") as progress:
            for nb in notebooks:
                progress.update(f"Migrating {nb.name}...")
                
                try:
                    # Determine target path
                    if source.is_file():
                        target_path = target / nb.with_suffix(".marimo.py").name
                    else:
                        rel_path = nb.relative_to(source)
                        target_path = target / rel_path.with_suffix(".marimo.py")
                    
                    # Check if exists
                    if target_path.exists() and not force:
                        if interactive:
                            if not feedback.confirm(f"Overwrite {target_path}?"):
                                results.append({
                                    "source": nb,
                                    "success": False,
                                    "issues": ["Skipped - file exists"],
                                })
                                continue
                        else:
                            feedback.warning(f"Skipping {nb.name} - target exists. Use --force to overwrite.")
                            results.append({
                                "source": nb,
                                "success": False,
                                "issues": ["Target exists"],
                            })
                            continue
                    
                    # Migrate notebook
                    result = migrator.migrate_notebook(nb, target_path, preserve_outputs)
                    result["success"] = True
                    results.append(result)
                    
                    # Create asset if requested
                    if create_assets:
                        asset_name = nb.stem.replace(" ", "_").replace("-", "_")
                        asset_code = migrator.create_dagster_asset(target_path, asset_name)
                        assets_code.append((asset_name, asset_code))
                    
                except Exception as e:
                    feedback.error(f"Failed to migrate {nb}: {e}")
                    results.append({
                        "source": nb,
                        "success": False,
                        "issues": [str(e)],
                    })
                    if not force:
                        raise typer.Exit(1)
        
        # Show results
        console.print(migrator.generate_migration_report(results))
        
        # Write assets
        if assets_code:
            assets_file = target / "__dagster_assets__.py"
            with open(assets_file, 'w') as f:
                f.write("# Auto-generated Dagster assets from notebook migration\n\n")
                for name, code in assets_code:
                    f.write(code)
                    f.write("\n\n")
            
            feedback.success(f"Created {len(assets_code)} Dagster assets in {assets_file}")
        
        # Summary
        successful = sum(1 for r in results if r.get("success", False))
        feedback.success(f"Successfully migrated {successful}/{len(notebooks)} notebooks")
        
        if successful < len(notebooks):
            feedback.warning("Some notebooks failed to migrate. Check the report above.")


@app.command()
def check(
    notebook: Path = typer.Argument(..., help="Notebook to check for compatibility"),
) -> None:
    """Check a notebook's compatibility for migration."""
    migrator = NotebookMigrator()
    feedback = UserFeedback()
    
    try:
        analysis = migrator.analyze_notebook(notebook)
        
        # Compatibility score
        score = 100
        issues = []
        
        if analysis["magic_commands"]:
            score -= len(analysis["magic_commands"]) * 2
            issues.append(f"{len(analysis['magic_commands'])} magic commands need conversion")
        
        if analysis["widgets"]:
            score -= 20
            issues.append("Contains widgets that need manual migration")
        
        if analysis["complexity"] == "complex":
            score -= 10
            issues.append("Complex notebook may require manual review")
        
        # Show results
        panel = Panel(
            f"[bold]Compatibility Score: {max(0, score)}/100[/bold]\n\n"
            f"Notebook: {notebook.name}\n"
            f"Total Cells: {analysis['total_cells']}\n"
            f"Complexity: {analysis['complexity']}\n\n"
            + ("\n".join([f"⚠️  {issue}" for issue in issues]) if issues else "✅ No issues found"),
            title="Migration Compatibility Check",
            border_style="green" if score >= 80 else "yellow" if score >= 60 else "red",
        )
        console.print(panel)
        
    except Exception as e:
        feedback.error(f"Failed to analyze notebook: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
