"""
Performance tracking and monitoring for DagLab notebooks.

This module provides utilities for tracking execution performance,
memory usage, and resource utilization.
"""

import gc
import json
import sys
import time
import threading
import warnings
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

import psutil
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
from scipy import stats


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    memory_delta_mb: float
    io_read_mb: float
    io_write_mb: float
    errors: List[str]
    metadata: Dict[str, Any]


class PerformanceTracker:
    """
    Performance tracking for Dagster operations in notebooks.
    
    Tracks CPU, memory, I/O, and custom metrics with visualization support.
    """
    
    def __init__(self, name: str = "default", enable_background_monitoring: bool = False):
        """
        Initialize performance tracker.
        
        Args:
            name: Tracker name for identification
            enable_background_monitoring: Enable continuous background monitoring
        """
        self.name = name
        self.metrics: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.process = psutil.Process()
        self._start_io_counters = None
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.anomaly_thresholds: Dict[str, float] = {
            "duration": 3.0,  # 3 standard deviations
            "memory": 3.0,
            "cpu": 3.0
        }
        
        # Background monitoring
        self.enable_background_monitoring = enable_background_monitoring
        self._monitor_thread = None
        self._monitor_stop_event = threading.Event()
        self._background_metrics = deque(maxlen=1000)
        
        if enable_background_monitoring:
            self._start_background_monitoring()
        
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Start tracking an operation.
        
        Args:
            operation_name: Name of the operation
            metadata: Additional metadata to track
        """
        # Collect starting metrics
        mem_info = self.process.memory_info()
        io_counters = self.process.io_counters()
        
        self.active_operations[operation_name] = {
            "start_time": time.time(),
            "start_memory": mem_info.rss / 1024 / 1024,  # MB
            "start_io_read": io_counters.read_bytes / 1024 / 1024,  # MB
            "start_io_write": io_counters.write_bytes / 1024 / 1024,  # MB
            "cpu_percent_samples": [],
            "metadata": metadata or {},
            "errors": []
        }
        
        # Start CPU monitoring in background
        self._start_cpu_monitoring(operation_name)
    
    def end_operation(self, operation_name: str, success: bool = True, error: Optional[str] = None):
        """
        End tracking an operation.
        
        Args:
            operation_name: Name of the operation
            success: Whether operation succeeded
            error: Error message if failed
        """
        if operation_name not in self.active_operations:
            return
        
        op_data = self.active_operations[operation_name]
        end_time = time.time()
        
        # Collect ending metrics
        mem_info = self.process.memory_info()
        io_counters = self.process.io_counters()
        
        # Calculate metrics
        duration = end_time - op_data["start_time"]
        memory_delta = (mem_info.rss / 1024 / 1024) - op_data["start_memory"]
        io_read_delta = (io_counters.read_bytes / 1024 / 1024) - op_data["start_io_read"]
        io_write_delta = (io_counters.write_bytes / 1024 / 1024) - op_data["start_io_write"]
        
        # Average CPU usage
        cpu_samples = op_data["cpu_percent_samples"]
        avg_cpu = np.mean(cpu_samples) if cpu_samples else 0.0
        
        # Add error if provided
        if error:
            op_data["errors"].append(error)
        
        # Create metrics object
        metrics = PerformanceMetrics(
            operation=operation_name,
            start_time=op_data["start_time"],
            end_time=end_time,
            duration=duration,
            cpu_percent=avg_cpu,
            memory_mb=mem_info.rss / 1024 / 1024,
            memory_percent=self.process.memory_percent(),
            memory_delta_mb=memory_delta,
            io_read_mb=io_read_delta,
            io_write_mb=io_write_delta,
            errors=op_data["errors"],
            metadata={**op_data["metadata"], "success": success}
        )
        
        self.metrics.append(metrics)
        del self.active_operations[operation_name]
    
    @contextmanager
    def track(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracking an operation.
        
        Args:
            operation_name: Name of the operation
            metadata: Additional metadata
            
        Example:
            with tracker.track("data_processing"):
                # Your code here
                pass
        """
        self.start_operation(operation_name, metadata)
        success = True
        error = None
        
        try:
            yield self
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            self.end_operation(operation_name, success, error)
    
    def get_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary.
        
        Args:
            operation_name: Filter by operation name
            
        Returns:
            Summary statistics
        """
        # Filter metrics
        metrics = self.metrics
        if operation_name:
            metrics = [m for m in metrics if m.operation == operation_name]
        
        if not metrics:
            return {"message": "No metrics recorded"}
        
        # Calculate summary statistics
        durations = [m.duration for m in metrics]
        cpu_usage = [m.cpu_percent for m in metrics]
        memory_usage = [m.memory_mb for m in metrics]
        memory_deltas = [m.memory_delta_mb for m in metrics]
        io_reads = [m.io_read_mb for m in metrics]
        io_writes = [m.io_write_mb for m in metrics]
        
        return {
            "operation_count": len(metrics),
            "total_duration": sum(durations),
            "duration": {
                "mean": np.mean(durations),
                "std": np.std(durations),
                "min": min(durations),
                "max": max(durations)
            },
            "cpu_percent": {
                "mean": np.mean(cpu_usage),
                "std": np.std(cpu_usage),
                "max": max(cpu_usage)
            },
            "memory_mb": {
                "mean": np.mean(memory_usage),
                "max": max(memory_usage),
                "total_delta": sum(memory_deltas)
            },
            "io_mb": {
                "total_read": sum(io_reads),
                "total_write": sum(io_writes)
            },
            "error_count": sum(len(m.errors) for m in metrics),
            "success_rate": sum(1 for m in metrics if m.metadata.get("success", True)) / len(metrics)
        }
    
    def get_operation_comparison(self) -> Dict[str, Dict[str, Any]]:
        """
        Compare performance across different operations.
        
        Returns:
            Dict mapping operation names to their statistics
        """
        comparison = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "avg_duration": 0,
            "avg_cpu": 0,
            "avg_memory": 0,
            "total_io_read": 0,
            "total_io_write": 0
        })
        
        for metric in self.metrics:
            op_stats = comparison[metric.operation]
            op_stats["count"] += 1
            op_stats["total_duration"] += metric.duration
            op_stats["avg_duration"] = op_stats["total_duration"] / op_stats["count"]
            op_stats["avg_cpu"] = (op_stats["avg_cpu"] * (op_stats["count"] - 1) + metric.cpu_percent) / op_stats["count"]
            op_stats["avg_memory"] = (op_stats["avg_memory"] * (op_stats["count"] - 1) + metric.memory_mb) / op_stats["count"]
            op_stats["total_io_read"] += metric.io_read_mb
            op_stats["total_io_write"] += metric.io_write_mb
        
        return dict(comparison)
    
    def visualize(
        self,
        metric_type: str = "duration",
        operation_filter: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None
    ) -> Figure:
        """
        Visualize performance metrics.
        
        Args:
            metric_type: Type of metric to visualize ('duration', 'memory', 'cpu', 'io', 'timeline')
            operation_filter: Filter by operation name
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        # Filter metrics
        metrics = self.metrics
        if operation_filter:
            metrics = [m for m in metrics if m.operation == operation_filter]
        
        if not metrics:
            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            ax.text(0.5, 0.5, "No metrics to display", ha='center', va='center')
            return fig
        
        # Create appropriate visualization
        if metric_type == "duration":
            fig = self._plot_durations(metrics)
        elif metric_type == "memory":
            fig = self._plot_memory(metrics)
        elif metric_type == "cpu":
            fig = self._plot_cpu(metrics)
        elif metric_type == "io":
            fig = self._plot_io(metrics)
        elif metric_type == "timeline":
            fig = self._plot_timeline(metrics)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")
        
        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def export(self, file_path: Union[str, Path], format: str = "json"):
        """
        Export metrics to file.
        
        Args:
            file_path: Output file path
            format: Export format ('json', 'csv', 'prometheus')
        """
        path = Path(file_path)
        
        if format == "json":
            data = {
                "tracker": self.name,
                "timestamp": datetime.now().isoformat(),
                "summary": self.get_summary(),
                "metrics": [asdict(m) for m in self.metrics],
                "baselines": self.baselines,
                "anomalies": self.detect_anomalies()
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        
        elif format == "csv":
            import csv
            
            with open(path, "w", newline="") as f:
                if self.metrics:
                    writer = csv.DictWriter(f, fieldnames=asdict(self.metrics[0]).keys())
                    writer.writeheader()
                    for metric in self.metrics:
                        writer.writerow(asdict(metric))
        
        elif format == "prometheus":
            self._export_prometheus(path)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def reset(self):
        """Reset all tracked metrics."""
        self.metrics.clear()
        self.active_operations.clear()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_background_monitoring()
    
    def _start_cpu_monitoring(self, operation_name: str):
        """Start CPU usage monitoring for an operation."""
        # Note: In a real implementation, this would start a background thread
        # For notebook usage, we'll sample CPU when possible
        if operation_name in self.active_operations:
            try:
                cpu_percent = self.process.cpu_percent(interval=0.1)
                self.active_operations[operation_name]["cpu_percent_samples"].append(cpu_percent)
            except:
                pass
    
    def _plot_durations(self, metrics: List[PerformanceMetrics]) -> Figure:
        """Plot operation durations."""
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        # Group by operation
        op_durations = defaultdict(list)
        for m in metrics:
            op_durations[m.operation].append(m.duration)
        
        # Create box plot
        labels = list(op_durations.keys())
        data = [op_durations[label] for label in labels]
        
        ax.boxplot(data, labels=labels)
        ax.set_ylabel("Duration (seconds)")
        ax.set_title("Operation Duration Distribution")
        plt.xticks(rotation=45, ha='right')
        
        return fig
    
    def _plot_memory(self, metrics: List[PerformanceMetrics]) -> Figure:
        """Plot memory usage over time."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Sort by time
        sorted_metrics = sorted(metrics, key=lambda m: m.start_time)
        
        # Extract data
        times = [m.start_time for m in sorted_metrics]
        memory_usage = [m.memory_mb for m in sorted_metrics]
        memory_deltas = [m.memory_delta_mb for m in sorted_metrics]
        
        # Plot absolute memory
        ax1.plot(times, memory_usage, marker='o', label='Memory Usage')
        ax1.set_ylabel("Memory (MB)")
        ax1.set_title("Memory Usage Over Time")
        ax1.grid(True, alpha=0.3)
        
        # Plot memory deltas
        colors = ['green' if d < 0 else 'red' for d in memory_deltas]
        ax2.bar(range(len(memory_deltas)), memory_deltas, color=colors)
        ax2.set_ylabel("Memory Delta (MB)")
        ax2.set_xlabel("Operation Index")
        ax2.set_title("Memory Changes per Operation")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _plot_cpu(self, metrics: List[PerformanceMetrics]) -> Figure:
        """Plot CPU usage."""
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        # Group by operation
        op_cpu = defaultdict(list)
        for m in metrics:
            op_cpu[m.operation].append(m.cpu_percent)
        
        # Create bar plot of average CPU usage
        operations = list(op_cpu.keys())
        avg_cpu = [np.mean(op_cpu[op]) for op in operations]
        
        bars = ax.bar(operations, avg_cpu)
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title("CPU Usage by Operation")
        plt.xticks(rotation=45, ha='right')
        
        # Color bars based on usage level
        for bar, cpu in zip(bars, avg_cpu):
            if cpu > 80:
                bar.set_color('red')
            elif cpu > 50:
                bar.set_color('orange')
            else:
                bar.set_color('green')
        
        return fig
    
    def _plot_io(self, metrics: List[PerformanceMetrics]) -> Figure:
        """Plot I/O operations."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Group by operation
        op_io = defaultdict(lambda: {"read": 0, "write": 0})
        for m in metrics:
            op_io[m.operation]["read"] += m.io_read_mb
            op_io[m.operation]["write"] += m.io_write_mb
        
        operations = list(op_io.keys())
        reads = [op_io[op]["read"] for op in operations]
        writes = [op_io[op]["write"] for op in operations]
        
        # Plot reads
        ax1.bar(operations, reads, color='blue', alpha=0.7)
        ax1.set_ylabel("I/O Read (MB)")
        ax1.set_title("I/O Read by Operation")
        ax1.tick_params(axis='x', rotation=45)
        
        # Plot writes
        ax2.bar(operations, writes, color='green', alpha=0.7)
        ax2.set_ylabel("I/O Write (MB)")
        ax2.set_title("I/O Write by Operation")
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        return fig
    
    def _plot_timeline(self, metrics: List[PerformanceMetrics]) -> Figure:
        """Plot operation timeline."""
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Sort by start time
        sorted_metrics = sorted(metrics, key=lambda m: m.start_time)
        
        # Assign y-positions for operations
        operation_types = list(set(m.operation for m in sorted_metrics))
        y_positions = {op: i for i, op in enumerate(operation_types)}
        
        # Plot timeline bars
        for metric in sorted_metrics:
            y = y_positions[metric.operation]
            width = metric.duration
            color = 'green' if metric.metadata.get("success", True) else 'red'
            
            ax.barh(y, width, left=metric.start_time, height=0.8, 
                   color=color, alpha=0.7, edgecolor='black')
        
        # Set labels
        ax.set_yticks(range(len(operation_types)))
        ax.set_yticklabels(operation_types)
        ax.set_xlabel("Time (seconds from start)")
        ax.set_title("Operation Timeline")
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def set_baseline(self, operation_name: str, run_multiple: bool = True):
        """
        Set performance baseline for an operation.
        
        Args:
            operation_name: Operation to baseline
            run_multiple: Run operation multiple times for stable baseline
        """
        operation_metrics = [m for m in self.metrics if m.operation == operation_name]
        
        if not operation_metrics:
            raise ValueError(f"No metrics found for operation: {operation_name}")
        
        # Calculate baseline statistics
        durations = [m.duration for m in operation_metrics]
        cpu_usage = [m.cpu_percent for m in operation_metrics]
        memory_usage = [m.memory_mb for m in operation_metrics]
        
        self.baselines[operation_name] = {
            "duration_mean": np.mean(durations),
            "duration_std": np.std(durations),
            "cpu_mean": np.mean(cpu_usage),
            "cpu_std": np.std(cpu_usage),
            "memory_mean": np.mean(memory_usage),
            "memory_std": np.std(memory_usage),
            "sample_size": len(operation_metrics)
        }
    
    def detect_anomalies(self, operation_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect performance anomalies based on baselines.
        
        Args:
            operation_name: Filter by operation
            
        Returns:
            List of anomalies detected
        """
        anomalies = []
        
        for metric in self.metrics:
            if operation_name and metric.operation != operation_name:
                continue
                
            baseline = self.baselines.get(metric.operation)
            if not baseline:
                continue
            
            # Check for anomalies
            anomaly_info = {
                "operation": metric.operation,
                "timestamp": metric.start_time,
                "anomalies": []
            }
            
            # Duration anomaly
            if baseline["duration_std"] > 0:
                z_score = (metric.duration - baseline["duration_mean"]) / baseline["duration_std"]
                if abs(z_score) > self.anomaly_thresholds["duration"]:
                    anomaly_info["anomalies"].append({
                        "type": "duration",
                        "z_score": z_score,
                        "value": metric.duration,
                        "baseline_mean": baseline["duration_mean"]
                    })
            
            # CPU anomaly
            if baseline["cpu_std"] > 0:
                z_score = (metric.cpu_percent - baseline["cpu_mean"]) / baseline["cpu_std"]
                if abs(z_score) > self.anomaly_thresholds["cpu"]:
                    anomaly_info["anomalies"].append({
                        "type": "cpu",
                        "z_score": z_score,
                        "value": metric.cpu_percent,
                        "baseline_mean": baseline["cpu_mean"]
                    })
            
            # Memory anomaly
            if baseline["memory_std"] > 0:
                z_score = (metric.memory_mb - baseline["memory_mean"]) / baseline["memory_std"]
                if abs(z_score) > self.anomaly_thresholds["memory"]:
                    anomaly_info["anomalies"].append({
                        "type": "memory",
                        "z_score": z_score,
                        "value": metric.memory_mb,
                        "baseline_mean": baseline["memory_mean"]
                    })
            
            if anomaly_info["anomalies"]:
                anomalies.append(anomaly_info)
        
        return anomalies
    
    def compare_runs(self, run_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare performance between different runs.
        
        Args:
            run_ids: List of run IDs to compare (uses metadata["run_id"])
            
        Returns:
            Comparison statistics
        """
        if not run_ids:
            # Get all unique run IDs
            run_ids = list(set(m.metadata.get("run_id", "default") for m in self.metrics))
        
        comparison = {}
        
        for run_id in run_ids:
            run_metrics = [m for m in self.metrics if m.metadata.get("run_id", "default") == run_id]
            if not run_metrics:
                continue
            
            comparison[run_id] = {
                "operation_count": len(run_metrics),
                "total_duration": sum(m.duration for m in run_metrics),
                "avg_duration": np.mean([m.duration for m in run_metrics]),
                "avg_cpu": np.mean([m.cpu_percent for m in run_metrics]),
                "avg_memory": np.mean([m.memory_mb for m in run_metrics]),
                "total_io_read": sum(m.io_read_mb for m in run_metrics),
                "total_io_write": sum(m.io_write_mb for m in run_metrics),
                "error_count": sum(len(m.errors) for m in run_metrics)
            }
        
        # Add relative comparisons
        if len(comparison) > 1:
            baseline_id = run_ids[0]
            baseline = comparison[baseline_id]
            
            for run_id in run_ids[1:]:
                if run_id not in comparison:
                    continue
                
                run_data = comparison[run_id]
                run_data["relative_to_baseline"] = {
                    "duration_change": (run_data["avg_duration"] - baseline["avg_duration"]) / baseline["avg_duration"] * 100,
                    "cpu_change": (run_data["avg_cpu"] - baseline["avg_cpu"]) / baseline["avg_cpu"] * 100 if baseline["avg_cpu"] > 0 else 0,
                    "memory_change": (run_data["avg_memory"] - baseline["avg_memory"]) / baseline["avg_memory"] * 100
                }
        
        return comparison
    
    def _export_prometheus(self, file_path: Path):
        """Export metrics in Prometheus format."""
        with open(file_path, "w") as f:
            # Write metrics in Prometheus format
            timestamp = int(time.time() * 1000)
            
            for metric in self.metrics:
                labels = f'operation="{metric.operation}",tracker="{self.name}"'
                
                f.write(f'daglab_operation_duration_seconds{{{labels}}} {metric.duration} {timestamp}\n')
                f.write(f'daglab_operation_cpu_percent{{{labels}}} {metric.cpu_percent} {timestamp}\n')
                f.write(f'daglab_operation_memory_bytes{{{labels}}} {metric.memory_mb * 1024 * 1024} {timestamp}\n')
                f.write(f'daglab_operation_io_read_bytes{{{labels}}} {metric.io_read_mb * 1024 * 1024} {timestamp}\n')
                f.write(f'daglab_operation_io_write_bytes{{{labels}}} {metric.io_write_mb * 1024 * 1024} {timestamp}\n')
                f.write(f'daglab_operation_errors_total{{{labels}}} {len(metric.errors)} {timestamp}\n')
    
    def _start_background_monitoring(self):
        """Start background resource monitoring."""
        self._monitor_stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._background_monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def _stop_background_monitoring(self):
        """Stop background monitoring."""
        self._monitor_stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _background_monitor_loop(self):
        """Background monitoring loop."""
        while not self._monitor_stop_event.is_set():
            try:
                # Collect metrics
                cpu = self.process.cpu_percent(interval=0.1)
                mem_info = self.process.memory_info()
                io_counters = self.process.io_counters()
                
                metric = {
                    "timestamp": time.time(),
                    "cpu_percent": cpu,
                    "memory_mb": mem_info.rss / 1024 / 1024,
                    "memory_percent": self.process.memory_percent(),
                    "io_read_bytes": io_counters.read_bytes,
                    "io_write_bytes": io_counters.write_bytes
                }
                
                self._background_metrics.append(metric)
                
            except Exception:
                pass
            
            time.sleep(1)
    
    def get_background_metrics(self, last_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get background monitoring metrics.
        
        Args:
            last_seconds: Get metrics from last N seconds
            
        Returns:
            List of background metrics
        """
        if not self._background_metrics:
            return []
        
        metrics = list(self._background_metrics)
        
        if last_seconds:
            cutoff = time.time() - last_seconds
            metrics = [m for m in metrics if m["timestamp"] > cutoff]
        
        return metrics


# Utility functions for memory monitoring
def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage statistics.
    
    Returns:
        Dict with memory statistics in MB
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    
    return {
        "rss": mem_info.rss / 1024 / 1024,  # Resident Set Size
        "vms": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        "percent": process.memory_percent(),
        "available": psutil.virtual_memory().available / 1024 / 1024
    }


def monitor_resource_usage(duration: int = 60, interval: float = 1.0) -> Dict[str, List[float]]:
    """
    Monitor resource usage over time.
    
    Args:
        duration: Monitoring duration in seconds
        interval: Sampling interval in seconds
        
    Returns:
        Dict with time series of resource metrics
    """
    process = psutil.Process()
    
    metrics = {
        "timestamps": [],
        "cpu_percent": [],
        "memory_mb": [],
        "memory_percent": [],
        "io_read_mb": [],
        "io_write_mb": []
    }
    
    start_time = time.time()
    last_io = process.io_counters()
    
    while time.time() - start_time < duration:
        current_time = time.time() - start_time
        
        # CPU usage
        cpu = process.cpu_percent(interval=interval)
        
        # Memory usage
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        mem_percent = process.memory_percent()
        
        # I/O usage
        current_io = process.io_counters()
        io_read_delta = (current_io.read_bytes - last_io.read_bytes) / 1024 / 1024
        io_write_delta = (current_io.write_bytes - last_io.write_bytes) / 1024 / 1024
        last_io = current_io
        
        # Store metrics
        metrics["timestamps"].append(current_time)
        metrics["cpu_percent"].append(cpu)
        metrics["memory_mb"].append(mem_mb)
        metrics["memory_percent"].append(mem_percent)
        metrics["io_read_mb"].append(io_read_delta)
        metrics["io_write_mb"].append(io_write_delta)
        
        time.sleep(interval)
    
    return metrics


def profile_memory_usage(func):
    """
    Decorator to profile memory usage of a function.
    
    Example:
        @profile_memory_usage
        def my_function():
            # Your code here
            pass
    """
    def wrapper(*args, **kwargs):
        # Force garbage collection
        gc.collect()
        
        # Get starting memory
        start_mem = get_memory_usage()
        
        # Run function
        result = func(*args, **kwargs)
        
        # Get ending memory
        gc.collect()
        end_mem = get_memory_usage()
        
        # Calculate deltas
        delta = {
            "rss_delta_mb": end_mem["rss"] - start_mem["rss"],
            "vms_delta_mb": end_mem["vms"] - start_mem["vms"],
            "final_rss_mb": end_mem["rss"],
            "final_percent": end_mem["percent"]
        }
        
        print(f"Memory usage for {func.__name__}:")
        print(f"  RSS Delta: {delta['rss_delta_mb']:.2f} MB")
        print(f"  Final RSS: {delta['final_rss_mb']:.2f} MB ({delta['final_percent']:.1f}%)")
        
        return result
    
    return wrapper


class MetricsCollector:
    """
    System-wide metrics collection across multiple trackers.
    
    Aggregates metrics from multiple PerformanceTracker instances and provides
    system-wide performance insights.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.trackers: Dict[str, PerformanceTracker] = {}
        self.system_metrics: List[Dict[str, Any]] = []
        self._collect_thread = None
        self._stop_event = threading.Event()
        
    def register_tracker(self, tracker: PerformanceTracker):
        """
        Register a performance tracker.
        
        Args:
            tracker: PerformanceTracker instance
        """
        self.trackers[tracker.name] = tracker
    
    def unregister_tracker(self, name: str):
        """
        Unregister a tracker.
        
        Args:
            name: Tracker name
        """
        self.trackers.pop(name, None)
    
    def collect_system_metrics(self):
        """Collect system-wide metrics."""
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        return {
            "timestamp": time.time(),
            "cpu": {
                "count": cpu_count,
                "percent": psutil.cpu_percent(interval=1, percpu=False),
                "percpu": psutil.cpu_percent(interval=1, percpu=True),
                "frequency": cpu_freq.current if cpu_freq else 0,
                "frequency_min": cpu_freq.min if cpu_freq else 0,
                "frequency_max": cpu_freq.max if cpu_freq else 0
            },
            "memory": {
                "total": memory.total / 1024 / 1024 / 1024,  # GB
                "available": memory.available / 1024 / 1024 / 1024,
                "percent": memory.percent,
                "used": memory.used / 1024 / 1024 / 1024,
                "free": memory.free / 1024 / 1024 / 1024
            },
            "disk": {
                "total": disk.total / 1024 / 1024 / 1024,  # GB
                "used": disk.used / 1024 / 1024 / 1024,
                "free": disk.free / 1024 / 1024 / 1024,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent / 1024 / 1024,  # MB
                "bytes_recv": net_io.bytes_recv / 1024 / 1024,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    
    def start_collection(self, interval: float = 5.0):
        """
        Start periodic system metrics collection.
        
        Args:
            interval: Collection interval in seconds
        """
        self._stop_event.clear()
        self._collect_thread = threading.Thread(
            target=self._collection_loop,
            args=(interval,)
        )
        self._collect_thread.daemon = True
        self._collect_thread.start()
    
    def stop_collection(self):
        """Stop metrics collection."""
        self._stop_event.set()
        if self._collect_thread:
            self._collect_thread.join(timeout=5)
    
    def _collection_loop(self, interval: float):
        """Collection loop."""
        while not self._stop_event.is_set():
            try:
                metrics = self.collect_system_metrics()
                self.system_metrics.append(metrics)
                
                # Keep only last hour of metrics
                cutoff = time.time() - 3600
                self.system_metrics = [
                    m for m in self.system_metrics
                    if m["timestamp"] > cutoff
                ]
            except Exception:
                pass
            
            time.sleep(interval)
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics across all trackers.
        
        Returns:
            Aggregated performance data
        """
        all_metrics = []
        for tracker in self.trackers.values():
            all_metrics.extend(tracker.metrics)
        
        if not all_metrics:
            return {"message": "No metrics available"}
        
        # Aggregate by operation type
        operation_stats = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "total_cpu": 0,
            "total_memory": 0,
            "errors": 0
        })
        
        for metric in all_metrics:
            stats = operation_stats[metric.operation]
            stats["count"] += 1
            stats["total_duration"] += metric.duration
            stats["total_cpu"] += metric.cpu_percent
            stats["total_memory"] += metric.memory_mb
            stats["errors"] += len(metric.errors)
        
        # Calculate averages
        for op, stats in operation_stats.items():
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            stats["avg_cpu"] = stats["total_cpu"] / stats["count"]
            stats["avg_memory"] = stats["total_memory"] / stats["count"]
            stats["error_rate"] = stats["errors"] / stats["count"]
        
        return {
            "total_operations": len(all_metrics),
            "total_trackers": len(self.trackers),
            "operation_types": dict(operation_stats),
            "system_metrics": self.system_metrics[-1] if self.system_metrics else None
        }
    
    def export_report(self, file_path: Union[str, Path], format: str = "html"):
        """
        Export comprehensive performance report.
        
        Args:
            file_path: Output file path
            format: Report format ('html', 'json', 'pdf')
        """
        path = Path(file_path)
        
        if format == "json":
            data = {
                "timestamp": datetime.now().isoformat(),
                "aggregated_metrics": self.get_aggregated_metrics(),
                "trackers": {
                    name: {
                        "summary": tracker.get_summary(),
                        "comparison": tracker.get_operation_comparison()
                    }
                    for name, tracker in self.trackers.items()
                },
                "system_metrics": self.system_metrics
            }
            
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        
        elif format == "html":
            self._export_html_report(path)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_html_report(self, file_path: Path):
        """Export HTML performance report."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DagLab Performance Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .metric { font-weight: bold; color: #2196F3; }
                .warning { color: #ff9800; }
                .error { color: #f44336; }
            </style>
        </head>
        <body>
            <h1>DagLab Performance Report</h1>
            <p>Generated: {timestamp}</p>
            
            <h2>System Overview</h2>
            {system_overview}
            
            <h2>Operation Statistics</h2>
            {operation_stats}
            
            <h2>Tracker Details</h2>
            {tracker_details}
        </body>
        </html>
        """
        
        # Generate content sections
        aggregated = self.get_aggregated_metrics()
        
        # System overview
        system_overview = "<table>"
        if aggregated.get("system_metrics"):
            sys_metrics = aggregated["system_metrics"]
            system_overview += f"""
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>CPU Usage</td><td class="metric">{sys_metrics['cpu']['percent']:.1f}%</td></tr>
            <tr><td>Memory Usage</td><td class="metric">{sys_metrics['memory']['percent']:.1f}%</td></tr>
            <tr><td>Disk Usage</td><td class="metric">{sys_metrics['disk']['percent']:.1f}%</td></tr>
            """
        system_overview += "</table>"
        
        # Operation statistics
        operation_stats = "<table><tr><th>Operation</th><th>Count</th><th>Avg Duration (s)</th><th>Avg CPU (%)</th><th>Avg Memory (MB)</th><th>Error Rate</th></tr>"
        
        for op, stats in aggregated.get("operation_types", {}).items():
            error_class = "error" if stats["error_rate"] > 0.1 else "warning" if stats["error_rate"] > 0 else ""
            operation_stats += f"""
            <tr>
                <td>{op}</td>
                <td>{stats['count']}</td>
                <td>{stats['avg_duration']:.3f}</td>
                <td>{stats['avg_cpu']:.1f}</td>
                <td>{stats['avg_memory']:.1f}</td>
                <td class="{error_class}">{stats['error_rate']:.1%}</td>
            </tr>
            """
        operation_stats += "</table>"
        
        # Tracker details
        tracker_details = ""
        for name, tracker in self.trackers.items():
            tracker_details += f"<h3>Tracker: {name}</h3>"
            summary = tracker.get_summary()
            
            if isinstance(summary, dict) and summary.get("operation_count", 0) > 0:
                tracker_details += f"""
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Operations</td><td>{summary['operation_count']}</td></tr>
                    <tr><td>Total Duration</td><td>{summary['total_duration']:.2f}s</td></tr>
                    <tr><td>Success Rate</td><td>{summary['success_rate']:.1%}</td></tr>
                </table>
                """
        
        # Fill template
        html = html.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            system_overview=system_overview,
            operation_stats=operation_stats,
            tracker_details=tracker_details
        )
        
        with open(file_path, "w") as f:
            f.write(html)