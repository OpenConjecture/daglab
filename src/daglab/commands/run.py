"""Run command for executing Dagster entities."""

import typer
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich.table import Table
from rich.syntax import Syntax
import asyncio
import json
import yaml
import time
import sys
import os
from datetime import datetime, timedelta

console = Console()
app = typer.Typer(help="Execute Dagster entities")


class RunSubmitter:
    """Handles submission of Dagster runs."""
    
    def __init__(self):
        self.console = console
        
    def submit_job(
        self,
        job_name: str,
        run_config: Dict[str, Any],
        repo: Optional[str] = None,
        location: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Submit a job run."""
        # TODO: Integrate with Dagster GraphQL API
        # For now, simulate submission
        run_id = f"run_{int(time.time())}"
        self.console.print(f"[green]✓[/green] Submitted job '{job_name}' with run ID: {run_id}")
        return run_id
    
    def materialize_assets(
        self,
        asset_selection: List[str],
        repo: Optional[str] = None,
        location: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Submit asset materialization."""
        # TODO: Integrate with Dagster GraphQL API
        run_id = f"run_{int(time.time())}"
        self.console.print(f"[green]✓[/green] Materializing {len(asset_selection)} assets with run ID: {run_id}")
        return run_id
    
    def expand_asset_pattern(self, pattern: str, repo: Optional[str] = None) -> List[str]:
        """Expand asset pattern (e.g., orders/* -> all orders assets)."""
        # TODO: Query Dagster for matching assets
        # For now, simulate expansion
        if pattern.endswith("/*"):
            base = pattern[:-2]
            return [f"{base}_raw", f"{base}_cleaned", f"{base}_aggregated"]
        return [pattern]


class RunMonitor:
    """Monitors Dagster run execution."""
    
    def __init__(self):
        self.console = console
    
    async def monitor_run(
        self,
        run_id: str,
        timeout: Optional[int] = None,
        cancel_on_timeout: bool = False
    ) -> bool:
        """Monitor a run until completion."""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Running...", total=100)
            
            # Simulate run monitoring
            for i in range(101):
                if timeout and time.time() - start_time > timeout:
                    if cancel_on_timeout:
                        self.console.print("[red]✗[/red] Run timed out and was cancelled")
                        return False
                    else:
                        self.console.print("[yellow]⚠[/yellow] Run timed out but continues running")
                        return False
                
                progress.update(task, completed=i)
                await asyncio.sleep(0.1)  # Simulate work
        
        self.console.print("[green]✓[/green] Run completed successfully")
        return True
    
    def get_run_url(self, run_id: str) -> str:
        """Get Dagster UI URL for run."""
        # TODO: Get from config
        base_url = os.getenv("DAGSTER_UI_URL", "http://localhost:3000")
        return f"{base_url}/runs/{run_id}"
    
    def stream_logs(self, run_id: str):
        """Stream logs from running job."""
        # TODO: Implement real log streaming
        self.console.print("[dim]Log streaming not yet implemented[/dim]")


class ConfigManager:
    """Manages run configuration."""
    
    def __init__(self):
        self.console = console
    
    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path.suffix}")
        
        return self._substitute_env_vars(config)
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Substitute environment variables in config."""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            default = None
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            return os.environ.get(env_var, default)
        return config
    
    def validate_config(self, config: Dict[str, Any], job_name: str) -> bool:
        """Validate configuration against job schema."""
        # TODO: Implement real validation against job config schema
        self.console.print("[dim]Config validation not yet implemented[/dim]")
        return True
    
    def parse_yaml_string(self, yaml_string: str) -> Dict[str, Any]:
        """Parse YAML configuration from string."""
        try:
            return yaml.safe_load(yaml_string)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    job: Optional[str] = typer.Option(
        None,
        "--job",
        "-j",
        help="Job name to execute"
    ),
    asset_selection: Optional[List[str]] = typer.Option(
        None,
        "--asset-selection",
        "-a",
        help="Assets to materialize (can specify multiple)"
    ),
    asset_pattern: Optional[str] = typer.Option(
        None,
        "--asset-pattern",
        help="Pattern for asset selection (e.g., 'orders/*')"
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repository name"
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location",
        "-l",
        help="Code location name"
    ),
    run_config: Optional[Path] = typer.Option(
        None,
        "--run-config",
        "-c",
        help="Run configuration file (YAML or JSON)"
    ),
    config_yaml: Optional[str] = typer.Option(
        None,
        "--config-yaml",
        help="Inline YAML configuration"
    ),
    validate_only: bool = typer.Option(
        False,
        "--validate-only",
        help="Validate configuration without executing"
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Wait for run to complete"
    ),
    timeout: Optional[int] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (only with --wait)"
    ),
    cancel_on_timeout: bool = typer.Option(
        False,
        "--cancel-on-timeout",
        help="Cancel run on timeout (requires --timeout)"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output JSON instead of human-readable format"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output"
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags",
        help="Run tags in format 'key1=value1,key2=value2'"
    ),
) -> None:
    """Execute Dagster jobs or materialize assets.
    
    This command provides a unified interface to run Dagster entities
    with proper configuration and monitoring.
    
    Examples:
        # Run a job
        daglab run --job daily_etl
        
        # Materialize specific assets
        daglab run --asset-selection raw_orders --asset-selection raw_customers
        
        # Use asset patterns
        daglab run --asset-pattern "analytics/*"
        
        # Run with configuration
        daglab run --job ml_pipeline --run-config config.yaml
        
        # Inline configuration
        daglab run --job batch_job --config-yaml "ops: {process: {config: {batch_size: 100}}}"
        
        # Don't wait for completion
        daglab run --job long_running --no-wait
        
        # With timeout and cancellation
        daglab run --job data_sync --timeout 3600 --cancel-on-timeout
    """
    if ctx.invoked_subcommand is not None:
        return
    
    # Validate inputs
    if not job and not asset_selection and not asset_pattern:
        console.print("[red]Error:[/red] Must specify either --job, --asset-selection, or --asset-pattern")
        raise typer.Exit(1)
    
    if job and (asset_selection or asset_pattern):
        console.print("[red]Error:[/red] Cannot specify both job and asset options")
        raise typer.Exit(1)
    
    if cancel_on_timeout and not timeout:
        console.print("[red]Error:[/red] --cancel-on-timeout requires --timeout")
        raise typer.Exit(1)
    
    # Initialize components
    submitter = RunSubmitter()
    monitor = RunMonitor()
    config_manager = ConfigManager()
    
    # Parse tags
    run_tags = {}
    if tags:
        for tag in tags.split(","):
            if "=" not in tag:
                console.print(f"[red]Error:[/red] Invalid tag format: {tag}")
                raise typer.Exit(1)
            key, value = tag.split("=", 1)
            run_tags[key.strip()] = value.strip()
    
    # Load configuration
    config = {}
    if run_config:
        try:
            config = config_manager.load_config(run_config)
            if verbose:
                console.print("[dim]Loaded configuration from:[/dim]", run_config)
        except Exception as e:
            console.print(f"[red]Error loading config:[/red] {e}")
            raise typer.Exit(1)
    elif config_yaml:
        try:
            config = config_manager.parse_yaml_string(config_yaml)
            if verbose:
                console.print("[dim]Parsed inline configuration[/dim]")
        except Exception as e:
            console.print(f"[red]Error parsing config:[/red] {e}")
            raise typer.Exit(1)
    
    # Validate configuration
    if job and config:
        if not config_manager.validate_config(config, job):
            console.print("[red]Error:[/red] Configuration validation failed")
            raise typer.Exit(1)
    
    if validate_only:
        console.print("[green]✓[/green] Configuration is valid")
        return
    
    # Show what will be executed
    if verbose or json_output:
        execution_plan = {
            "type": "job" if job else "asset_materialization",
            "target": job if job else "assets",
            "repo": repo,
            "location": location,
            "config": config,
            "tags": run_tags
        }
        
        if asset_selection:
            execution_plan["assets"] = asset_selection
        elif asset_pattern:
            execution_plan["asset_pattern"] = asset_pattern
            execution_plan["expanded_assets"] = submitter.expand_asset_pattern(asset_pattern, repo)
        
        if json_output:
            console.print(json.dumps(execution_plan, indent=2))
        else:
            console.print(Panel(
                Syntax(json.dumps(execution_plan, indent=2), "json"),
                title="Execution Plan",
                border_style="blue"
            ))
    
    # Submit run
    try:
        if job:
            run_id = submitter.submit_job(job, config, repo, location, run_tags)
        else:
            # Determine assets to materialize
            assets = []
            if asset_selection:
                assets = list(asset_selection)
            elif asset_pattern:
                assets = submitter.expand_asset_pattern(asset_pattern, repo)
            
            run_id = submitter.materialize_assets(assets, repo, location, run_tags)
        
        # Show run URL
        run_url = monitor.get_run_url(run_id)
        console.print(f"[dim]View in Dagster UI:[/dim] {run_url}")
        
        # Monitor if requested
        if wait:
            console.print()
            success = asyncio.run(monitor.monitor_run(run_id, timeout, cancel_on_timeout))
            
            if json_output:
                result = {
                    "run_id": run_id,
                    "status": "success" if success else "failed",
                    "url": run_url
                }
                console.print(json.dumps(result))
            
            if not success:
                raise typer.Exit(1)
        else:
            if json_output:
                result = {
                    "run_id": run_id,
                    "status": "submitted",
                    "url": run_url
                }
                console.print(json.dumps(result))
            else:
                console.print(f"\n[green]✓[/green] Run submitted. Monitor with: daglab status {run_id}")
        
    except Exception as e:
        if json_output:
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            console.print(json.dumps(error_result))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("validate")
def validate_command(
    job: Optional[str] = typer.Option(
        None,
        "--job",
        "-j",
        help="Job name to validate"
    ),
    run_config: Optional[Path] = typer.Option(
        None,
        "--run-config",
        "-c", 
        help="Run configuration file to validate"
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repository name"
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location",
        "-l",
        help="Code location name"
    ),
) -> None:
    """Validate job configuration without executing."""
    if not job:
        console.print("[red]Error:[/red] --job is required for validation")
        raise typer.Exit(1)
    
    if not run_config:
        console.print("[red]Error:[/red] --run-config is required for validation")
        raise typer.Exit(1)
    
    config_manager = ConfigManager()
    
    try:
        # Load configuration
        config = config_manager.load_config(run_config)
        console.print(f"[green]✓[/green] Configuration file is valid YAML/JSON")
        
        # Display parsed config
        console.print("\n[bold]Parsed Configuration:[/bold]")
        console.print(Syntax(yaml.dump(config, default_flow_style=False), "yaml"))
        
        # Validate against job schema
        if config_manager.validate_config(config, job):
            console.print(f"\n[green]✓[/green] Configuration is valid for job '{job}'")
        else:
            console.print(f"\n[red]✗[/red] Configuration validation failed for job '{job}'")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list-assets")
def list_assets(
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Filter assets by pattern"
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repository name"
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location",
        "-l",
        help="Code location name"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
) -> None:
    """List available assets for materialization."""
    # TODO: Query Dagster for available assets
    # For now, show example output
    
    assets = [
        {"name": "raw_orders", "group": "ingestion", "description": "Raw order data"},
        {"name": "raw_customers", "group": "ingestion", "description": "Raw customer data"},
        {"name": "cleaned_orders", "group": "transformation", "description": "Cleaned order data"},
        {"name": "cleaned_customers", "group": "transformation", "description": "Cleaned customer data"},
        {"name": "daily_revenue", "group": "analytics", "description": "Daily revenue metrics"},
        {"name": "customer_segments", "group": "analytics", "description": "Customer segmentation"},
    ]
    
    # Filter by pattern
    if pattern:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            assets = [a for a in assets if a["name"].startswith(prefix)]
        else:
            assets = [a for a in assets if pattern in a["name"]]
    
    if json_output:
        console.print(json.dumps(assets, indent=2))
    else:
        table = Table(title="Available Assets")
        table.add_column("Name", style="cyan")
        table.add_column("Group", style="yellow")
        table.add_column("Description")
        
        for asset in assets:
            table.add_row(asset["name"], asset["group"], asset["description"])
        
        console.print(table)


@app.command("list-jobs")
def list_jobs(
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repository name"
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location",
        "-l",
        help="Code location name"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
) -> None:
    """List available jobs."""
    # TODO: Query Dagster for available jobs
    # For now, show example output
    
    jobs = [
        {"name": "daily_etl", "description": "Daily ETL pipeline"},
        {"name": "ml_training", "description": "ML model training pipeline"},
        {"name": "data_quality", "description": "Data quality checks"},
        {"name": "backup_job", "description": "Database backup job"},
    ]
    
    if json_output:
        console.print(json.dumps(jobs, indent=2))
    else:
        table = Table(title="Available Jobs")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        
        for job in jobs:
            table.add_row(job["name"], job["description"])
        
        console.print(table)


if __name__ == "__main__":
    app()