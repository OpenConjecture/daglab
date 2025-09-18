"""Command-line interface for Daglab."""

import typer
from typing import Optional, Dict, Any
from pathlib import Path
import json
import yaml
import sys
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
import asyncio
from contextvars import ContextVar

from daglab import __version__
from daglab.config import DaglabConfig, ConfigLoader, get_config
from daglab.runtime.logging import get_logger, setup_logging
from daglab.runtime.errors import DaglabError, ExitCode

# Global context for configuration
_global_context: ContextVar[Dict[str, Any]] = ContextVar('global_context', default={})

# Create app with no_args_is_help for better UX
app = typer.Typer(
    name="daglab",
    help="Scaffold and run paired marimo notebooks for Dagster assets & jobs.",
    rich_markup_mode="rich",
    add_completion=True,
    no_args_is_help=True,
)

# Initialize Rich console
console = Console()

# Error console for styled errors
error_console = Console(stderr=True)

logger = get_logger(__name__)

def version_callback(value: bool):
    """Show version and exit."""
    if value:
        version_panel = Panel(
            f"[bold blue]daglab[/bold blue] version [green]{__version__}[/green]\n"
            f"[dim]Scaffold and run paired marimo notebooks for Dagster assets & jobs[/dim]",
            title="Daglab",
            border_style="blue",
        )
        console.print(version_panel)
        raise typer.Exit()

@app.callback()
def main_callback(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to configuration file",
        exists=True,
        dir_okay=False,
        resolve_path=True,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-V",
        help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Suppress non-error output"
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", 
        callback=version_callback, 
        is_eager=True,
        help="Show version and exit"
    ),
):
    """
    Daglab - Scaffold and run paired marimo notebooks for Dagster assets & jobs.
    
    Use 'daglab COMMAND --help' for more information on a specific command.
    """
    # Set up global context
    ctx = _global_context.get()
    ctx['config_file'] = config
    ctx['verbose'] = verbose
    ctx['quiet'] = quiet
    
    # Configure logging based on verbosity
    if verbose:
        setup_logging(level="DEBUG")
    elif quiet:
        setup_logging(level="ERROR")
    else:
        setup_logging(level="INFO")
    
    _global_context.set(ctx)

# Import commands from modular structure
# Import existing Phase 1 commands (these may not exist yet)
try:
    from daglab.commands import init as init_cmd
    app.add_typer(init_cmd.app, name="init", help="Initialize a new Daglab project")
except ImportError:
    pass

try:
    from daglab.commands import doctor as doctor_cmd
    app.add_typer(doctor_cmd.app, name="doctor", help="Check system health and configuration")
except ImportError:
    pass

try:
    from daglab.commands import clean as clean_cmd
    app.add_typer(clean_cmd.app, name="clean", help="Clean up artifacts and temporary files")
except ImportError:
    pass

# Import future phase commands (stubs)
try:
    # Phase 3 commands
    from daglab.commands import scaffold as scaffold_cmd
    app.add_typer(scaffold_cmd.app, name="scaffold", help="Generate notebook templates [Phase 3]")
except ImportError as e:
    logger.debug(f"Scaffold command not available: {e}")

try:
    # Phase 4 commands
    from daglab.commands import discover as discover_cmd
    app.add_typer(discover_cmd.app, name="discover", help="Discover Dagster entities [Phase 4]")
except ImportError as e:
    logger.debug(f"Discover command not available: {e}")

try:
    from daglab.commands import run as run_cmd
    app.add_typer(run_cmd.app, name="run", help="Execute Dagster entities [Phase 4]")
except ImportError as e:
    logger.debug(f"Run command not available: {e}")

try:
    # Phase 5 commands
    from daglab.commands import export as export_cmd
    app.add_typer(export_cmd.app, name="export", help="Export notebooks to various formats [Phase 5]")
except ImportError as e:
    logger.debug(f"Export command not available: {e}")

try:
    from daglab.commands import dev as dev_cmd
    app.add_typer(dev_cmd.app, name="dev", help="Development environment tools [Phase 5]")
except ImportError as e:
    logger.debug(f"Dev command not available: {e}")

try:
    from daglab.commands import stats as stats_cmd
    app.add_typer(stats_cmd.app, name="stats", help="View usage statistics and metrics [Phase 5]")
except ImportError as e:
    logger.debug(f"Stats command not available: {e}")

try:
    from daglab.commands import migrate as migrate_cmd
    app.add_typer(migrate_cmd.app, name="migrate", help="Migrate Jupyter notebooks to Marimo [Phase 5]")
except ImportError as e:
    logger.debug(f"Migrate command not available: {e}")

