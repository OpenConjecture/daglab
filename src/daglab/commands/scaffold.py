"""Scaffold command for notebook generation."""

import typer
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from rich import print as rprint
import json
import subprocess
import sys
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFoundError
import importlib.metadata

console = Console()
app = typer.Typer(help="Generate notebook templates")


def get_daglab_version() -> str:
    """Get the current daglab version."""
    try:
        return importlib.metadata.version("daglab")
    except:
        return "0.1.0"


def get_template_dir() -> Path:
    """Get the templates directory."""
    return Path(__file__).parent.parent / "templates" / "notebooks"


def list_available_templates() -> List[str]:
    """List available notebook templates."""
    template_dir = get_template_dir()
    templates = []
    if template_dir.exists():
        for item in template_dir.iterdir():
            if item.is_dir() and (item / "notebook.py").exists():
                templates.append(item.name)
    return sorted(templates)


def validate_target_selection(asset: Optional[str], job: Optional[str], from_selection: Optional[str]) -> tuple[str, str]:
    """Validate that only one target is specified and return the type and name."""
    targets = [(asset, 'asset'), (job, 'job'), (from_selection, 'selection')]
    specified = [(name, type_) for name, type_ in targets if name is not None]
    
    if len(specified) == 0:
        raise typer.BadParameter("Must specify one of --asset, --job, or --from-selection")
    elif len(specified) > 1:
        raise typer.BadParameter("Can only specify one of --asset, --job, or --from-selection")
    
    return specified[0][1], specified[0][0]


def generate_filename(target_type: str, target_name: str, template: str) -> str:
    """Generate a default filename based on target and template."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = []
    
    if target_name:
        # Clean target name for filename
        clean_name = target_name.replace("/", "_").replace(".", "_").replace("-", "_")
        parts.append(clean_name)
    
    parts.append(template)
    parts.append("notebook")
    
    return "_".join(parts) + ".py"


def parse_template_vars(template_vars: List[str]) -> Dict[str, Any]:
    """Parse template variables from command line."""
    vars_dict = {}
    for var in template_vars:
        if "=" not in var:
            raise typer.BadParameter(f"Template variable must be in format key=value, got: {var}")
        key, value = var.split("=", 1)
        # Try to parse as JSON first, then as string
        try:
            vars_dict[key] = json.loads(value)
        except:
            vars_dict[key] = value
    return vars_dict


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render a notebook template with the given context."""
    template_dir = get_template_dir()
    env = Environment(loader=FileSystemLoader(template_dir))
    
    try:
        template = env.get_template(f"{template_name}/notebook.py")
        return template.render(**context)
    except TemplateNotFoundError:
        raise typer.BadParameter(f"Template '{template_name}' not found. Available templates: {', '.join(list_available_templates())}")


def validate_notebook_syntax(content: str) -> bool:
    """Validate that the generated notebook has valid Python syntax."""
    try:
        compile(content, '<generated>', 'exec')
        return True
    except SyntaxError:
        return False


def commit_to_git(filepath: Path, message: str) -> bool:
    """Commit the generated file to git."""
    try:
        # Check if we're in a git repository
        result = subprocess.run(["git", "rev-parse", "--git-dir"], 
                              capture_output=True, text=True, check=True)
        
        # Add file
        subprocess.run(["git", "add", str(filepath)], check=True)
        
        # Commit
        subprocess.run(["git", "commit", "-m", message], check=True)
        
        return True
    except subprocess.CalledProcessError:
        return False


