"""
Utility functions for DagLab notebooks.

This module provides general utilities for asset selection, pattern expansion,
URL generation, error formatting, and data validation.
"""

import json
import re
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlencode, urljoin

import pandas as pd
from dagster import AssetKey
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.syntax import Syntax


# Rich console for pretty output
console = Console()


def parse_asset_selection(
    selection: Union[str, List[str]],
    available_assets: Optional[List[str]] = None
) -> List[AssetKey]:
    """
    Parse asset selection string into AssetKey objects.
    
    Supports:
    - Single asset: "my_asset"
    - Multiple assets: "asset1,asset2,asset3"
    - Wildcards: "my_*" or "*_model"
    - Groups: "models/*" or "*/silver"
    - Exclusions: "* -test_*"
    
    Args:
        selection: Asset selection string or list
        available_assets: List of available asset names for validation
        
    Returns:
        List of AssetKey objects
    """
    if isinstance(selection, list):
        # Already a list, just parse each item
        asset_keys = []
        for item in selection:
            if isinstance(item, AssetKey):
                asset_keys.append(item)
            else:
                asset_keys.extend(parse_asset_selection(item, available_assets))
        return asset_keys
    
    # Parse selection string
    parts = selection.split()
    includes = []
    excludes = []
    
    for part in parts:
        if part.startswith("-"):
            excludes.append(part[1:])
        else:
            includes.append(part)
    
    # Expand patterns
    selected_names = set()
    
    for pattern in includes:
        if available_assets:
            # Match against available assets
            matched = expand_pattern(pattern, available_assets)
            selected_names.update(matched)
        else:
            # No validation, just parse the pattern
            if "*" in pattern:
                # Can't expand without available assets
                raise ValueError(
                    f"Cannot expand wildcard '{pattern}' without available_assets list"
                )
            else:
                # Split by comma if multiple assets
                selected_names.update(p.strip() for p in pattern.split(","))
    
    # Apply exclusions
    for pattern in excludes:
        if available_assets:
            matched = expand_pattern(pattern, available_assets)
            selected_names.difference_update(matched)
    
    # Convert to AssetKey objects
    asset_keys = []
    for name in sorted(selected_names):
        # Handle nested keys (e.g., "models/my_model")
        if "/" in name:
            parts = name.split("/")
            asset_keys.append(AssetKey(parts))
        else:
            asset_keys.append(AssetKey([name]))
    
    return asset_keys


def expand_pattern(
    pattern: str,
    candidates: List[str]
) -> Set[str]:
    """
    Expand a pattern with wildcards to matching strings.
    
    Args:
        pattern: Pattern with optional wildcards (*)
        candidates: List of candidate strings
        
    Returns:
        Set of matching strings
    """
    # Convert pattern to regex
    # Escape special regex characters except *
    regex_pattern = re.escape(pattern).replace(r"\*", ".*")
    regex_pattern = f"^{regex_pattern}$"
    
    # Find matches
    matches = set()
    compiled_regex = re.compile(regex_pattern)
    
    for candidate in candidates:
        if compiled_regex.match(candidate):
            matches.add(candidate)
    
    return matches


def generate_dagster_url(
    base_url: str = "http://localhost:3000",
    path: str = "",
    **params
) -> str:
    """
    Generate URL for Dagster UI.
    
    Args:
        base_url: Base URL of Dagster instance
        path: URL path (e.g., "/instance/runs/abc123")
        **params: Query parameters
        
    Returns:
        Complete URL
    """
    url = urljoin(base_url, path)
    
    if params:
        # Filter out None values
        filtered_params = {k: v for k, v in params.items() if v is not None}
        if filtered_params:
            url += "?" + urlencode(filtered_params)
    
    return url


