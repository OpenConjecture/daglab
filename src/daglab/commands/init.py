"""Initialize command for Daglab projects."""

import typer
from pathlib import Path
from typing import Optional
import yaml
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from daglab.runtime.errors import DaglabError, ExitCode
from daglab.runtime.logging import get_logger

app = typer.Typer()
console = Console()
logger = get_logger(__name__)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Initialize a new Daglab project."""
    # If no subcommand is given, run the main init command
    if ctx.invoked_subcommand is None:
        ctx.invoke(init_project)


@app.command(name="project")
def init_project(
    path: Path = typer.Argument(Path.cwd(), help="Project directory path"),
    name: str = typer.Option("my-project", "--name", "-n", help="Project name"),
    template: str = typer.Option("basic", "--template", "-t", help="Project template"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing project"),
):
    """Initialize a new Daglab project with the specified template."""
    project_path = path / name
    
    # Check if project already exists
    if project_path.exists() and not force:
        console.print(Panel(
            f"[yellow]Project '{name}' already exists at {project_path}[/yellow]\n"
            "Use --force to overwrite",
            title="Warning",
            border_style="yellow"
        ))
        raise typer.Exit(17)  # File exists error
    
    console.print(Panel.fit(
        f"[bold]Initializing Daglab Project[/bold]\n"
        f"Name: [cyan]{name}[/cyan]\n"
        f"Template: [cyan]{template}[/cyan]\n"
        f"Path: [dim]{project_path}[/dim]",
        border_style="blue"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create project structure
        task = progress.add_task("Creating project structure...", total=5)
        
        project_path.mkdir(parents=True, exist_ok=True)
        progress.update(task, advance=1, description="Created project directory")
        
        # Create directories
        dirs = {
            "dags": "DAG definitions",
            "data": "Data files",
            "logs": "Execution logs",
            "artifacts": "Generated artifacts",
            "config": "Configuration files",
            "notebooks": "Marimo notebooks",
            "tests": "Test files",
        }
        
        for dir_name, desc in dirs.items():
            dir_path = project_path / dir_name
            dir_path.mkdir(exist_ok=True)
            # Add .gitkeep to empty directories
            (dir_path / ".gitkeep").touch()
        
        progress.update(task, advance=1, description="Created project directories")
        
        # Create configuration
        config_data = {
            "project": {
                "name": name,
                "version": "0.1.0",
                "description": f"Daglab project: {name}",
            },
            "runtime": {
                "executor": "local",
                "max_workers": 4,
                "timeout": 3600,
            },
            "storage": {
                "backend": "local",
                "path": "./artifacts",
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "./logs/daglab.log",
            },
            "marimo": {
                "auto_reload": True,
                "port": 8890,
            }
        }
        
        config_path = project_path / "config" / "daglab.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        progress.update(task, advance=1, description="Created configuration")
        
        # Create .gitignore
        gitignore_content = """# Daglab
/logs/
/artifacts/
/data/*.tmp
*.pyc
__pycache__/
.daglab/
.env
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
"""
        
        with open(project_path / ".gitignore", "w") as f:
            f.write(gitignore_content)
        
        progress.update(task, advance=1, description="Created .gitignore")
        
        # Create README
        readme_content = f"""# {name}

A Daglab project for scaffolding and running paired marimo notebooks for Dagster assets & jobs.

## Getting Started

1. Install dependencies:
   ```bash
   pip install daglab
   ```

2. List available DAGs:
   ```bash
   daglab list
   ```

3. Run a DAG:
   ```bash
   daglab run <dag-name>
   ```

## Project Structure

- `dags/` - DAG definitions
- `notebooks/` - Marimo notebooks
- `data/` - Data files
- `config/` - Configuration files
- `artifacts/` - Generated artifacts
- `logs/` - Execution logs
- `tests/` - Test files

## Configuration

Edit `config/daglab.yaml` to customize project settings.
"""
        
        with open(project_path / "README.md", "w") as f:
            f.write(readme_content)
        
        progress.update(task, advance=1, description="Project initialized")
    
    # Show success message
    console.print("\n")
    success_panel = Panel(
        f"[green]✓ Project '{name}' created successfully![/green]\n\n"
        "[bold]Next steps:[/bold]\n"
        f"  1. cd {project_path}\n"
        "  2. daglab doctor       # Check system health\n"
        "  3. daglab list         # List available DAGs\n"
        "  4. daglab run <dag>    # Run a DAG",
        title="Success",
        border_style="green"
    )
    console.print(success_panel)


@app.command(name="template")
def list_templates():
    """List available project templates."""
    console.print(Panel.fit(
        "[bold]Available Project Templates[/bold]",
        border_style="blue"
    ))
    
    templates = [
        {
            "name": "basic",
            "description": "Basic project structure with sample DAG",
            "features": ["Local executor", "File storage", "JSON logging"],
        },
        {
            "name": "etl",
            "description": "ETL pipeline template with data processing examples",
            "features": ["Data validation", "Transform chains", "Error handling"],
        },
        {
            "name": "ml",
            "description": "Machine learning pipeline template",
            "features": ["Model training", "Evaluation metrics", "Artifact tracking"],
        },
        {
            "name": "dagster",
            "description": "Dagster integration template",
            "features": ["Asset definitions", "Job configurations", "IO managers"],
        },
    ]
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Template", style="cyan", no_wrap=True)
    table.add_column("Description", style="dim")
    table.add_column("Features", style="green")
    
    for template in templates:
        features = "\n".join(f"• {f}" for f in template["features"])
        table.add_row(
            template["name"],
            template["description"],
            features
        )
    
    console.print(table)
    console.print("\n[dim]Use 'daglab init --template <name>' to create a project[/dim]")