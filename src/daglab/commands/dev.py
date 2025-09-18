"""Dev command for development environment - Phase 5."""

import os
import sys
import time
import signal
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from dotenv import load_dotenv

from ..helpers.process import ProcessManager, ProcessState
from ..helpers.ports import PortManager
from ..helpers.browser import BrowserManager

console = Console()
app = typer.Typer(help="Development environment tools [Phase 5]")


class DevEnvironment:
    """Manage the integrated development environment."""
    
    def __init__(
        self,
        dagster_port: int = 3000,
        marimo_port: int = 2718,
        auto_reload: bool = True,
        open_browser: bool = True,
        env_file: Optional[str] = None,
        sandbox_mode: bool = False,
        ci_mode: bool = False
    ):
        self.dagster_port = dagster_port
        self.marimo_port = marimo_port
        self.auto_reload = auto_reload
        self.open_browser = open_browser
        self.env_file = env_file
        self.sandbox_mode = sandbox_mode
        self.ci_mode = ci_mode or os.environ.get("CI") == "true"
        
        # Initialize managers
        self.process_manager = ProcessManager(log_dir=Path.cwd() / ".daglab" / "logs")
        self.port_manager = PortManager()
        self.browser_manager = BrowserManager()
        
        # Track state
        self.start_time = None
        self.is_running = False
        self.urls: Dict[str, str] = {}
        
    def load_environment(self):
        """Load environment variables."""
        if self.env_file and Path(self.env_file).exists():
            load_dotenv(self.env_file)
            console.print(f"[green]✓[/green] Loaded environment from {self.env_file}")
        elif Path(".env").exists():
            load_dotenv()
            console.print("[green]✓[/green] Loaded .env file")
            
    def check_dependencies(self) -> List[str]:
        """Check for required dependencies."""
        missing = []
        
        # Check for dagster
        try:
            import dagster
        except ImportError:
            missing.append("dagster")
            
        # Check for marimo
        try:
            import marimo
        except ImportError:
            missing.append("marimo")
            
        # Check for psutil (for process monitoring)
        try:
            import psutil
        except ImportError:
            missing.append("psutil")
            
        return missing
        
    def allocate_ports(self) -> bool:
        """Allocate ports for services."""
        try:
            # Allocate Dagster port
            actual_dagster_port = self.port_manager.allocate_port(
                "dagster",
                preferred=self.dagster_port,
                range_name="dagster"
            )
            
            if actual_dagster_port != self.dagster_port:
                console.print(
                    f"[yellow]Port {self.dagster_port} unavailable, "
                    f"using {actual_dagster_port} for Dagster[/yellow]"
                )
            self.dagster_port = actual_dagster_port
            
            # Allocate Marimo port
            actual_marimo_port = self.port_manager.allocate_port(
                "marimo",
                preferred=self.marimo_port,
                range_name="marimo"
            )
            
            if actual_marimo_port != self.marimo_port:
                console.print(
                    f"[yellow]Port {self.marimo_port} unavailable, "
                    f"using {actual_marimo_port} for Marimo[/yellow]"
                )
            self.marimo_port = actual_marimo_port
            
            # Store URLs
            self.urls["dagster"] = f"http://localhost:{self.dagster_port}"
            self.urls["marimo"] = f"http://localhost:{self.marimo_port}"
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to allocate ports: {e}[/red]")
            return False
            
    def setup_processes(self):
        """Set up process configurations."""
        # Dagster configuration
        dagster_cmd = [
            sys.executable, "-m", "dagster", "dev",
            "-p", str(self.dagster_port)
        ]
        
        if self.auto_reload:
            dagster_cmd.append("--reload")
            
        if self.sandbox_mode:
            dagster_cmd.extend(["--graphql-sandbox"])
            
        # Register Dagster process
        self.process_manager.register(
            "dagster",
            dagster_cmd,
            health_check_fn=lambda: self._check_http_health(
                f"http://localhost:{self.dagster_port}/graphql",
                "dagster"
            )
        )
        
        # Marimo configuration
        marimo_cmd = [
            sys.executable, "-m", "marimo", "edit",
            "--port", str(self.marimo_port),
            "--no-open"  # We'll handle opening ourselves
        ]
        
        if self.ci_mode:
            marimo_cmd.append("--headless")
            
        # Register Marimo process
        self.process_manager.register(
            "marimo",
            marimo_cmd,
            health_check_fn=lambda: self._check_http_health(
                f"http://localhost:{self.marimo_port}",
                "marimo"
            )
        )
        
    def _check_http_health(self, url: str, service: str) -> bool:
        """Check if HTTP service is responding."""
        try:
            import requests
            response = requests.get(url, timeout=2)
            return response.status_code < 500
        except Exception:
            return False
            
    def start(self):
        """Start the development environment."""
        self.start_time = datetime.now()
        self.is_running = True
        
        # Start processes
        console.print("\n[bold cyan]Starting Development Environment[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Start Dagster
            task = progress.add_task("Starting Dagster UI...", total=None)
            if self.process_manager.start("dagster"):
                progress.update(task, completed=True, description="[green]✓[/green] Dagster UI started")
            else:
                progress.update(task, completed=True, description="[red]✗[/red] Failed to start Dagster")
                return False
                
            # Start Marimo
            task = progress.add_task("Starting Marimo editor...", total=None)
            if self.process_manager.start("marimo"):
                progress.update(task, completed=True, description="[green]✓[/green] Marimo editor started")
            else:
                progress.update(task, completed=True, description="[red]✗[/red] Failed to start Marimo")
                return False
                
        # Wait for services to be ready
        console.print("\n[cyan]Waiting for services to be ready...[/cyan]")
        
        dagster_ready = self.process_manager.wait_for_ready("dagster", timeout=30)
        marimo_ready = self.process_manager.wait_for_ready("marimo", timeout=30)
        
        if not dagster_ready or not marimo_ready:
            console.print("[red]Services failed to start properly[/red]")
            return False
            
        # Open browsers if requested
        if self.open_browser and not self.ci_mode:
            time.sleep(2)  # Brief pause to ensure services are fully ready
            
            console.print("\n[cyan]Opening browsers...[/cyan]")
            self.browser_manager.open_multiple([
                self.urls["dagster"],
                self.urls["marimo"]
            ], delay=1)
            
        return True
        
    def display_status(self):
        """Display current environment status."""
        # Create status table
        table = Table(title="Development Environment", box=None)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("URL", style="blue")
        table.add_column("PID")
        table.add_column("CPU %")
        table.add_column("Memory")
        
        # Get process status
        status = self.process_manager.get_status()
        
        for service, info in status.items():
            state_style = "green" if info["state"] == "running" else "yellow"
            state_icon = "●" if info["state"] == "running" else "○"
            
            table.add_row(
                service.capitalize(),
                f"[{state_style}]{state_icon} {info['state']}[/{state_style}]",
                self.urls.get(service, "-"),
                str(info.get("pid", "-")),
                f"{info.get('cpu_percent', 0)}%",
                f"{info.get('memory_mb', 0):.1f} MB"
            )
            
        console.print(table)
        
        # Show uptime
        if self.start_time:
            uptime = datetime.now() - self.start_time
            console.print(f"\n[dim]Uptime: {str(uptime).split('.')[0]}[/dim]")
            
    def run_interactive(self):
        """Run in interactive mode with live monitoring."""
        if not self.start():
            console.print("[red]Failed to start environment[/red]")
            return
            
        console.print("\n[bold green]Development Environment Running![/bold green]")
        self.display_status()
        
        console.print("\n[yellow]Press Ctrl+C to stop[/yellow]")
        
        try:
            # Keep running and periodically update status
            while self.is_running:
                time.sleep(5)
                # Could add live status updates here
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            self.stop()
            
    def stop(self):
        """Stop the development environment."""
        self.is_running = False
        
        console.print("\n[cyan]Stopping services...[/cyan]")
        
        # Stop processes
        self.process_manager.shutdown_all()
        
        # Release ports
        self.port_manager.release_all()
        
        console.print("[green]✓[/green] Development environment stopped")


@app.callback(invoke_without_command=True)
def dev(
    ctx: typer.Context,
    dagster_port: int = typer.Option(
        3000,
        "--dagster-port",
        "-d",
        help="Port for Dagster UI"
    ),
    marimo_port: int = typer.Option(
        2718,
        "--marimo-port",
        "-m",
        help="Port for Marimo editor"
    ),
    auto_reload: bool = typer.Option(
        True,
        "--auto-reload/--no-auto-reload",
        help="Enable auto-reload on file changes"
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open browser automatically"
    ),
    env: Optional[str] = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment file to load"
    ),
    sandbox: bool = typer.Option(
        False,
        "--sandbox",
        help="Enable GraphQL sandbox mode"
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help="Run in CI mode (headless)"
    ),
) -> None:
    """Start integrated development environment.
    
    Launch a complete development environment with Dagster UI,
    Marimo editor, and development tools all configured and ready.
    
    Examples:
        daglab dev
        daglab dev --dagster-port 4000 --marimo-port 3000
        daglab dev --no-auto-reload --env staging.env
        daglab dev --no-open --ci
    """
    if ctx.invoked_subcommand is None:
        # Create and configure environment
        env = DevEnvironment(
            dagster_port=dagster_port,
            marimo_port=marimo_port,
            auto_reload=auto_reload,
            open_browser=open_browser,
            env_file=env,
            sandbox_mode=sandbox,
            ci_mode=ci
        )
        
        # Check dependencies
        missing_deps = env.check_dependencies()
        if missing_deps:
            console.print(
                f"[red]Missing required dependencies: {', '.join(missing_deps)}[/red]\n"
                f"Install with: pip install {' '.join(missing_deps)}"
            )
            raise typer.Exit(1)
            
        # Load environment
        env.load_environment()
        
        # Allocate ports
        if not env.allocate_ports():
            raise typer.Exit(1)
            
        # Setup processes
        env.setup_processes()
        
        # Run
        if ci:
            # In CI mode, just start and report status
            if env.start():
                env.display_status()
                console.print("\n[green]Environment started successfully[/green]")
                
                # Print URLs for CI logs
                console.print(f"\nDagster UI: {env.urls['dagster']}")
                console.print(f"Marimo Editor: {env.urls['marimo']}")
            else:
                raise typer.Exit(1)
        else:
            # Interactive mode
            env.run_interactive()


@app.command()
def status(
    json: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Show status of development environment."""
    # This would connect to running environment if implemented
    console.print(
        Panel(
            "[yellow]Status command will be implemented to show running environment status[/yellow]",
            title="Dev Status",
            border_style="yellow"
        )
    )


@app.command()
def logs(
    service: str = typer.Argument(..., help="Service name (dagster|marimo)"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
) -> None:
    """View logs from development services."""
    console.print(
        Panel(
            f"[yellow]Logs command will show logs for {service}[/yellow]",
            title="Dev Logs",
            border_style="yellow"
        )
    )


if __name__ == "__main__":
    app()