"""Doctor command for system health checks."""

import typer
import sys
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from daglab import __version__
from daglab.runtime.logging import get_logger
from daglab.config import get_config, ConfigLoader

app = typer.Typer()
console = Console()
logger = get_logger(__name__)


class HealthCheck:
    """System health check utilities."""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
        
    def check_python_version(self) -> Tuple[bool, str]:
        """Check Python version compatibility."""
        py_version = sys.version_info
        min_version = (3, 8)
        
        if py_version >= min_version:
            return True, f"Python {py_version.major}.{py_version.minor}.{py_version.micro}"
        else:
            return False, f"Python {py_version.major}.{py_version.minor} (requires >= 3.8)"
    
    def check_daglab_installation(self) -> Tuple[bool, str]:
        """Check if Daglab is properly installed."""
        try:
            import daglab
            return True, f"Version {__version__}"
        except ImportError:
            return False, "Not installed"
    
    def check_required_packages(self) -> Dict[str, Tuple[bool, str]]:
        """Check required package installations."""
        packages = {
            "typer": "CLI framework",
            "rich": "Terminal formatting",
            "pydantic": "Data validation",
            "yaml": "YAML parsing",
            "marimo": "Notebook runtime",
            "dagster": "Orchestration engine",
        }
        
        results = {}
        for package, description in packages.items():
            try:
                if package == "yaml":
                    import yaml
                else:
                    __import__(package)
                results[package] = (True, "Installed")
            except ImportError:
                results[package] = (False, "Not installed")
        
        return results
    
    def check_system_commands(self) -> Dict[str, Tuple[bool, str]]:
        """Check system command availability."""
        commands = {
            "git": "Version control",
            "python": "Python interpreter",
            "pip": "Package installer",
        }
        
        results = {}
        for cmd, description in commands.items():
            path = shutil.which(cmd)
            if path:
                results[cmd] = (True, f"Found at {path}")
            else:
                results[cmd] = (False, "Not found")
        
        return results
    
    def check_project_structure(self, path: Path) -> Dict[str, Tuple[bool, str]]:
        """Check project directory structure."""
        expected_dirs = {
            "dags": "DAG definitions",
            "config": "Configuration files",
            "notebooks": "Marimo notebooks",
            "data": "Data directory",
            "logs": "Log files",
            "artifacts": "Output artifacts",
        }
        
        results = {}
        for dir_name, description in expected_dirs.items():
            dir_path = path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                results[dir_name] = (True, "Exists")
            else:
                results[dir_name] = (False, "Missing")
        
        return results
    
    def check_configuration(self, path: Path) -> Tuple[bool, str]:
        """Check configuration file."""
        config_path = path / "config" / "daglab.yaml"
        
        if not config_path.exists():
            return False, "Config file not found"
        
        try:
            config = ConfigLoader.load_from_file(config_path)
            return True, "Valid configuration"
        except Exception as e:
            return False, f"Invalid: {str(e)}"
    
    def check_permissions(self, path: Path) -> Dict[str, Tuple[bool, str]]:
        """Check file system permissions."""
        dirs_to_check = ["logs", "artifacts", "data"]
        results = {}
        
        for dir_name in dirs_to_check:
            dir_path = path / dir_name
            if dir_path.exists():
                # Check write permission
                test_file = dir_path / ".daglab_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    results[dir_name] = (True, "Writable")
                except Exception:
                    results[dir_name] = (False, "Not writable")
            else:
                results[dir_name] = (None, "Directory doesn't exist")
        
        return results


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Run system health checks."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(run_checks)


