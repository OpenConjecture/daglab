"""
Notebook-specific performance metrics for DagLab.

Provides detailed performance tracking for Jupyter notebook operations including
cell execution timing, memory usage, and optimization suggestions.
"""

import ast
import gc
import importlib
import json
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import psutil
import numpy as np
import pandas as pd
from IPython import get_ipython
from IPython.core.magic import register_line_magic, register_cell_magic

from .performance import PerformanceTracker, get_memory_usage


@dataclass
class CellMetrics:
    """Metrics for a single cell execution."""
    cell_id: str
    cell_type: str  # 'code' or 'markdown'
    execution_count: Optional[int]
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    cpu_percent: float
    variables_created: List[str]
    variables_modified: List[str]
    imports: List[str]
    functions_defined: List[str]
    classes_defined: List[str]
    errors: List[str]
    output_size: int


@dataclass
class VariableMetrics:
    """Metrics for tracking variables in notebook."""
    name: str
    type_name: str
    size_bytes: int
    shape: Optional[Tuple]
    created_time: float
    last_modified: float
    access_count: int


class NotebookPerformanceTracker:
    """
    Performance tracking specifically for Jupyter notebooks.
    
    Tracks cell execution, memory usage, variable sizes, and provides
    optimization suggestions.
    """
    
    def __init__(self, name: str = "notebook"):
        """
        Initialize notebook performance tracker.
        
        Args:
            name: Tracker name
        """
        self.name = name
        self.base_tracker = PerformanceTracker(name)
        self.cell_metrics: List[CellMetrics] = []
        self.variable_metrics: Dict[str, VariableMetrics] = {}
        self.import_times: Dict[str, float] = {}
        self.namespace_snapshot: Dict[str, Any] = {}
        self._ipython = get_ipython()
        
        # Register IPython magic commands if available
        if self._ipython:
            self._register_magics()
    
    def start_cell(self, cell_id: str, cell_type: str = "code",
                   execution_count: Optional[int] = None):
        """
        Start tracking a cell execution.
        
        Args:
            cell_id: Unique cell identifier
            cell_type: Type of cell ('code' or 'markdown')
            execution_count: Execution count for code cells
        """
        # Take namespace snapshot
        if self._ipython:
            self.namespace_snapshot = dict(self._ipython.user_ns)
        
        # Start base tracking
        self.base_tracker.start_operation(f"cell_{cell_id}", {
            "cell_type": cell_type,
            "execution_count": execution_count
        })
    
    def end_cell(self, cell_id: str, source_code: Optional[str] = None,
                 output_size: int = 0) -> CellMetrics:
        """
        End tracking a cell execution.
        
        Args:
            cell_id: Cell identifier
            source_code: Cell source code for analysis
            output_size: Size of cell output in bytes
            
        Returns:
            Cell execution metrics
        """
        # End base tracking
        self.base_tracker.end_operation(f"cell_{cell_id}")
        
        # Get the latest metric
        metric = self.base_tracker.metrics[-1]
        
        # Analyze code if provided
        variables_created = []
        variables_modified = []
        imports = []
        functions_defined = []
        classes_defined = []
        
        if source_code and self._ipython:
            analysis = self._analyze_code(source_code)
            imports = analysis["imports"]
            functions_defined = analysis["functions"]
            classes_defined = analysis["classes"]
            
            # Detect variable changes
            new_namespace = self._ipython.user_ns
            for name, value in new_namespace.items():
                if name.startswith('_'):
                    continue
                    
                if name not in self.namespace_snapshot:
                    variables_created.append(name)
                    # Track new variable
                    self._track_variable(name, value)
                elif id(value) != id(self.namespace_snapshot.get(name)):
                    variables_modified.append(name)
                    # Update variable metrics
                    self._track_variable(name, value)
        
        # Create cell metrics
        cell_metrics = CellMetrics(
            cell_id=cell_id,
            cell_type=metric.metadata.get("cell_type", "code"),
            execution_count=metric.metadata.get("execution_count"),
            start_time=metric.start_time,
            end_time=metric.end_time,
            duration=metric.duration,
            memory_before=metric.memory_mb - metric.memory_delta_mb,
            memory_after=metric.memory_mb,
            memory_delta=metric.memory_delta_mb,
            cpu_percent=metric.cpu_percent,
            variables_created=variables_created,
            variables_modified=variables_modified,
            imports=imports,
            functions_defined=functions_defined,
            classes_defined=classes_defined,
            errors=metric.errors,
            output_size=output_size
        )
        
        self.cell_metrics.append(cell_metrics)
        return cell_metrics
    
    def track_import(self, module_name: str) -> float:
        """
        Track import time for a module.
        
        Args:
            module_name: Module to import
            
        Returns:
            Import time in seconds
        """
        start_time = time.time()
        
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass
        
        import_time = time.time() - start_time
        self.import_times[module_name] = import_time
        
        return import_time
    
    def get_variable_report(self) -> pd.DataFrame:
        """
        Get report on all tracked variables.
        
        Returns:
            DataFrame with variable metrics
        """
        data = []
        
        for name, metrics in self.variable_metrics.items():
            data.append({
                "name": name,
                "type": metrics.type_name,
                "size_mb": metrics.size_bytes / 1024 / 1024,
                "shape": str(metrics.shape) if metrics.shape else "",
                "created": datetime.fromtimestamp(metrics.created_time).strftime("%H:%M:%S"),
                "modified": datetime.fromtimestamp(metrics.last_modified).strftime("%H:%M:%S"),
                "accesses": metrics.access_count
            })
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values("size_mb", ascending=False)
        
        return df
    
    def get_cell_report(self) -> pd.DataFrame:
        """
        Get report on all cell executions.
        
        Returns:
            DataFrame with cell metrics
        """
        data = []
        
        for metrics in self.cell_metrics:
            data.append({
                "cell_id": metrics.cell_id,
                "type": metrics.cell_type,
                "execution": metrics.execution_count,
                "duration": metrics.duration,
                "memory_delta": metrics.memory_delta,
                "cpu_percent": metrics.cpu_percent,
                "vars_created": len(metrics.variables_created),
                "vars_modified": len(metrics.variables_modified),
                "imports": len(metrics.imports),
                "errors": len(metrics.errors),
                "output_size": metrics.output_size
            })
        
        return pd.DataFrame(data)
    
    def get_import_report(self) -> pd.DataFrame:
        """
        Get report on module import times.
        
        Returns:
            DataFrame with import metrics
        """
        data = [
            {"module": module, "import_time": time_s}
            for module, time_s in self.import_times.items()
        ]
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values("import_time", ascending=False)
        
        return df
    
    def generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """
        Generate performance optimization suggestions.
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Analyze cell performance
        if self.cell_metrics:
            # Slow cells
            slow_cells = [
                m for m in self.cell_metrics
                if m.duration > 1.0  # More than 1 second
            ]
            
            if slow_cells:
                suggestions.append({
                    "category": "slow_cells",
                    "severity": "warning",
                    "message": f"Found {len(slow_cells)} slow cells (>1s execution time)",
                    "details": [
                        f"Cell {m.cell_id}: {m.duration:.2f}s"
                        for m in slow_cells[:5]
                    ],
                    "recommendation": "Consider optimizing these cells or breaking them into smaller chunks"
                })
            
            # Memory hungry cells
            memory_cells = [
                m for m in self.cell_metrics
                if m.memory_delta > 100  # More than 100MB
            ]
            
            if memory_cells:
                suggestions.append({
                    "category": "memory_usage",
                    "severity": "warning",
                    "message": f"Found {len(memory_cells)} cells with high memory usage (>100MB)",
                    "details": [
                        f"Cell {m.cell_id}: +{m.memory_delta:.1f}MB"
                        for m in memory_cells[:5]
                    ],
                    "recommendation": "Review data loading and processing in these cells"
                })
        
        # Analyze variables
        if self.variable_metrics:
            # Large variables
            large_vars = [
                (name, m.size_bytes / 1024 / 1024)
                for name, m in self.variable_metrics.items()
                if m.size_bytes > 100 * 1024 * 1024  # 100MB
            ]
            
            if large_vars:
                suggestions.append({
                    "category": "large_variables",
                    "severity": "info",
                    "message": f"Found {len(large_vars)} large variables (>100MB)",
                    "details": [
                        f"{name}: {size:.1f}MB"
                        for name, size in sorted(large_vars, key=lambda x: x[1], reverse=True)[:5]
                    ],
                    "recommendation": "Consider using more efficient data structures or clearing unused variables"
                })
            
            # Unused variables
            unused_vars = [
                name for name, m in self.variable_metrics.items()
                if m.access_count == 0 and m.size_bytes > 1024 * 1024  # 1MB
            ]
            
            if unused_vars:
                suggestions.append({
                    "category": "unused_variables",
                    "severity": "info",
                    "message": f"Found {len(unused_vars)} unused variables (>1MB)",
                    "details": unused_vars[:10],
                    "recommendation": "Consider deleting unused variables to free memory"
                })
        
        # Analyze imports
        if self.import_times:
            # Slow imports
            slow_imports = [
                (module, time_s)
                for module, time_s in self.import_times.items()
                if time_s > 0.5  # More than 0.5 seconds
            ]
            
            if slow_imports:
                suggestions.append({
                    "category": "slow_imports",
                    "severity": "info",
                    "message": f"Found {len(slow_imports)} slow imports (>0.5s)",
                    "details": [
                        f"{module}: {time_s:.2f}s"
                        for module, time_s in sorted(slow_imports, key=lambda x: x[1], reverse=True)[:5]
                    ],
                    "recommendation": "Consider lazy imports or optimizing import order"
                })
        
        # General recommendations
        total_memory = sum(m.memory_delta for m in self.cell_metrics)
        if total_memory > 1000:  # More than 1GB total
            suggestions.append({
                "category": "total_memory",
                "severity": "warning",
                "message": f"High total memory usage: {total_memory:.1f}MB",
                "details": [],
                "recommendation": "Consider running garbage collection or restarting kernel"
            })
        
        return suggestions
    
    def generate_report(self, output_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate comprehensive performance report.
        
        Args:
            output_path: Optional path to save report
            
        Returns:
            HTML report content
        """
        # Generate report sections
        cell_df = self.get_cell_report()
        var_df = self.get_variable_report()
        import_df = self.get_import_report()
        suggestions = self.generate_optimization_suggestions()
        
        # Create HTML report
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Notebook Performance Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }}
        
        h1, h2 {{
            color: #333;
        }}
        
        .summary {{
            background: #f0f0f0;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        
        th, td {{
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        
        .suggestion {{
            background: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
        }}
        
        .suggestion.warning {{
            background: #f8d7da;
            border-color: #f5c6cb;
        }}
    </style>
</head>
<body>
    <h1>Notebook Performance Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Cells Executed: {len(self.cell_metrics)}</p>
        <p>Total Execution Time: {sum(m.duration for m in self.cell_metrics):.2f}s</p>
        <p>Total Memory Change: {sum(m.memory_delta for m in self.cell_metrics):.1f}MB</p>
        <p>Variables Tracked: {len(self.variable_metrics)}</p>
    </div>
    
    <h2>Cell Execution Metrics</h2>
    {cell_df.to_html(index=False) if not cell_df.empty else "<p>No cell metrics available</p>"}
    
    <h2>Variable Usage</h2>
    {var_df.to_html(index=False) if not var_df.empty else "<p>No variable metrics available</p>"}
    
    <h2>Import Times</h2>
    {import_df.to_html(index=False) if not import_df.empty else "<p>No import metrics available</p>"}
    
    <h2>Optimization Suggestions</h2>
"""
        
        # Add suggestions
        if suggestions:
            for suggestion in suggestions:
                severity_class = "warning" if suggestion["severity"] == "warning" else ""
                html += f"""
    <div class="suggestion {severity_class}">
        <strong>{suggestion['message']}</strong>
        <p>{suggestion['recommendation']}</p>
"""
                if suggestion['details']:
                    html += "<ul>"
                    for detail in suggestion['details']:
                        html += f"<li>{detail}</li>"
                    html += "</ul>"
                html += "</div>"
        else:
            html += "<p>No optimization suggestions at this time.</p>"
        
        html += """
</body>
</html>
"""
        
        # Save if path provided
        if output_path:
            path = Path(output_path)
            with open(path, "w") as f:
                f.write(html)
        
        return html
    
    def _analyze_code(self, source_code: str) -> Dict[str, List[str]]:
        """Analyze source code for imports, functions, and classes."""
        result = {
            "imports": [],
            "functions": [],
            "classes": []
        }
        
        try:
            tree = ast.parse(source_code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        result["imports"].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.FunctionDef):
                    result["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append(node.name)
        except:
            pass
        
        return result
    
    def _track_variable(self, name: str, value: Any):
        """Track a variable's metrics."""
        # Calculate size
        size_bytes = sys.getsizeof(value)
        
        # Get shape for arrays
        shape = None
        if hasattr(value, 'shape'):
            shape = value.shape
        elif isinstance(value, (list, tuple, dict)):
            shape = (len(value),)
        
        # Update or create metrics
        if name in self.variable_metrics:
            metrics = self.variable_metrics[name]
            metrics.size_bytes = size_bytes
            metrics.shape = shape
            metrics.last_modified = time.time()
            metrics.access_count += 1
        else:
            self.variable_metrics[name] = VariableMetrics(
                name=name,
                type_name=type(value).__name__,
                size_bytes=size_bytes,
                shape=shape,
                created_time=time.time(),
                last_modified=time.time(),
                access_count=0
            )
    
    def _register_magics(self):
        """Register IPython magic commands."""
        
        @register_line_magic
        def track_cell(line):
            """Track the next cell execution."""
            cell_id = line.strip() or f"cell_{int(time.time())}"
            self.start_cell(cell_id)
            print(f"Tracking cell: {cell_id}")
        
        @register_line_magic
        def show_performance(line):
            """Show performance summary."""
            print("\n=== Notebook Performance Summary ===")
            print(f"Total cells executed: {len(self.cell_metrics)}")
            print(f"Total execution time: {sum(m.duration for m in self.cell_metrics):.2f}s")
            print(f"Total memory change: {sum(m.memory_delta for m in self.cell_metrics):.1f}MB")
            print(f"\nSlowest cells:")
            
            sorted_cells = sorted(self.cell_metrics, key=lambda x: x.duration, reverse=True)
            for cell in sorted_cells[:5]:
                print(f"  {cell.cell_id}: {cell.duration:.2f}s")
        
        @register_line_magic
        def clear_performance(line):
            """Clear performance tracking data."""
            self.cell_metrics.clear()
            self.variable_metrics.clear()
            self.import_times.clear()
            print("Performance tracking data cleared.")


# Convenience functions
def track_notebook_performance(name: str = "notebook") -> NotebookPerformanceTracker:
    """
    Create and return a notebook performance tracker.
    
    Args:
        name: Tracker name
        
    Returns:
        NotebookPerformanceTracker instance
    """
    return NotebookPerformanceTracker(name)


def auto_track_cells():
    """
    Automatically track all cell executions in the current notebook.
    
    This function patches IPython to track all cell executions automatically.
    """
    tracker = NotebookPerformanceTracker("auto")
    ipython = get_ipython()
    
    if not ipython:
        raise RuntimeError("Not running in IPython/Jupyter environment")
    
    # Patch execution
    original_run_cell = ipython.run_cell
    
    def tracked_run_cell(raw_cell, store_history=False, silent=False, shell_futures=None):
        cell_id = f"auto_{int(time.time() * 1000)}"
        
        # Start tracking
        tracker.start_cell(cell_id, execution_count=ipython.execution_count)
        
        # Run cell
        result = original_run_cell(raw_cell, store_history, silent, shell_futures)
        
        # End tracking
        output_size = len(str(result.result)) if result.result else 0
        tracker.end_cell(cell_id, raw_cell, output_size)
        
        return result
    
    ipython.run_cell = tracked_run_cell
    
    print("Automatic cell tracking enabled.")
    return tracker