"""Clean command for removing artifacts and temporary files."""

import typer
import shutil
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.prompt import Confirm

from daglab.runtime.logging import get_logger

app = typer.Typer()
console = Console()
logger = get_logger(__name__)


class Cleaner:
    """File cleanup utilities."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.files_removed = 0
        self.space_freed = 0
        
    def get_size(self, path: Path) -> int:
        """Get size of file or directory in bytes."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total
        return 0
    
    def format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def find_artifacts(self) -> List[Tuple[Path, int]]:
        """Find artifact files."""
        artifacts = []
        artifacts_dir = self.base_path / "artifacts"
        
        if artifacts_dir.exists():
            for item in artifacts_dir.rglob("*"):
                if item.is_file() and item.name != ".gitkeep":
                    size = self.get_size(item)
                    artifacts.append((item, size))
        
        return artifacts
    
    def find_logs(self, older_than_days: int = 0) -> List[Tuple[Path, int]]:
        """Find log files."""
        logs = []
        logs_dir = self.base_path / "logs"
        
        if logs_dir.exists():
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            
            for item in logs_dir.rglob("*"):
                if item.is_file() and item.name != ".gitkeep":
                    if older_than_days == 0 or datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                        size = self.get_size(item)
                        logs.append((item, size))
        
        return logs
    
    def find_temp_files(self) -> List[Tuple[Path, int]]:
        """Find temporary files."""
        temp_patterns = [
            "*.tmp",
            "*.temp",
            "*.cache",
            "*.pyc",
            "__pycache__",
            ".DS_Store",
            "Thumbs.db",
            "*.swp",
            "*.swo",
            "*~",
        ]
        
        temp_files = []
        
        for pattern in temp_patterns:
            for item in self.base_path.rglob(pattern):
                if item.is_file():
                    size = self.get_size(item)
                    temp_files.append((item, size))
                elif item.is_dir() and item.name == "__pycache__":
                    size = self.get_size(item)
                    temp_files.append((item, size))
        
        return temp_files
    
    def find_data_files(self) -> List[Tuple[Path, int]]:
        """Find data files marked as temporary."""
        data_files = []
        data_dir = self.base_path / "data"
        
        if data_dir.exists():
            for item in data_dir.glob("*.tmp"):
                if item.is_file():
                    size = self.get_size(item)
                    data_files.append((item, size))
        
        return data_files
    
    def remove_files(self, files: List[Tuple[Path, int]], dry_run: bool = False) -> int:
        """Remove files and return bytes freed."""
        total_freed = 0
        
        for file_path, size in files:
            if not dry_run:
                try:
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    self.files_removed += 1
                    total_freed += size
                except Exception as e:
                    console.print(f"[red]Error removing {file_path}: {e}[/red]")
            else:
                total_freed += size
        
        self.space_freed += total_freed
        return total_freed


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Clean up artifacts and temporary files."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(clean_all)


@app.command(name="all")
def clean_all(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clean all artifacts, logs, and temporary files."""
    cleaner = Cleaner(path)
    
    console.print(Panel.fit(
        "[bold]Daglab Clean[/bold]\n"
        f"[dim]{'DRY RUN - No files will be removed' if dry_run else 'Scanning for files to clean...'}[/dim]",
        border_style="yellow" if dry_run else "blue"
    ))
    
    # Find all cleanable files
    artifacts = cleaner.find_artifacts()
    logs = cleaner.find_logs()
    temp_files = cleaner.find_temp_files()
    data_files = cleaner.find_data_files()
    
    # Prepare summary
    categories = [
        ("Artifacts", artifacts, "green"),
        ("Logs", logs, "yellow"),
        ("Temporary files", temp_files, "red"),
        ("Data files", data_files, "blue"),
    ]
    
    # Display summary
    table = Table(title="Files to Clean", show_header=True, header_style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")
    
    total_files = 0
    total_size = 0
    
    for category_name, files, color in categories:
        if files:
            size = sum(s for _, s in files)
            table.add_row(
                f"[{color}]{category_name}[/{color}]",
                str(len(files)),
                cleaner.format_size(size)
            )
            total_files += len(files)
            total_size += size
    
    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_files} files, {cleaner.format_size(total_size)}")
    
    if total_files == 0:
        console.print("\n[green]Nothing to clean![/green]")
        return
    
    # Confirm action
    if not dry_run and not force:
        if not Confirm.ask("\nProceed with cleanup?", default=False):
            console.print("[yellow]Cleanup cancelled[/yellow]")
            return
    
    # Perform cleanup
    if not dry_run:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Cleaning files...", total=total_files)
            
            for category_name, files, _ in categories:
                if files:
                    cleaner.remove_files(files, dry_run)
                    progress.update(task, advance=len(files))
        
        console.print(f"\n[green]✓ Cleaned {cleaner.files_removed} files[/green]")
        console.print(f"[green]✓ Freed {cleaner.format_size(cleaner.space_freed)}[/green]")
    else:
        console.print("\n[dim]Run without --dry-run to remove these files[/dim]")


@app.command(name="artifacts")
def clean_artifacts(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
):
    """Clean only artifact files."""
    cleaner = Cleaner(path)
    artifacts = cleaner.find_artifacts()
    
    if not artifacts:
        console.print("[green]No artifacts to clean[/green]")
        return
    
    console.print(f"Found {len(artifacts)} artifact files")
    total_size = sum(s for _, s in artifacts)
    console.print(f"Total size: {cleaner.format_size(total_size)}")
    
    if not dry_run:
        freed = cleaner.remove_files(artifacts)
        console.print(f"[green]✓ Cleaned {len(artifacts)} files, freed {cleaner.format_size(freed)}[/green]")
    else:
        console.print("[dim]Run without --dry-run to remove these files[/dim]")


@app.command(name="logs")
def clean_logs(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    older_than: int = typer.Option(7, "--older-than", help="Remove logs older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
):
    """Clean log files older than specified days."""
    cleaner = Cleaner(path)
    logs = cleaner.find_logs(older_than_days=older_than)
    
    if not logs:
        console.print(f"[green]No logs older than {older_than} days to clean[/green]")
        return
    
    console.print(f"Found {len(logs)} log files older than {older_than} days")
    total_size = sum(s for _, s in logs)
    console.print(f"Total size: {cleaner.format_size(total_size)}")
    
    if not dry_run:
        freed = cleaner.remove_files(logs)
        console.print(f"[green]✓ Cleaned {len(logs)} files, freed {cleaner.format_size(freed)}[/green]")
    else:
        console.print("[dim]Run without --dry-run to remove these files[/dim]")


@app.command(name="cache")
def clean_cache(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
):
    """Clean Python cache and temporary files."""
    cleaner = Cleaner(path)
    temp_files = cleaner.find_temp_files()
    
    if not temp_files:
        console.print("[green]No cache files to clean[/green]")
        return
    
    console.print(f"Found {len(temp_files)} cache/temporary files")
    total_size = sum(s for _, s in temp_files)
    console.print(f"Total size: {cleaner.format_size(total_size)}")
    
    if not dry_run:
        freed = cleaner.remove_files(temp_files)
        console.print(f"[green]✓ Cleaned {len(temp_files)} files, freed {cleaner.format_size(freed)}[/green]")
    else:
        console.print("[dim]Run without --dry-run to remove these files[/dim]")