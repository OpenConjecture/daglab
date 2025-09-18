"""Initialize daglab in a Dagster project."""

import os
import shutil
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def detect_dagster_project(path: Path) -> Tuple[bool, str]:
    """Detect if path contains a Dagster project.
    
    Returns:
        Tuple of (is_dagster_project, project_type)
    """
    # Check for dagster.yaml
    if (path / "dagster.yaml").exists():
        return True, "dagster.yaml"
    
    # Check for workspace.yaml
    if (path / "workspace.yaml").exists():
        return True, "workspace.yaml"
    
    # Check for pyproject.toml with dagster dependency
    if (path / "pyproject.toml").exists():
        try:
            # Try to import tomli for Python < 3.11
            try:
                import tomli
            except ImportError:
                import tomllib as tomli
                
            with open(path / "pyproject.toml", "rb") as f:
                data = tomli.load(f)
                deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                if "dagster" in deps:
                    return True, "pyproject.toml"
                
                # Also check setup.py style dependencies
                deps = data.get("project", {}).get("dependencies", [])
                if any("dagster" in dep for dep in deps):
                    return True, "pyproject.toml"
        except Exception:
            pass
    
    return False, ""


def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))
            return True
    except OSError:
        return False


def get_available_port(start_port: int) -> int:
    """Find an available port starting from start_port."""
    port = start_port
    while port < 65535:
        if is_port_available(port):
            return port
        port += 1
    raise RuntimeError(f"No available ports found starting from {start_port}")


def create_daglab_config(
    project_path: Path,
    notebooks_dir: str,
    dagster_port: int,
    daglab_port: int,
    template: str
) -> Dict:
    """Create daglab configuration."""
    config = {
        "project": {
            "name": project_path.name,
            "type": template,
            "notebooks_dir": notebooks_dir,
        },
        "server": {
            "port": daglab_port,
            "dagster_port": dagster_port,
            "auto_reload": True,
        },
        "notebooks": {
            "default_kernel": "python3",
            "extensions": ["ipynb"],
            "auto_save": True,
        }
    }
    
    if template == "ml":
        config["ml"] = {
            "frameworks": ["pandas", "scikit-learn", "matplotlib"],
            "data_dir": "data/",
            "models_dir": "models/",
        }
    
    return config


def create_project_structure(
    project_path: Path,
    notebooks_dir: str,
    create_examples: bool,
    template: str,
    force: bool
) -> None:
    """Create project directory structure."""
    # Create .daglab directory
    daglab_dir = project_path / ".daglab"
    daglab_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (daglab_dir / "cache").mkdir(exist_ok=True)
    (daglab_dir / "logs").mkdir(exist_ok=True)
    (daglab_dir / "tmp").mkdir(exist_ok=True)
    
    # Create notebooks directory
    notebooks_path = project_path / notebooks_dir
    notebooks_path.mkdir(parents=True, exist_ok=True)
    
    # Create example notebooks
    if create_examples:
        examples_dir = Path(__file__).parent.parent / "templates" / template / "notebooks"
        if examples_dir.exists():
            for example in examples_dir.glob("*.ipynb"):
                dest = notebooks_path / example.name
                if not dest.exists() or force:
                    shutil.copy2(example, dest)