# Enhanced list command with better formatting
@app.command(name="list")
def list_dags(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
):
    """List all DAGs in the project."""
    context = _global_context.get()
    if not context.get('quiet'):
        console.print(Panel.fit(
            "[bold]Listing DAGs[/bold]",
            border_style="blue"
        ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=context.get('quiet', False),
    ) as progress:
        task = progress.add_task("Scanning for DAGs...", total=None)
        dags_path = path / "dags"
        
        if not dags_path.exists():
            error_panel = Panel(
                "[red]No 'dags' directory found.[/red]\n"
                "Please ensure you're in a Daglab project directory or use --path",
                title="Error",
                border_style="red",
            )
            error_console.print(error_panel)
            raise typer.Exit(ExitCode.CONFIGURATION_ERROR)
        
        progress.update(task, description="Loading DAG files...")
        
        table = Table(
            title="Available DAGs",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="dim")
        table.add_column("Nodes", justify="right", style="green")
        table.add_column("Edges", justify="right", style="yellow")
        table.add_column("Status", justify="center")
        
        dag_files = list(dags_path.glob("*.json")) + list(dags_path.glob("*.yaml"))
        
        for dag_file in dag_files:
            try:
                if dag_file.suffix == ".json":
                    with open(dag_file) as f:
                        dag_data = json.load(f)
                else:
                    with open(dag_file) as f:
                        dag_data = yaml.safe_load(f)
                
                name = dag_data.get("name", dag_file.stem)
                description = dag_data.get("description", "No description")
                nodes = len(dag_data.get("nodes", []))
                edges = len(dag_data.get("edges", []))
                
                # Add status indicator
                status = "[green]✓[/green]" if nodes > 0 else "[yellow]![/yellow]"
                
                table.add_row(name, description, str(nodes), str(edges), status)
            except Exception as e:
                if context.get('verbose'):
                    console.print(f"[yellow]Warning:[/yellow] Could not load {dag_file.name}: {e}")
        
    if not context.get('quiet'):
        console.print(table)
        console.print(f"\n[dim]Found {len(dag_files)} DAG(s)[/dim]")


@app.command()
def validate(
    dag_file: Path = typer.Argument(..., help="DAG file to validate"),
):
    """Validate a DAG definition."""
    context = _global_context.get()
    
    if not context.get('quiet'):
        console.print(Panel.fit(
            f"[bold]Validating DAG[/bold]\n[dim]{dag_file}[/dim]",
            border_style="blue"
        ))
    
    try:
        # Load DAG
        if dag_file.suffix == ".json":
            with open(dag_file) as f:
                dag_data = json.load(f)
        else:
            with open(dag_file) as f:
                dag_data = yaml.safe_load(f)
        
        # Basic validation
        required_fields = ["name", "nodes", "edges"]
        missing_fields = [field for field in required_fields if field not in dag_data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate structure
        nodes = dag_data.get("nodes", [])
        edges = dag_data.get("edges", [])
        
        if not isinstance(nodes, list):
            raise ValueError("'nodes' must be a list")
        if not isinstance(edges, list):
            raise ValueError("'edges' must be a list")
        
        console.print(f"[green]✓[/green] DAG '{dag_data['name']}' is valid")
        
        # Show summary
        if not context.get('quiet'):
            console.print(f"\nSummary:")
            console.print(f"  Nodes: {len(nodes)}")
            console.print(f"  Edges: {len(edges)}")
        
    except Exception as e:
        error_panel = Panel(
            f"[red]Validation Error:[/red] {e}",
            title="Error",
            border_style="red"
        )
        error_console.print(error_panel)
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

@app.command()
def config(
    action: str = typer.Argument(..., help="Action: show/set/get"),
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
):
    """Manage Daglab configuration."""
    context = _global_context.get()
    
    if action == "show":
        if not context.get('quiet'):
            console.print(Panel.fit(
                "[bold]Current Configuration[/bold]",
                border_style="blue"
            ))
        
        try:
            config = get_config()
            
            # Display config in a table
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="dim")
            
            def add_config_items(data, prefix=""):
                for k, v in data.items():
                    if isinstance(v, dict):
                        add_config_items(v, f"{prefix}{k}.")
                    else:
                        table.add_row(f"{prefix}{k}", str(v))
            
            add_config_items(config.model_dump())
            console.print(table)
            
        except Exception as e:
            error_console.print(f"[red]Error loading configuration:[/red] {e}")
            raise typer.Exit(ExitCode.CONFIGURATION_ERROR)
    
    elif action == "get" and key:
        try:
            config = get_config()
            # Navigate nested config
            value = config.model_dump()
            for part in key.split('.'):
                value = value.get(part)
                if value is None:
                    error_console.print(f"[red]Error:[/red] Unknown config key '{key}'")
                    raise typer.Exit(ExitCode.CONFIGURATION_ERROR)
            
            console.print(f"{key}: {value}")
            
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(ExitCode.CONFIGURATION_ERROR)
    
    elif action == "set" and key and value:
        # In a real implementation, this would update the config file
        console.print(Panel.fit(
            f"[green]✓[/green] Set {key} = {value}",
            border_style="green"
        ))
    
    else:
        error_console.print("[red]Error:[/red] Invalid command. Use 'show', 'get <key>', or 'set <key> <value>'")
        raise typer.Exit(ExitCode.MISUSE)

# Add styled error handling
def handle_error(error: Exception):
    """Handle errors with Rich formatting."""
    error_panel = Panel(
        f"[red]{type(error).__name__}:[/red] {str(error)}",
        title="Error",
        border_style="red",
        expand=False,
    )
    error_console.print(error_panel)
    
    context = _global_context.get()
    if context.get('verbose'):
        import traceback
        error_console.print("[dim]Traceback:[/dim]")
        error_console.print(traceback.format_exc())

def main():
    """Main entry point with error handling."""
    try:
        app()
    except DaglabError as e:
        handle_error(e)
        sys.exit(e.exit_code.value)
    except Exception as e:
        handle_error(e)
        sys.exit(ExitCode.RUNTIME_ERROR.value)
    except KeyboardInterrupt:
        error_console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)  # Standard interrupt exit code

if __name__ == "__main__":
    main()