@app.callback(invoke_without_command=True)
def scaffold(
    ctx: typer.Context,
    # Target selection (mutually exclusive)
    job: Optional[str] = typer.Option(
        None,
        "--job",
        "-j",
        help="Target Dagster job for the notebook"
    ),
    asset: Optional[str] = typer.Option(
        None,
        "--asset",
        "-a",
        help="Target Dagster asset for the notebook"
    ),
    from_selection: Optional[str] = typer.Option(
        None,
        "--from-selection",
        "-s",
        help="Generate from a selection/query"
    ),
    # Template configuration
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Template to use (default, minimal, ml)"
    ),
    filename: Optional[str] = typer.Option(
        None,
        "--filename",
        "-f",
        help="Custom filename for the notebook"
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        help="Title for the notebook"
    ),
    # Feature flags
    no_inprocess: bool = typer.Option(
        False,
        "--no-inprocess",
        help="Disable in-process asset creation"
    ),
    no_attach: bool = typer.Option(
        False,
        "--no-attach",
        help="Don't attach to target asset/job"
    ),
    # Additional options
    validate_config: bool = typer.Option(
        False,
        "--validate-config",
        help="Validate configuration after generation"
    ),
    seed_data: bool = typer.Option(
        False,
        "--seed-data",
        help="Include sample data generation"
    ),
    git_commit: bool = typer.Option(
        False,
        "--git-commit",
        help="Commit generated file to git"
    ),
    template_vars: List[str] = typer.Option(
        [],
        "--template-vars",
        "-v",
        help="Custom template variables (key=value format)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-F",
        help="Force overwrite existing files"
    ),
    output_dir: Path = typer.Option(
        Path("notebooks"),
        "--output-dir",
        "-o",
        help="Output directory for generated notebooks"
    ),
) -> None:
    """Generate notebook templates for Dagster assets and jobs.
    
    This command generates Marimo notebook templates pre-configured
    with Dagster integration, best practices, and example code.
    
    Examples:
    
        # Generate notebook for an asset
        daglab scaffold --asset my_model --template ml
        
        # Generate notebook for a job with custom title
        daglab scaffold --job daily_pipeline --title "Daily ETL Pipeline"
        
        # Generate with seed data and validation
        daglab scaffold --asset data_processor --seed-data --validate-config
        
        # Generate with custom template variables
        daglab scaffold --asset model -v "model_type=random_forest" -v "epochs=100"
        
        # Force overwrite and commit to git
        daglab scaffold --job pipeline --force --git-commit
    """
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        # Validate target selection
        target_type, target_name = validate_target_selection(asset, job, from_selection)
        
        # Show available templates
        available_templates = list_available_templates()
        if template not in available_templates:
            console.print(f"[red]Error:[/red] Template '{template}' not found.")
            console.print(f"Available templates: {', '.join(available_templates)}")
            raise typer.Exit(1)
        
        # Build template context
        context = {
            "daglab_version": get_daglab_version(),
            "target_type": target_type,
            "target_name": target_name,
            "title": title or f"{target_name.title()} Notebook" if target_name else "DAGLab Notebook",
            "template": template,
            "no_inprocess": no_inprocess,
            "no_attach": no_attach,
            "validate_config": validate_config,
            "seed_data": seed_data,
            "asset_name": f"{target_name}_output" if target_name else "notebook_output",
            "width": "full" if template == "ml" else "medium",
        }
        
        # Add custom template variables
        if template_vars:
            custom_vars = parse_template_vars(template_vars)
            context["template_vars"] = custom_vars
            context.update(custom_vars)
        
        # Generate filename
        if not filename:
            filename = generate_filename(target_type, target_name, template)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        # Check if file exists
        if output_path.exists() and not force:
            if not Confirm.ask(f"[yellow]File {output_path} already exists. Overwrite?[/yellow]"):
                console.print("[red]Aborted.[/red]")
                raise typer.Exit(1)
        
        # Render template with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Render template
            task = progress.add_task("Rendering template...", total=None)
            content = render_template(template, context)
            progress.update(task, completed=True)
            
            # Validate syntax
            if validate_config:
                task = progress.add_task("Validating notebook syntax...", total=None)
                if not validate_notebook_syntax(content):
                    console.print("[red]Error:[/red] Generated notebook has syntax errors.")
                    raise typer.Exit(1)
                progress.update(task, completed=True)
            
            # Write file
            task = progress.add_task(f"Writing {filename}...", total=None)
            output_path.write_text(content)
            progress.update(task, completed=True)
            
            # Commit to git
            if git_commit:
                task = progress.add_task("Committing to git...", total=None)
                commit_message = f"Add {template} notebook for {target_type} '{target_name}'"
                if commit_to_git(output_path, commit_message):
                    progress.update(task, completed=True)
                else:
                    progress.update(task, description="[yellow]Git commit skipped (not in repo or error)[/yellow]")
        
        # Show success message
        success_panel = Panel(
            f"[bold green]✓[/bold green] Notebook successfully generated!\n\n"
            f"[cyan]File:[/cyan] {output_path}\n"
            f"[cyan]Template:[/cyan] {template}\n"
            f"[cyan]Target:[/cyan] {target_type} '{target_name}'\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"1. Open the notebook: [cyan]marimo edit {output_path}[/cyan]\n"
            f"2. Modify the template to fit your needs\n"
            f"3. {'Run [cyan]daglab sync[/cyan] to register with Dagster' if not no_inprocess else 'Export for use in your pipeline'}\n"
            f"4. View in Dagster UI at [cyan]http://localhost:3000[/cyan]",
            title="[bold green]Notebook Generated[/bold green]",
            border_style="green"
        )
        console.print(success_panel)
        
        # Show template info
        if template == "ml":
            info_table = Table(title="ML Template Features", show_header=False)
            info_table.add_column("Feature", style="cyan")
            info_table.add_row("📊 Exploratory data analysis")
            info_table.add_row("🔍 Feature engineering")
            info_table.add_row("🤖 Model training & evaluation")
            info_table.add_row("📈 Performance visualization")
            info_table.add_row("💾 Dagster asset integration")
            console.print(info_table)
        
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list_templates():
    """List all available notebook templates."""
    templates = list_available_templates()
    
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    
    table = Table(title="Available Notebook Templates")
    table.add_column("Template", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    
    descriptions = {
        "default": "Full-featured template with data processing and visualization",
        "minimal": "Minimal template for quick starts",
        "ml": "Machine learning pipeline with training and evaluation",
    }
    
    for template in templates:
        desc = descriptions.get(template, "Custom template")
        table.add_row(template, desc)
    
    console.print(table)


if __name__ == "__main__":
    app()
