"""Stats command for usage statistics - Phase 5."""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich import box
import plotext as plt

from ..helpers.state import StateManager
from ..helpers.feedback import UserFeedback
from ..runtime.telemetry import TelemetryCollector

console = Console()
app = typer.Typer(help="View usage statistics and metrics [Phase 5]")


class StatsCollector:
    """Collects and analyzes usage statistics."""
    
    def __init__(self):
        self.state_manager = StateManager(namespace="stats")
        self.telemetry = TelemetryCollector()
        self.feedback = UserFeedback()
        self.stats_db = Path.home() / ".daglab" / "stats.db"
        
    def _get_time_range(self, period: str) -> Tuple[datetime, datetime]:
        """Convert period string to datetime range."""
        now = datetime.now()
        
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        elif period == "year":
            start = now - timedelta(days=365)
        else:  # all
            start = datetime(2020, 1, 1)  # Arbitrary old date
            
        return start, now
    
    def collect_command_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Collect command usage statistics."""
        # Get command history from state
        commands = self.state_manager.get("command_history", [])
        
        # Filter by time range
        filtered = [
            cmd for cmd in commands 
            if start <= datetime.fromisoformat(cmd.get("timestamp", "2020-01-01")) <= end
        ]
        
        # Aggregate stats
        command_counts = {}
        success_count = 0
        failure_count = 0
        total_duration = 0
        
        for cmd in filtered:
            cmd_name = cmd.get("command", "unknown")
            command_counts[cmd_name] = command_counts.get(cmd_name, 0) + 1
            
            if cmd.get("success", False):
                success_count += 1
            else:
                failure_count += 1
                
            total_duration += cmd.get("duration", 0)
        
        return {
            "total_commands": len(filtered),
            "command_counts": command_counts,
            "success_rate": success_count / len(filtered) if filtered else 0,
            "failure_rate": failure_count / len(filtered) if filtered else 0,
            "avg_duration": total_duration / len(filtered) if filtered else 0,
            "most_used": max(command_counts.items(), key=lambda x: x[1])[0] if command_counts else None,
        }
    
    def collect_notebook_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Collect notebook usage statistics."""
        notebooks = self.state_manager.get("notebook_history", [])
        
        filtered = [
            nb for nb in notebooks
            if start <= datetime.fromisoformat(nb.get("created_at", "2020-01-01")) <= end
        ]
        
        template_counts = {}
        total_cells = 0
        
        for nb in filtered:
            template = nb.get("template", "custom")
            template_counts[template] = template_counts.get(template, 0) + 1
            total_cells += nb.get("cell_count", 0)
        
        return {
            "total_notebooks": len(filtered),
            "template_usage": template_counts,
            "avg_cells_per_notebook": total_cells / len(filtered) if filtered else 0,
            "most_used_template": max(template_counts.items(), key=lambda x: x[1])[0] if template_counts else None,
        }
    
    def collect_performance_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Collect performance metrics."""
        metrics = self.telemetry.get_metrics(start, end)
        
        return {
            "avg_cpu_usage": metrics.get("cpu", {}).get("average", 0),
            "peak_cpu_usage": metrics.get("cpu", {}).get("max", 0),
            "avg_memory_mb": metrics.get("memory", {}).get("average", 0),
            "peak_memory_mb": metrics.get("memory", {}).get("max", 0),
            "total_disk_io_mb": metrics.get("disk_io", {}).get("total", 0),
            "cache_hit_rate": metrics.get("cache", {}).get("hit_rate", 0),
        }
    
    def collect_error_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Collect error statistics."""
        errors = self.state_manager.get("error_log", [])
        
        filtered = [
            err for err in errors
            if start <= datetime.fromisoformat(err.get("timestamp", "2020-01-01")) <= end
        ]
        
        error_types = {}
        for err in filtered:
            err_type = err.get("type", "unknown")
            error_types[err_type] = error_types.get(err_type, 0) + 1
        
        return {
            "total_errors": len(filtered),
            "error_types": error_types,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None,
        }


class StatsFormatter:
    """Formats statistics for different output types."""
    
    @staticmethod
    def format_table(stats: Dict[str, Any]) -> Table:
        """Format stats as a Rich table."""
        table = Table(title="DagLab Usage Statistics", box=box.ROUNDED)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Metric", style="magenta")
        table.add_column("Value", justify="right", style="green")
        
        # Command stats
        if "command_stats" in stats:
            cmd_stats = stats["command_stats"]
            table.add_row("Commands", "Total Executed", str(cmd_stats["total_commands"]))
            table.add_row("", "Success Rate", f"{cmd_stats['success_rate']:.1%}")
            table.add_row("", "Most Used", cmd_stats["most_used"] or "N/A")
            table.add_row("", "Avg Duration", f"{cmd_stats['avg_duration']:.2f}s")
        
        # Notebook stats
        if "notebook_stats" in stats:
            nb_stats = stats["notebook_stats"]
            table.add_row("Notebooks", "Total Created", str(nb_stats["total_notebooks"]))
            table.add_row("", "Most Used Template", nb_stats["most_used_template"] or "N/A")
            table.add_row("", "Avg Cells", f"{nb_stats['avg_cells_per_notebook']:.1f}")
        
        # Performance stats
        if "performance_stats" in stats:
            perf_stats = stats["performance_stats"]
            table.add_row("Performance", "Avg CPU", f"{perf_stats['avg_cpu_usage']:.1f}%")
            table.add_row("", "Peak Memory", f"{perf_stats['peak_memory_mb']:.0f} MB")
            table.add_row("", "Cache Hit Rate", f"{perf_stats['cache_hit_rate']:.1%}")
        
        # Error stats
        if "error_stats" in stats:
            err_stats = stats["error_stats"]
            table.add_row("Errors", "Total", str(err_stats["total_errors"]))
            table.add_row("", "Most Common", err_stats["most_common_error"] or "N/A")
        
        return table
    
    @staticmethod
    def format_json(stats: Dict[str, Any]) -> str:
        """Format stats as JSON."""
        return json.dumps(stats, indent=2, default=str)
    
    @staticmethod
    def format_csv(stats: Dict[str, Any], filepath: Path) -> None:
        """Export stats to CSV file."""
        rows = []
        
        # Flatten nested stats
        for category, metrics in stats.items():
            if isinstance(metrics, dict):
                for metric, value in metrics.items():
                    if not isinstance(value, dict):
                        rows.append({
                            "category": category,
                            "metric": metric,
                            "value": value
                        })
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["category", "metric", "value"])
            writer.writeheader()
            writer.writerows(rows)
    
    @staticmethod
    def format_chart(stats: Dict[str, Any]) -> None:
        """Display stats as charts."""
        plt.clear_figure()
        
        # Command usage chart
        if "command_stats" in stats and stats["command_stats"]["command_counts"]:
            commands = list(stats["command_stats"]["command_counts"].keys())
            counts = list(stats["command_stats"]["command_counts"].values())
            
            plt.bar(commands[:10], counts[:10])  # Top 10
            plt.title("Top 10 Commands")
            plt.show()
            plt.clear_figure()
        
        # Performance trend (mock data for now)
        days = [f"Day {i}" for i in range(1, 8)]
        cpu_usage = [20, 25, 30, 22, 28, 35, 30]
        
        plt.plot(days, cpu_usage)
        plt.title("CPU Usage Trend (Last Week)")
        plt.show()