def create_bootstrap_project(
    project_path: Path,
    template: str,
    force: bool
) -> None:
    """Create a new Dagster project from scratch."""
    template_dir = Path(__file__).parent.parent / "templates" / template
    
    if not template_dir.exists():
        console.print(f"[red]Template '{template}' not found[/red]")
        return
    
    # Create project structure
    dirs_to_create = [
        project_path / "dagster",
        project_path / "dagster" / "assets",
        project_path / "dagster" / "jobs",
        project_path / "dagster" / "ops",
        project_path / "dagster" / "resources",
        project_path / "dagster" / "schedules",
        project_path / "dagster" / "sensors",
        project_path / "tests",
        project_path / "data",
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Copy template files
    template_files = {
        "dagster.yaml": project_path / "dagster.yaml",
        "workspace.yaml": project_path / "workspace.yaml",
        "pyproject.toml": project_path / "pyproject.toml",
        "repository.py": project_path / "dagster" / "repository.py",
        "__init__.py": project_path / "dagster" / "__init__.py",
    }
    
    for src_name, dest_path in template_files.items():
        src_file = template_dir / src_name
        if src_file.exists() and (not dest_path.exists() or force):
            shutil.copy2(src_file, dest_path)
    
    # Create example assets
    if template == "ml":
        assets_file = template_dir / "assets" / "ml_assets.py"
        if assets_file.exists():
            shutil.copy2(assets_file, project_path / "dagster" / "assets" / "ml_assets.py")
    else:
        # Copy standard assets
        assets_dir = template_dir / "assets"
        if assets_dir.exists():
            for asset_file in assets_dir.glob("*.py"):
                shutil.copy2(asset_file, project_path / "dagster" / "assets" / asset_file.name)


def update_gitignore(project_path: Path) -> None:
    """Update .gitignore with daglab entries."""
    gitignore_path = project_path / ".gitignore"
    
    daglab_entries = """
# Daglab
.daglab/
*.daglab.log
.ipynb_checkpoints/
__pycache__/
*.pyc

# Dagster
.dagster/
dagster.db
dagster.db-journal
"""
    
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".daglab/" not in content:
            with open(gitignore_path, "a") as f:
                f.write(daglab_entries)
    else:
        gitignore_path.write_text(daglab_entries.lstrip())


@click.command()
@click.option(
    "--notebooks-dir",
    default="dagster/notebooks",
    help="Directory for Jupyter notebooks"
)
@click.option(
    "--dagster-port",
    type=int,
    default=3000,
    help="Port for Dagster UI"
)
@click.option(
    "--daglab-port",
    type=int,
    default=8888,
    help="Port for Daglab server"
)
@click.option(
    "--no-examples",
    is_flag=True,
    help="Skip creating example notebooks"
)
@click.option(
    "--template",
    type=click.Choice(["minimal", "standard", "ml"]),
    default="standard",
    help="Project template to use"
)
@click.option(
    "--bootstrap",
    is_flag=True,
    help="Create a new Dagster project from scratch"
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files"
)
@click.argument("path", type=click.Path(), default=".")
def dagster_init_command(
    path: str,
    notebooks_dir: str,
    dagster_port: int,
    daglab_port: int,
    no_examples: bool,
    template: str,
    bootstrap: bool,
    force: bool
) -> None:
    """Initialize daglab in a Dagster project.
    
    This command sets up daglab in your Dagster project, creating necessary
    configuration files and directory structure.
    """
    project_path = Path(path).resolve()
    
    console.print("\n[bold cyan]🚀 Initializing daglab for Dagster...[/bold cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check if it's a Dagster project
        task = progress.add_task("Detecting project type...", total=1)
        is_dagster, detected_type = detect_dagster_project(project_path)
        progress.update(task, completed=1)
        
        if is_dagster and not bootstrap:
            console.print(f"[green]✓[/green] Detected Dagster project ({detected_type})")
        elif bootstrap:
            if is_dagster and not force:
                if not Confirm.ask(
                    "[yellow]Dagster project already exists. Continue with bootstrap?[/yellow]"
                ):
                    console.print("[red]Aborted.[/red]")
                    return
            
            task = progress.add_task("Creating Dagster project...", total=1)
            create_bootstrap_project(project_path, template, force)
            progress.update(task, completed=1)
            console.print(f"[green]✓[/green] Created Dagster project with {template} template")
        else:
            console.print("[yellow]⚠[/yellow]  No Dagster project detected")
            if not bootstrap:
                console.print(
                    "\n[dim]Tip: Use --bootstrap to create a new Dagster project[/dim]"
                )
                return
        
        # Check for port availability
        task = progress.add_task("Checking port availability...", total=1)
        
        if not is_port_available(dagster_port):
            new_port = get_available_port(dagster_port)
            console.print(
                f"[yellow]⚠[/yellow]  Port {dagster_port} is in use, using {new_port} instead"
            )
            dagster_port = new_port
        
        if not is_port_available(daglab_port):
            new_port = get_available_port(daglab_port)
            console.print(
                f"[yellow]⚠[/yellow]  Port {daglab_port} is in use, using {new_port} instead"
            )
            daglab_port = new_port
        
        progress.update(task, completed=1)
        
        # Create configuration
        task = progress.add_task("Creating configuration...", total=1)
        config = create_daglab_config(
            project_path, notebooks_dir, dagster_port, daglab_port, template
        )
        
        config_path = project_path / "daglab.yaml"
        if config_path.exists() and not force:
            if not Confirm.ask(
                "[yellow]daglab.yaml already exists. Overwrite?[/yellow]"
            ):
                console.print("[red]Aborted.[/red]")
                return
        
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        progress.update(task, completed=1)
        console.print(f"[green]✓[/green] Created daglab.yaml")
        
        # Create project structure
        task = progress.add_task("Creating project structure...", total=1)
        create_project_structure(
            project_path,
            notebooks_dir,
            not no_examples,
            template,
            force
        )
        progress.update(task, completed=1)
        console.print(f"[green]✓[/green] Created project structure")
        
        # Update .gitignore
        task = progress.add_task("Updating .gitignore...", total=1)
        update_gitignore(project_path)
        progress.update(task, completed=1)
        console.print(f"[green]✓[/green] Updated .gitignore")
    
    # Display summary
    console.print("\n[bold green]✨ Daglab initialized successfully![/bold green]\n")
    
    # Show configuration summary
    table = Table(title="Configuration Summary")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Project Path", str(project_path))
    table.add_row("Notebooks Directory", notebooks_dir)
    table.add_row("Dagster Port", str(dagster_port))
    table.add_row("Daglab Port", str(daglab_port))
    table.add_row("Template", template)
    
    console.print(table)
    
    # Show next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Install daglab: [cyan]pip install daglab[/cyan]")
    if bootstrap:
        console.print("2. Install dependencies: [cyan]pip install -e .[dev][/cyan]")
        console.print("3. Start Dagster: [cyan]dagster dev[/cyan]")
        console.print("4. Start Daglab: [cyan]daglab start[/cyan]")
    else:
        console.print("2. Start Daglab: [cyan]daglab start[/cyan]")
    console.print("\n[dim]For more information, visit: https://daglab.ai/docs[/dim]")


if __name__ == "__main__":
    dagster_init_command()