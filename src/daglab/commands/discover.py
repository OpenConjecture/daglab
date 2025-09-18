"""Discover command for Dagster entity exploration."""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
import requests
from requests.auth import HTTPBasicAuth

try:
    from dagster_graphql import DagsterGraphQLClient
    from dagster_graphql.client.query import LAUNCH_PIPELINE_EXECUTION_MUTATION
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

console = Console()
app = typer.Typer(help="Discover Dagster entities")


class DagsterDiscoveryClient:
    """Client for discovering Dagster entities via GraphQL API."""
    
    def __init__(self, host: str = "localhost", port: int = 3000, auth_token: Optional[str] = None):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.base_url = f"http://{host}:{port}"
        self.graphql_url = f"{self.base_url}/graphql"
        
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GraphQL request to Dagster."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        try:
            response = requests.post(
                self.graphql_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Dagster: {e}[/red]")
            return {}
            
    def discover_repositories(self) -> List[Dict[str, Any]]:
        """Discover all repositories and code locations."""
        query = '''
        {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        id
                        name
                        location {
                            id
                            name
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        '''
        
        result = self._make_request(query)
        if result and "data" in result:
            repos_or_error = result["data"].get("repositoriesOrError", {})
            if "nodes" in repos_or_error:
                return repos_or_error["nodes"]
        return []
        
    def discover_jobs(self, repository_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover all jobs in repositories."""
        query = '''
        query JobsQuery($repositorySelector: RepositorySelector) {
            pipelinesOrError(repositorySelector: $repositorySelector) {
                ... on PipelineConnection {
                    nodes {
                        id
                        name
                        description
                        tags {
                            key
                            value
                        }
                        modes {
                            name
                        }
                        solidHandles {
                            handleID
                            solid {
                                name
                                definition {
                                    name
                                    description
                                }
                            }
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        '''
        
        variables = {}
        if repository_name:
            # First get the repository location
            repos = self.discover_repositories()
            repo = next((r for r in repos if r["name"] == repository_name), None)
            if repo:
                variables["repositorySelector"] = {
                    "repositoryLocationName": repo["location"]["name"],
                    "repositoryName": repository_name
                }
                
        result = self._make_request(query, variables)
        if result and "data" in result:
            jobs_or_error = result["data"].get("pipelinesOrError", {})
            if "nodes" in jobs_or_error:
                return jobs_or_error["nodes"]
        return []
        
    def discover_assets(self, repository_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover all assets in repositories."""
        query = '''
        query AssetsQuery {
            assetsOrError {
                ... on AssetConnection {
                    nodes {
                        id
                        key {
                            path
                        }
                        description
                        computeKind
                        opNames
                        tags {
                            key
                            value
                        }
                        dependencies {
                            asset {
                                key {
                                    path
                                }
                            }
                        }
                        dependedBy {
                            asset {
                                key {
                                    path
                                }
                            }
                        }
                        repository {
                            id
                            name
                            location {
                                id
                                name
                            }
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        '''
        
        result = self._make_request(query)
        if result and "data" in result:
            assets_or_error = result["data"].get("assetsOrError", {})
            if "nodes" in assets_or_error:
                assets = assets_or_error["nodes"]
                if repository_name:
                    # Filter by repository
                    assets = [
                        a for a in assets 
                        if a.get("repository", {}).get("name") == repository_name
                    ]
                return assets
        return []
        
    def discover_sensors(self, repository_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover all sensors in repositories."""
        query = '''
        query SensorsQuery($repositorySelector: RepositorySelector) {
            sensorsOrError(repositorySelector: $repositorySelector) {
                ... on Sensors {
                    results {
                        id
                        name
                        description
                        sensorType
                        jobOriginId
                        targets {
                            pipelineName
                            mode
                        }
                        metadata {
                            assetKeys {
                                path
                            }
                        }
                        sensorState {
                            id
                            status
                            runs {
                                id
                                runId
                                status
                            }
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        '''
        
        variables = {}
        if repository_name:
            repos = self.discover_repositories()
            repo = next((r for r in repos if r["name"] == repository_name), None)
            if repo:
                variables["repositorySelector"] = {
                    "repositoryLocationName": repo["location"]["name"],
                    "repositoryName": repository_name
                }
                
        result = self._make_request(query, variables)
        if result and "data" in result:
            sensors_or_error = result["data"].get("sensorsOrError", {})
            if "results" in sensors_or_error:
                return sensors_or_error["results"]
        return []
        
    def discover_schedules(self, repository_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover all schedules in repositories."""
        query = '''
        query SchedulesQuery($repositorySelector: RepositorySelector) {
            schedulesOrError(repositorySelector: $repositorySelector) {
                ... on Schedules {
                    results {
                        id
                        name
                        description
                        cronSchedule
                        pipelineName
                        mode
                        scheduleState {
                            id
                            status
                            runs {
                                id
                                runId
                                status
                            }
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        '''
        
        variables = {}
        if repository_name:
            repos = self.discover_repositories()
            repo = next((r for r in repos if r["name"] == repository_name), None)
            if repo:
                variables["repositorySelector"] = {
                    "repositoryLocationName": repo["location"]["name"],
                    "repositoryName": repository_name
                }
                
        result = self._make_request(query, variables)
        if result and "data" in result:
            schedules_or_error = result["data"].get("schedulesOrError", {})
            if "results" in schedules_or_error:
                return schedules_or_error["results"]
        return []


def filter_by_pattern(items: List[Dict], pattern: str, key_path: str) -> List[Dict]:
    """Filter items by pattern matching."""
    if not pattern:
        return items
        
    # Convert wildcards to regex
    regex_pattern = pattern.replace("*", ".*")
    regex = re.compile(regex_pattern, re.IGNORECASE)
    
    filtered = []
    for item in items:
        # Navigate nested keys
        value = item
        for key in key_path.split("."):
            value = value.get(key, "")
        
        if regex.match(str(value)):
            filtered.append(item)
            
    return filtered


def filter_by_tags(items: List[Dict], tags: List[str]) -> List[Dict]:
    """Filter items by tags."""
    if not tags:
        return items
        
    tag_filters = {}
    for tag in tags:
        if "=" in tag:
            key, value = tag.split("=", 1)
            tag_filters[key] = value
        else:
            tag_filters[tag] = None
            
    filtered = []
    for item in items:
        item_tags = {t["key"]: t["value"] for t in item.get("tags", [])}
        
        match = True
        for key, value in tag_filters.items():
            if value is None:
                # Just check if tag exists
                if key not in item_tags:
                    match = False
                    break
            else:
                # Check if tag has specific value
                if item_tags.get(key) != value:
                    match = False
                    break
                    
        if match:
            filtered.append(item)
            
    return filtered


def display_repositories(repos: List[Dict], verbose: bool = False) -> None:
    """Display repositories in a table."""
    if not repos:
        console.print("[yellow]No repositories found.[/yellow]")
        return
        
    table = Table(title="Repositories & Code Locations", box=box.ROUNDED)
    table.add_column("Repository", style="cyan")
    table.add_column("Code Location", style="green")
    table.add_column("ID", style="dim")
    
    for repo in repos:
        table.add_row(
            repo["name"],
            repo["location"]["name"],
            repo["id"] if verbose else "..."
        )
        
    console.print(table)
    

def display_jobs(jobs: List[Dict], verbose: bool = False) -> None:
    """Display jobs in a table."""
    if not jobs:
        console.print("[yellow]No jobs found.[/yellow]")
        return
        
    table = Table(title="Jobs", box=box.ROUNDED)
    table.add_column("Job Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Ops Count", style="green")
    table.add_column("Tags", style="magenta")
    
    for job in jobs:
        tags = ", ".join([f"{t['key']}={t['value']}" for t in job.get("tags", [])])
        op_count = len(job.get("solidHandles", []))
        
        table.add_row(
            job["name"],
            job.get("description", "") or "[dim]No description[/dim]",
            str(op_count),
            tags or "[dim]No tags[/dim]"
        )
        
    console.print(table)
    
    if verbose:
        console.print("\n[bold]Job Details:[/bold]")
        for job in jobs:
            tree = Tree(f"[bold cyan]{job['name']}[/bold cyan]")
            if job.get("description"):
                tree.add(f"[dim]Description:[/dim] {job['description']}")
            
            if job.get("solidHandles"):
                ops_branch = tree.add("[green]Ops:[/green]")
                for handle in job["solidHandles"]:
                    op_name = handle["solid"]["name"]
                    op_desc = handle["solid"]["definition"].get("description", "")
                    if op_desc:
                        ops_branch.add(f"{op_name} - [dim]{op_desc}[/dim]")
                    else:
                        ops_branch.add(op_name)
                        
            console.print(tree)
            console.print()


def display_assets(assets: List[Dict], verbose: bool = False) -> None:
    """Display assets in a table with lineage information."""
    if not assets:
        console.print("[yellow]No assets found.[/yellow]")
        return
        
    table = Table(title="Assets", box=box.ROUNDED)
    table.add_column("Asset Key", style="cyan")
    table.add_column("Compute Kind", style="green")
    table.add_column("Dependencies", style="blue")
    table.add_column("Dependents", style="magenta")
    table.add_column("Tags", style="yellow")
    
    for asset in assets:
        asset_key = ".".join(asset["key"]["path"])
        compute_kind = asset.get("computeKind", "Unknown")
        
        deps = [
            ".".join(d["asset"]["key"]["path"]) 
            for d in asset.get("dependencies", [])
        ]
        deps_str = ", ".join(deps[:3])
        if len(deps) > 3:
            deps_str += f" (+{len(deps)-3})"
            
        dependents = [
            ".".join(d["asset"]["key"]["path"]) 
            for d in asset.get("dependedBy", [])
        ]
        dependents_str = ", ".join(dependents[:3])
        if len(dependents) > 3:
            dependents_str += f" (+{len(dependents)-3})"
            
        tags = ", ".join([
            f"{t['key']}={t['value']}" 
            for t in asset.get("tags", [])
        ][:3])
        
        table.add_row(
            asset_key,
            compute_kind or "[dim]N/A[/dim]",
            deps_str or "[dim]None[/dim]",
            dependents_str or "[dim]None[/dim]",
            tags or "[dim]No tags[/dim]"
        )
        
    console.print(table)
    
    if verbose:
        console.print("\n[bold]Asset Lineage:[/bold]")
        for asset in assets[:5]:  # Limit to first 5 for readability
            asset_key = ".".join(asset["key"]["path"])
            tree = Tree(f"[bold cyan]{asset_key}[/bold cyan]")
            
            if asset.get("description"):
                tree.add(f"[dim]Description:[/dim] {asset['description']}")
                
            if asset.get("dependencies"):
                deps_branch = tree.add("[blue]← Dependencies:[/blue]")
                for dep in asset["dependencies"]:
                    dep_key = ".".join(dep["asset"]["key"]["path"])
                    deps_branch.add(dep_key)
                    
            if asset.get("dependedBy"):
                deps_branch = tree.add("[magenta]→ Used by:[/magenta]")
                for dep in asset["dependedBy"]:
                    dep_key = ".".join(dep["asset"]["key"]["path"])
                    deps_branch.add(dep_key)
                    
            console.print(tree)
            console.print()


def display_sensors(sensors: List[Dict], verbose: bool = False) -> None:
    """Display sensors in a table."""
    if not sensors:
        console.print("[yellow]No sensors found.[/yellow]")
        return
        
    table = Table(title="Sensors", box=box.ROUNDED)
    table.add_column("Sensor Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Targets", style="blue")
    
    for sensor in sensors:
        status = "Unknown"
        if sensor.get("sensorState"):
            status = sensor["sensorState"].get("status", "Unknown")
            
        targets = [
            f"{t['pipelineName']}" 
            for t in sensor.get("targets", [])
        ]
        targets_str = ", ".join(targets)
        
        # Color code status
        if status == "RUNNING":
            status_display = "[green]● RUNNING[/green]"
        elif status == "STOPPED":
            status_display = "[red]● STOPPED[/red]"
        else:
            status_display = f"[yellow]● {status}[/yellow]"
            
        table.add_row(
            sensor["name"],
            sensor.get("sensorType", "Unknown"),
            status_display,
            targets_str or "[dim]No targets[/dim]"
        )
        
    console.print(table)


def display_schedules(schedules: List[Dict], verbose: bool = False) -> None:
    """Display schedules in a table."""
    if not schedules:
        console.print("[yellow]No schedules found.[/yellow]")
        return
        
    table = Table(title="Schedules", box=box.ROUNDED)
    table.add_column("Schedule Name", style="cyan")
    table.add_column("Cron Schedule", style="green")
    table.add_column("Pipeline", style="blue")
    table.add_column("Status", style="yellow")
    
    for schedule in schedules:
        status = "Unknown"
        if schedule.get("scheduleState"):
            status = schedule["scheduleState"].get("status", "Unknown")
            
        # Color code status
        if status == "RUNNING":
            status_display = "[green]● RUNNING[/green]"
        elif status == "STOPPED":
            status_display = "[red]● STOPPED[/red]"
        else:
            status_display = f"[yellow]● {status}[/yellow]"
            
        table.add_row(
            schedule["name"],
            schedule.get("cronSchedule", "N/A"),
            schedule.get("pipelineName", "N/A"),
            status_display
        )
        
    console.print(table)


def export_to_json(data: Dict[str, Any], output_file: Optional[str] = None) -> None:
    """Export discovery results to JSON."""
    json_str = json.dumps(data, indent=2)
    
    if output_file:
        Path(output_file).write_text(json_str)
        console.print(f"[green]✓ Exported to {output_file}[/green]")
    else:
        console.print(json_str)


@app.callback(invoke_without_command=True)
def discover(
    ctx: typer.Context,
    filter: Optional[str] = typer.Option(
        "all",
        "--filter",
        "-f",
        help="Filter entities to discover (jobs|assets|repos|locations|sensors|schedules|all)"
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Pattern to match entity names (supports wildcards: *etl*, daily_*)"
    ),
    tags: Optional[List[str]] = typer.Option(
        None,
        "--tags",
        "-t",
        help="Filter by tags (e.g., --tags env=prod --tags team=data)"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format"
    ),
    dagster_port: int = typer.Option(
        3000,
        "--dagster-port",
        help="Dagster GraphQL port"
    ),
    auth_token: Optional[str] = typer.Option(
        None,
        "--auth-token",
        help="Authentication token for Dagster"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information"
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for JSON export"
    ),
) -> None:
    """Discover and explore Dagster entities in your codebase.
    
    This command connects to your Dagster instance and discovers:
    - Repositories and code locations
    - Jobs (pipelines) with metadata
    - Assets with lineage information
    - Sensors and their targets
    - Schedules and their configuration
    
    Examples:
        daglab discover --filter assets
        daglab discover --filter jobs --pattern "daily_*"
        daglab discover --tags env=prod team=data
        daglab discover --json --output entities.json
        daglab discover --verbose
    """
    if ctx.invoked_subcommand is not None:
        return
        
    console.print("[bold cyan]🔍 Discovering Dagster entities...[/bold cyan]\n")
    
    # Initialize discovery client
    client = DagsterDiscoveryClient(port=dagster_port, auth_token=auth_token)
    
    # Check connection
    try:
        response = requests.get(f"http://localhost:{dagster_port}/graphql", timeout=5)
        if response.status_code != 200:
            console.print(f"[red]✗ Cannot connect to Dagster at port {dagster_port}[/red]")
            console.print("[dim]Make sure Dagster is running with: dagster dev[/dim]")
            sys.exit(1)
    except requests.exceptions.RequestException:
        console.print(f"[red]✗ Cannot connect to Dagster at port {dagster_port}[/red]")
        console.print("[dim]Make sure Dagster is running with: dagster dev[/dim]")
        sys.exit(1)
        
    # Collect all discovery results
    results = {
        "timestamp": datetime.now().isoformat(),
        "filter": filter,
        "pattern": pattern,
        "tags": tags,
        "entities": {}
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Discover repositories
        if filter in ["all", "repos", "locations"]:
            task = progress.add_task("Discovering repositories...", total=1)
            repos = client.discover_repositories()
            results["entities"]["repositories"] = repos
            progress.update(task, completed=1)
            
            if not json_output:
                display_repositories(repos, verbose)
                console.print()
                
        # Discover jobs
        if filter in ["all", "jobs"]:
            task = progress.add_task("Discovering jobs...", total=1)
            jobs = client.discover_jobs()
            
            # Apply filters
            if pattern:
                jobs = filter_by_pattern(jobs, pattern, "name")
            if tags:
                jobs = filter_by_tags(jobs, tags)
                
            results["entities"]["jobs"] = jobs
            progress.update(task, completed=1)
            
            if not json_output:
                display_jobs(jobs, verbose)
                console.print()
                
        # Discover assets
        if filter in ["all", "assets"]:
            task = progress.add_task("Discovering assets...", total=1)
            assets = client.discover_assets()
            
            # Apply filters
            if pattern:
                # For assets, match on the full key path
                filtered_assets = []
                for asset in assets:
                    asset_key = ".".join(asset["key"]["path"])
                    if re.match(pattern.replace("*", ".*"), asset_key, re.IGNORECASE):
                        filtered_assets.append(asset)
                assets = filtered_assets
                
            if tags:
                assets = filter_by_tags(assets, tags)
                
            results["entities"]["assets"] = assets
            progress.update(task, completed=1)
            
            if not json_output:
                display_assets(assets, verbose)
                console.print()
                
        # Discover sensors
        if filter in ["all", "sensors"]:
            task = progress.add_task("Discovering sensors...", total=1)
            sensors = client.discover_sensors()
            
            # Apply filters
            if pattern:
                sensors = filter_by_pattern(sensors, pattern, "name")
                
            results["entities"]["sensors"] = sensors
            progress.update(task, completed=1)
            
            if not json_output:
                display_sensors(sensors, verbose)
                console.print()
                
        # Discover schedules
        if filter in ["all", "schedules"]:
            task = progress.add_task("Discovering schedules...", total=1)
            schedules = client.discover_schedules()
            
            # Apply filters
            if pattern:
                schedules = filter_by_pattern(schedules, pattern, "name")
                
            results["entities"]["schedules"] = schedules
            progress.update(task, completed=1)
            
            if not json_output:
                display_schedules(schedules, verbose)
                console.print()
                
    # Display summary
    if not json_output:
        summary_table = Table(title="Discovery Summary", box=box.ROUNDED)
        summary_table.add_column("Entity Type", style="cyan")
        summary_table.add_column("Count", style="green")
        
        entity_counts = [
            ("Repositories", len(results["entities"].get("repositories", []))),
            ("Jobs", len(results["entities"].get("jobs", []))),
            ("Assets", len(results["entities"].get("assets", []))),
            ("Sensors", len(results["entities"].get("sensors", []))),
            ("Schedules", len(results["entities"].get("schedules", []))),
        ]
        
        total = 0
        for entity_type, count in entity_counts:
            if entity_type.lower() in results["entities"]:
                summary_table.add_row(entity_type, str(count))
                total += count
                
        summary_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
        console.print(summary_table)
        
        # Show applied filters
        if pattern or tags:
            console.print("\n[bold]Applied Filters:[/bold]")
            if pattern:
                console.print(f"  Pattern: [cyan]{pattern}[/cyan]")
            if tags:
                console.print(f"  Tags: [cyan]{', '.join(tags)}[/cyan]")
    else:
        # Export to JSON
        export_to_json(results, output)
        
    # Post-task hook
    import subprocess
    subprocess.run([
        "npx", "claude-flow@alpha", "hooks", "notify",
        "--message", f"Discovered {total if 'total' in locals() else 0} Dagster entities"
    ])


if __name__ == "__main__":
    app()