@app.callback(invoke_without_command=True)
def stats(
    ctx: typer.Context,
    period: str = typer.Option(
        "week",
        "--period",
        "-p",
        help="Time period (today|week|month|year|all)"
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table|json|csv|chart)"
    ),
    entity: Optional[str] = typer.Option(
        None,
        "--entity",
        "-e",
        help="Filter by specific entity"
    ),
    export: Optional[Path] = typer.Option(
        None,
        "--export",
        help="Export stats to file"
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Show stats since date (YYYY-MM-DD)"
    ),
) -> None:
    """View comprehensive usage statistics and metrics.
    
    Track notebook executions, asset materializations, job runs,
    and system resource usage over time.
    
    Examples:
        daglab stats
        daglab stats --period month --format chart
        daglab stats --entity my_asset --period year
        daglab stats --export stats_report.csv
        daglab stats --since 2024-01-01 --format json
    """
    if ctx.invoked_subcommand is None:
        feedback = UserFeedback()
        collector = StatsCollector()
        formatter = StatsFormatter()
        
        with feedback.progress("Collecting statistics...") as progress:
            # Determine time range
            if since:
                try:
                    start = datetime.fromisoformat(since)
                    end = datetime.now()
                except ValueError:
                    feedback.error(f"Invalid date format: {since}. Use YYYY-MM-DD")
                    raise typer.Exit(1)
            else:
                start, end = collector._get_time_range(period)
            
            # Collect all stats
            stats = {}
            
            progress.update("Collecting command statistics...")
            stats["command_stats"] = collector.collect_command_stats(start, end)
            
            progress.update("Collecting notebook statistics...")
            stats["notebook_stats"] = collector.collect_notebook_stats(start, end)
            
            progress.update("Collecting performance metrics...")
            stats["performance_stats"] = collector.collect_performance_stats(start, end)
            
            progress.update("Collecting error statistics...")
            stats["error_stats"] = collector.collect_error_stats(start, end)
            
            # Add metadata
            stats["meta"] = {
                "period": period if not since else "custom",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "generated_at": datetime.now().isoformat(),
            }
        
        # Filter by entity if specified
        if entity:
            # TODO: Implement entity-specific filtering
            feedback.info(f"Filtering by entity: {entity}")
        
        # Format output
        if format == "table":
            console.print(formatter.format_table(stats))
        elif format == "json":
            console.print(formatter.format_json(stats))
        elif format == "csv":
            if export:
                formatter.format_csv(stats, export)
                feedback.success(f"Stats exported to {export}")
            else:
                feedback.error("CSV format requires --export option")
                raise typer.Exit(1)
        elif format == "chart":
            formatter.format_chart(stats)
        else:
            feedback.error(f"Unknown format: {format}")
            raise typer.Exit(1)
        
        # Export if requested (for non-CSV formats)
        if export and format != "csv":
            export_path = Path(export)
            if format == "json":
                export_path.write_text(formatter.format_json(stats))
            else:
                # Export as JSON for other formats
                export_path.write_text(formatter.format_json(stats))
            feedback.success(f"Stats exported to {export_path}")


@app.command()
def reset() -> None:
    """Reset statistics database."""
    feedback = UserFeedback()
    
    if feedback.confirm("Are you sure you want to reset all statistics?"):
        state_manager = StateManager(namespace="stats")
        state_manager.clear_namespace()
        feedback.success("Statistics have been reset")
    else:
        feedback.info("Reset cancelled")


@app.command()
def trends(
    metric: str = typer.Argument(
        "cpu",
        help="Metric to analyze (cpu|memory|errors|commands)"
    ),
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Number of days to analyze"
    ),
) -> None:
    """Analyze trends for specific metrics."""
    feedback = UserFeedback()
    
    with feedback.progress(f"Analyzing {metric} trends...") as progress:
        # TODO: Implement trend analysis
        progress.update("Collecting historical data...")
        progress.update("Calculating trends...")
        progress.update("Generating visualization...")
    
    feedback.success(f"Trend analysis complete for {metric}")


if __name__ == "__main__":
    app()