@app.command(name="check")
def run_checks(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Run comprehensive system health checks."""
    console.print(Panel.fit(
        "[bold]Daglab Doctor[/bold]\n"
        "[dim]Running system health checks...[/dim]",
        border_style="blue"
    ))
    
    health = HealthCheck()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running checks...", total=6)
        
        # System checks
        results = {
            "System Information": {},
            "Python Environment": {},
            "Required Packages": {},
            "System Commands": {},
            "Project Structure": {},
            "Configuration": {},
        }
        
        # System info
        progress.update(task, description="Checking system information...")
        results["System Information"] = {
            "OS": (True, f"{platform.system()} {platform.release()}"),
            "Architecture": (True, platform.machine()),
            "Python": health.check_python_version(),
            "Daglab": health.check_daglab_installation(),
        }
        progress.update(task, advance=1)
        
        # Python environment
        progress.update(task, description="Checking Python environment...")
        results["Python Environment"] = {
            "Virtual env": (True, "Active" if hasattr(sys, 'real_prefix') or 
                          (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) 
                          else "Not active"),
            "Site packages": (True, f"{len([p for p in sys.path if 'site-packages' in p])} paths"),
        }
        progress.update(task, advance=1)
        
        # Required packages
        progress.update(task, description="Checking required packages...")
        results["Required Packages"] = health.check_required_packages()
        progress.update(task, advance=1)
        
        # System commands
        progress.update(task, description="Checking system commands...")
        results["System Commands"] = health.check_system_commands()
        progress.update(task, advance=1)
        
        # Project structure
        progress.update(task, description="Checking project structure...")
        results["Project Structure"] = health.check_project_structure(path)
        progress.update(task, advance=1)
        
        # Configuration
        progress.update(task, description="Checking configuration...")
        config_status = health.check_configuration(path)
        results["Configuration"]["daglab.yaml"] = config_status
        progress.update(task, advance=1)
    
    # Display results
    console.print("\n[bold]Health Check Results[/bold]\n")
    
    total_passed = 0
    total_failed = 0
    
    for category, checks in results.items():
        table = Table(title=category, show_header=True, header_style="bold blue")
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        for check_name, (passed, details) in checks.items():
            if passed is True:
                status = "[green]✓[/green]"
                total_passed += 1
            elif passed is False:
                status = "[red]✗[/red]"
                total_failed += 1
            else:
                status = "[yellow]-[/yellow]"
            
            table.add_row(check_name, status, details)
        
        console.print(table)
        console.print("")
    
    # Summary
    if total_failed == 0:
        summary = Panel(
            f"[green]All checks passed![/green] ({total_passed} checks)\n"
            "[dim]Your Daglab installation is healthy.[/dim]",
            title="Summary",
            border_style="green"
        )
    else:
        summary = Panel(
            f"[yellow]Some checks failed[/yellow]\n"
            f"Passed: [green]{total_passed}[/green] | Failed: [red]{total_failed}[/red]\n\n"
            "[dim]Run 'daglab doctor fix' to attempt automatic fixes[/dim]",
            title="Summary",
            border_style="yellow"
        )
    
    console.print(summary)


@app.command(name="fix")
def fix_issues(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fixed"),
):
    """Attempt to fix common issues automatically."""
    console.print(Panel.fit(
        "[bold]Daglab Doctor - Fix Mode[/bold]\n"
        f"[dim]{'DRY RUN - No changes will be made' if dry_run else 'Attempting automatic fixes...'}[/dim]",
        border_style="yellow" if dry_run else "blue"
    ))
    
    fixes_applied = []
    
    # Check and create missing directories
    expected_dirs = ["dags", "config", "notebooks", "data", "logs", "artifacts"]
    for dir_name in expected_dirs:
        dir_path = path / dir_name
        if not dir_path.exists():
            if not dry_run:
                dir_path.mkdir(parents=True, exist_ok=True)
                (dir_path / ".gitkeep").touch()
            fixes_applied.append(f"Created missing directory: {dir_name}/")
    
    # Check and create config file
    config_path = path / "config" / "daglab.yaml"
    if not config_path.exists():
        if not dry_run:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create minimal config
            import yaml
            config_data = {
                "project": {"name": path.name, "version": "0.1.0"},
                "runtime": {"executor": "local"},
                "logging": {"level": "INFO"},
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
        fixes_applied.append("Created missing configuration file")
    
    # Display results
    if fixes_applied:
        console.print("\n[bold]Fixes Applied:[/bold]" if not dry_run else "\n[bold]Fixes to Apply:[/bold]")
        for fix in fixes_applied:
            console.print(f"  • {fix}")
    else:
        console.print("\n[green]No fixes needed![/green]")
    
    if dry_run and fixes_applied:
        console.print("\n[dim]Run without --dry-run to apply these fixes[/dim]")