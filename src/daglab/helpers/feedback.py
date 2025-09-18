"""User feedback and interaction utilities with Rich integration."""

import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Any, Union, Dict
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
from rich import box
from rich.text import Text
from rich.style import Style

console = Console()


class UserFeedback:
    """Enhanced user feedback system with Rich integration."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._start_times = {}
        
    def info(self, message: str, title: Optional[str] = None) -> None:
        """Display information message."""
        if title:
            self.console.print(Panel(f"[blue]{message}[/blue]", title=title, border_style="blue"))
        else:
            self.console.print(f"[blue]ℹ[/blue]  {message}")
    
    def success(self, message: str, title: Optional[str] = None, icon: str = "✓") -> None:
        """Display success message with optional animation."""
        if title:
            self.console.print(Panel(f"[green]{message}[/green]", title=title, border_style="green"))
        else:
            # Animate the checkmark
            with self.console.status("", spinner="dots") as status:
                for _ in range(3):
                    status.update("")
                    time.sleep(0.1)
            self.console.print(f"[green]{icon}[/green]  {message}")
    
    def warning(self, message: str, title: Optional[str] = None) -> None:
        """Display warning message."""
        if title:
            self.console.print(Panel(f"[yellow]{message}[/yellow]", title=title, border_style="yellow"))
        else:
            self.console.print(f"[yellow]⚠[/yellow]  {message}")
    
    def error(self, message: str, title: Optional[str] = None, suggestions: Optional[List[str]] = None) -> None:
        """Display error message with optional suggestions."""
        if title:
            content = f"[red]{message}[/red]"
            if suggestions:
                content += "\n\n[dim]Suggestions:[/dim]"
                for suggestion in suggestions:
                    content += f"\n  • {suggestion}"
            self.console.print(Panel(content, title=title, border_style="red"))
        else:
            self.console.print(f"[red]✗[/red]  {message}")
            if suggestions:
                self.console.print("[dim]  Suggestions:[/dim]")
                for suggestion in suggestions:
                    self.console.print(f"[dim]    • {suggestion}[/dim]")
    
    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask for user confirmation."""
        return Confirm.ask(question, default=default, console=self.console)
    
    def prompt(self, question: str, default: Optional[str] = None, password: bool = False) -> str:
        """Prompt for user input."""
        return Prompt.ask(question, default=default, password=password, console=self.console)
    
    @contextmanager
    def progress(self, description: str, total: Optional[int] = None):
        """Context manager for progress indication."""
        if total is None:
            # Indeterminate progress with spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=None)
                
                class ProgressUpdater:
                    def update(self, new_description: Optional[str] = None, advance: int = 1):
                        if new_description:
                            progress.update(task, description=new_description)
                        if total is not None:
                            progress.update(task, advance=advance)
                
                yield ProgressUpdater()
        else:
            # Determinate progress with bar
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=total)
                
                class ProgressUpdater:
                    def update(self, new_description: Optional[str] = None, advance: int = 1):
                        if new_description:
                            progress.update(task, description=new_description)
                        progress.update(task, advance=advance)
                    
                    @property
                    def completed(self) -> int:
                        return progress.tasks[task].completed
                
                yield ProgressUpdater()
    
    def show_code(self, code: str, language: str = "python", title: Optional[str] = None) -> None:
        """Display syntax-highlighted code."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        if title:
            self.console.print(Panel(syntax, title=title, border_style="cyan"))
        else:
            self.console.print(syntax)
    
    def show_diff(self, old: str, new: str, title: str = "Changes") -> None:
        """Display a diff between old and new content."""
        # Simple line-based diff visualization
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        
        diff_text = Text()
        
        # Find differences (simplified)
        max_lines = max(len(old_lines), len(new_lines))
        for i in range(max_lines):
            if i < len(old_lines) and i < len(new_lines):
                if old_lines[i] != new_lines[i]:
                    diff_text.append(f"- {old_lines[i]}\n", style="red")
                    diff_text.append(f"+ {new_lines[i]}\n", style="green")
                else:
                    diff_text.append(f"  {old_lines[i]}\n", style="dim")
            elif i < len(old_lines):
                diff_text.append(f"- {old_lines[i]}\n", style="red")
            else:
                diff_text.append(f"+ {new_lines[i]}\n", style="green")
        
        self.console.print(Panel(diff_text, title=title, border_style="yellow"))
    
    def timer_start(self, name: str) -> None:
        """Start a named timer."""
        self._start_times[name] = time.time()
    
    def timer_end(self, name: str, message: Optional[str] = None) -> float:
        """End a named timer and optionally display elapsed time."""
        if name not in self._start_times:
            return 0.0
        
        elapsed = time.time() - self._start_times[name]
        del self._start_times[name]
        
        if message:
            self.info(f"{message} took {elapsed:.2f} seconds")
        
        return elapsed
    
    def show_table(self, data: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """Display data in a table format."""
        if not data:
            self.warning("No data to display")
            return
        
        # Create table
        table = Table(title=title, box=box.ROUNDED)
        
        # Add columns from first row
        columns = list(data[0].keys())
        for col in columns:
            table.add_column(col, style="cyan", no_wrap=False)
        
        # Add rows
        for row in data:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        
        self.console.print(table)
    
    def command_example(self, command: str, description: str) -> None:
        """Show a command example with description."""
        self.console.print(f"[dim]{description}:[/dim]")
        self.console.print(f"  [bold cyan]$ {command}[/bold cyan]\n")
    
    def suggest_command(self, attempted: str, suggestions: List[str]) -> None:
        """Suggest commands when user makes a typo."""
        self.error(f"Unknown command: '{attempted}'")
        
        if suggestions:
            self.console.print("\n[yellow]Did you mean one of these?[/yellow]")
            for suggestion in suggestions[:3]:  # Show top 3
                self.console.print(f"  [cyan]→ {suggestion}[/cyan]")
    
    @contextmanager
    def live_output(self, title: str = "Output"):
        """Create a live updating output panel."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
        )
        
        layout["header"].update(Panel(title, style="bold blue"))
        content = Text()
        layout["body"].update(Panel(content, border_style="cyan"))
        
        with Live(layout, console=self.console, refresh_per_second=4) as live:
            class LiveUpdater:
                def write(self, text: str):
                    content.append(text)
                    if len(content) > 1000:  # Limit size
                        content = Text(str(content)[-1000:])
                    layout["body"].update(Panel(content, border_style="cyan"))
                
                def clear(self):
                    content.clear()
            
            yield LiveUpdater()
    
    def show_help_context(self, command: str, options: List[tuple[str, str, str]]) -> None:
        """Show contextual help for a command."""
        help_panel = f"[bold cyan]{command}[/bold cyan]\n\n"
        
        if options:
            help_panel += "[yellow]Options:[/yellow]\n"
            for option, typ, desc in options:
                help_panel += f"  [green]{option}[/green] [{typ}]  {desc}\n"
        
        self.console.print(Panel(help_panel, title="Command Help", border_style="blue"))
    
    def eta_progress(self, items: List[Any], description: str = "Processing"):
        """Progress bar with ETA calculation."""
        total = len(items)
        start_time = time.time()
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]ETA:[/cyan] {task.fields[eta]}"),
            TextColumn("•"),
            TextColumn("[green]Speed:[/green] {task.fields[speed]}"),
            console=self.console
        ) as progress:
            task = progress.add_task(
                description,
                total=total,
                eta="calculating...",
                speed="0 items/s"
            )
            
            for i, item in enumerate(items):
                # Update ETA
                elapsed = time.time() - start_time
                if i > 0:
                    avg_time_per_item = elapsed / i
                    remaining = total - i
                    eta_seconds = avg_time_per_item * remaining
                    eta_str = str(timedelta(seconds=int(eta_seconds)))
                    speed = f"{i / elapsed:.1f} items/s"
                    
                    progress.update(task, 
                                    advance=1,
                                    eta=eta_str,
                                    speed=speed)
                else:
                    progress.update(task, advance=1)
                
                yield item
    
    def remediation_panel(self, error: str, steps: List[str]) -> None:
        """Show error remediation steps."""
        content = f"[red]Error:[/red] {error}\n\n"
        content += "[yellow]To fix this issue:[/yellow]\n\n"
        
        for i, step in enumerate(steps, 1):
            content += f"{i}. {step}\n"
        
        self.console.print(Panel(
            content,
            title="🔧 Troubleshooting",
            border_style="yellow"
        ))


# Convenience functions
feedback = UserFeedback()


def show_spinner(message: str):
    """Decorator to show a spinner during function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with console.status(f"[cyan]{message}[/cyan]...", spinner="dots"):
                result = func(*args, **kwargs)
            feedback.success(f"{message} complete!")
            return result
        return wrapper
    return decorator


def handle_errors(func):
    """Decorator to handle errors with user-friendly messages."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            feedback.warning("\nOperation cancelled by user")
            raise typer.Exit(130)
        except Exception as e:
            feedback.error(
                f"An unexpected error occurred: {str(e)}",
                suggestions=[
                    "Try running with --debug for more details",
                    "Check the logs at ~/.daglab/logs/",
                    "Report this issue: daglab feedback --error"
                ]
            )
            raise typer.Exit(1)
    return wrapper