def format_error(
    error: Exception,
    include_traceback: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format an error for display with optional context.
    
    Args:
        error: The exception
        include_traceback: Whether to include full traceback
        context: Additional context information
        
    Returns:
        Formatted error string
    """
    lines = []
    
    # Error type and message
    lines.append(f"❌ {error.__class__.__name__}: {str(error)}")
    
    # Context information
    if context:
        lines.append("\n📋 Context:")
        for key, value in context.items():
            lines.append(f"  • {key}: {value}")
    
    # Traceback
    if include_traceback:
        lines.append("\n📍 Traceback:")
        tb_lines = traceback.format_tb(error.__traceback__)
        for line in tb_lines:
            lines.append(line.rstrip())
    
    return "\n".join(lines)


def pretty_print_error(
    error: Exception,
    title: str = "Error",
    context: Optional[Dict[str, Any]] = None
):
    """
    Pretty print an error using Rich console.
    
    Args:
        error: The exception
        title: Error title
        context: Additional context
    """
    console.print(f"\n[bold red]{title}[/bold red]")
    console.print(f"[red]{error.__class__.__name__}:[/red] {str(error)}")
    
    if context:
        console.print("\n[yellow]Context:[/yellow]")
        for key, value in context.items():
            console.print(f"  • {key}: [cyan]{value}[/cyan]")
    
    # Show relevant code if available
    tb = traceback.extract_tb(error.__traceback__)
    if tb:
        last_frame = tb[-1]
        console.print(f"\n[yellow]Location:[/yellow] {last_frame.filename}:{last_frame.lineno}")
        
        if last_frame.line:
            console.print("\n[yellow]Code:[/yellow]")
            syntax = Syntax(
                last_frame.line.strip(),
                "python",
                theme="monokai",
                line_numbers=True,
                start_line=last_frame.lineno
            )
            console.print(syntax)


def validate_data(
    data: Any,
    schema: Dict[str, Any],
    strict: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate data against a schema.
    
    Args:
        data: Data to validate
        schema: Validation schema
        strict: Whether to fail on extra fields
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    def validate_field(value: Any, field_schema: Dict[str, Any], path: str = ""):
        """Recursively validate a field."""
        
        # Check type
        if "type" in field_schema:
            expected_type = field_schema["type"]
            type_map = {
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "array": list,
                "object": dict
            }
            
            python_type = type_map.get(expected_type)
            if python_type and not isinstance(value, python_type):
                errors.append(
                    f"{path}: Expected type '{expected_type}', got '{type(value).__name__}'"
                )
                return
        
        # Check enum values
        if "enum" in field_schema and value not in field_schema["enum"]:
            errors.append(
                f"{path}: Value '{value}' not in allowed values: {field_schema['enum']}"
            )
        
        # Check string patterns
        if "pattern" in field_schema and isinstance(value, str):
            if not re.match(field_schema["pattern"], value):
                errors.append(
                    f"{path}: Value '{value}' doesn't match pattern '{field_schema['pattern']}'"
                )
        
        # Check numeric constraints
        if isinstance(value, (int, float)):
            if "minimum" in field_schema and value < field_schema["minimum"]:
                errors.append(
                    f"{path}: Value {value} is less than minimum {field_schema['minimum']}"
                )
            
            if "maximum" in field_schema and value > field_schema["maximum"]:
                errors.append(
                    f"{path}: Value {value} is greater than maximum {field_schema['maximum']}"
                )
        
        # Check array items
        if isinstance(value, list) and "items" in field_schema:
            for i, item in enumerate(value):
                validate_field(item, field_schema["items"], f"{path}[{i}]")
        
        # Check object properties
        if isinstance(value, dict) and "properties" in field_schema:
            schema_props = field_schema["properties"]
            
            # Check required fields
            if "required" in field_schema:
                for req_field in field_schema["required"]:
                    if req_field not in value:
                        errors.append(f"{path}: Missing required field '{req_field}'")
            
            # Validate each property
            for prop, prop_value in value.items():
                if prop in schema_props:
                    validate_field(
                        prop_value,
                        schema_props[prop],
                        f"{path}.{prop}" if path else prop
                    )
                elif strict:
                    errors.append(f"{path}: Unknown field '{prop}'")
    
    # Start validation
    validate_field(data, schema)
    
    return len(errors) == 0, errors


def create_asset_tree(
    assets: List[Dict[str, Any]],
    group_by: str = "prefix"
) -> Tree:
    """
    Create a tree visualization of assets.
    
    Args:
        assets: List of asset dictionaries
        group_by: How to group assets ('prefix', 'group', 'type')
        
    Returns:
        Rich Tree object
    """
    tree = Tree("📦 Assets")
    
    if group_by == "prefix":
        # Group by common prefix
        groups = defaultdict(list)
        for asset in assets:
            key = asset.get("key", "")
            if "/" in key:
                prefix = key.split("/")[0]
            else:
                prefix = "root"
            groups[prefix].append(asset)
        
        for prefix, group_assets in sorted(groups.items()):
            branch = tree.add(f"📁 {prefix}")
            for asset in sorted(group_assets, key=lambda a: a.get("key", "")):
                name = asset.get("key", "").split("/")[-1]
                branch.add(f"📄 {name}")
    
    elif group_by == "group":
        # Group by asset group
        groups = defaultdict(list)
        for asset in assets:
            group = asset.get("group", "ungrouped")
            groups[group].append(asset)
        
        for group, group_assets in sorted(groups.items()):
            branch = tree.add(f"📁 {group}")
            for asset in sorted(group_assets, key=lambda a: a.get("key", "")):
                branch.add(f"📄 {asset.get('key', '')}")
    
    return tree


def create_run_table(
    runs: List[Dict[str, Any]],
    max_rows: int = 10
) -> Table:
    """
    Create a table visualization of runs.
    
    Args:
        runs: List of run dictionaries
        max_rows: Maximum rows to display
        
    Returns:
        Rich Table object
    """
    table = Table(title="🏃 Recent Runs")
    
    # Add columns
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Job", style="magenta")
    table.add_column("Status", style="bold")
    table.add_column("Started", style="green")
    table.add_column("Duration", style="yellow")
    
    # Add rows
    for i, run in enumerate(runs[:max_rows]):
        run_id = run.get("run_id", "")[:8]  # Short ID
        job_name = run.get("job_name", "")
        status = run.get("status", "")
        
        # Format status with color
        if status == "SUCCESS":
            status_display = "[green]✓ SUCCESS[/green]"
        elif status == "FAILURE":
            status_display = "[red]✗ FAILURE[/red]"
        elif status in ["STARTED", "QUEUED"]:
            status_display = "[yellow]⏳ " + status + "[/yellow]"
        else:
            status_display = status
        
        # Calculate duration
        started = run.get("started_at", "")
        completed = run.get("completed_at", "")
        
        if started and completed:
            try:
                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(completed)
                duration = str(end_dt - start_dt).split(".")[0]  # Remove microseconds
            except:
                duration = "-"
        else:
            duration = "-"
        
        table.add_row(
            run_id,
            job_name,
            status_display,
            started.split("T")[0] if started else "-",
            duration
        )
    
    if len(runs) > max_rows:
        table.add_row(
            "...",
            f"({len(runs) - max_rows} more)",
            "",
            "",
            ""
        )
    
    return table


def format_run_config(
    config: Dict[str, Any],
    syntax_highlight: bool = True
) -> Union[str, Syntax]:
    """
    Format run configuration for display.
    
    Args:
        config: Run configuration dictionary
        syntax_highlight: Whether to return Rich Syntax object
        
    Returns:
        Formatted config string or Syntax object
    """
    formatted = json.dumps(config, indent=2, sort_keys=True)
    
    if syntax_highlight:
        return Syntax(formatted, "json", theme="monokai", line_numbers=True)
    else:
        return formatted


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    column_types: Optional[Dict[str, type]] = None,
    min_rows: int = 0,
    max_rows: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """
    Validate a pandas DataFrame.
    
    Args:
        df: DataFrame to validate
        required_columns: Required column names
        column_types: Expected column types
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check DataFrame type
    if not isinstance(df, pd.DataFrame):
        errors.append(f"Expected pandas DataFrame, got {type(df).__name__}")
        return False, errors
    
    # Check required columns
    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            errors.append(f"Missing required columns: {missing}")
    
    # Check column types
    if column_types:
        for col, expected_type in column_types.items():
            if col in df.columns:
                actual_type = df[col].dtype
                
                # Map pandas dtypes to Python types
                type_map = {
                    str: ["object", "string"],
                    int: ["int64", "int32", "int16", "int8"],
                    float: ["float64", "float32"],
                    bool: ["bool"]
                }
                
                valid_dtypes = type_map.get(expected_type, [])
                if str(actual_type) not in valid_dtypes:
                    errors.append(
                        f"Column '{col}' has type '{actual_type}', expected {expected_type.__name__}"
                    )
    
    # Check row count
    row_count = len(df)
    
    if row_count < min_rows:
        errors.append(f"DataFrame has {row_count} rows, minimum required is {min_rows}")
    
    if max_rows is not None and row_count > max_rows:
        errors.append(f"DataFrame has {row_count} rows, maximum allowed is {max_rows}")
    
    # Check for empty DataFrame
    if df.empty and min_rows > 0:
        errors.append("DataFrame is empty")
    
    return len(errors) == 0, errors


def safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float],
    default: Union[int, float] = 0
) -> Union[int, float]:
    """
    Safely divide two numbers with default for division by zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value if division by zero
        
    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def truncate_string(
    text: str,
    max_length: int = 80,
    suffix: str = "..."
) -> str:
    """
    Truncate a string to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def humanize_bytes(
    num_bytes: int,
    decimal_places: int = 2
) -> str:
    """
    Convert bytes to human readable format.
    
    Args:
        num_bytes: Number of bytes
        decimal_places: Decimal places in output
        
    Returns:
        Human readable string (e.g., "1.23 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.{decimal_places}f} {unit}"
        num_bytes /= 1024.0
    
    return f"{num_bytes:.{decimal_places}f} PB"


def humanize_duration(
    seconds: float,
    precision: str = "seconds"
) -> str:
    """
    Convert seconds to human readable duration.
    
    Args:
        seconds: Duration in seconds
        precision: Precision level ('seconds', 'minutes', 'hours')
        
    Returns:
        Human readable duration (e.g., "2h 15m 30s")
    """
    if seconds < 0:
        return "Invalid duration"
    
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    
    if days > 0:
        parts.append(f"{days}d")
    
    if hours > 0 or (days > 0 and precision != "hours"):
        parts.append(f"{hours}h")
    
    if precision != "hours":
        if minutes > 0 or (hours > 0 and precision != "minutes"):
            parts.append(f"{minutes}m")
        
        if precision == "seconds" and (secs > 0 or not parts):
            parts.append(f"{secs}s")
    
    return " ".join(parts) if parts else "0s"