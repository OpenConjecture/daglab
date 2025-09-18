"""
Tests for enhanced performance monitoring functionality.
"""

import asyncio
import json
import sqlite3
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from daglab.helpers.performance import (
    PerformanceTracker, MetricsCollector, PerformanceMetrics,
    get_memory_usage, monitor_resource_usage, profile_memory_usage
)
from daglab.helpers.dashboard import DashboardServer, DashboardConfig, Alert
from daglab.helpers.metrics_store import MetricsStore, RetentionPolicy, AggregationType
from daglab.helpers.notebook_metrics import (
    NotebookPerformanceTracker, CellMetrics, VariableMetrics
)


class TestEnhancedPerformanceTracker:
    """Test enhanced PerformanceTracker features."""
    
    def test_background_monitoring(self):
        """Test background monitoring functionality."""
        tracker = PerformanceTracker("test", enable_background_monitoring=True)
        
        # Let background monitoring collect some data
        time.sleep(3)
        
        # Get background metrics
        metrics = tracker.get_background_metrics(last_seconds=5)
        
        assert len(metrics) > 0
        assert all("cpu_percent" in m for m in metrics)
        assert all("memory_mb" in m for m in metrics)
        
        # Clean up
        tracker.reset()
    
    def test_anomaly_detection(self):
        """Test anomaly detection."""
        tracker = PerformanceTracker("test")
        
        # Add some normal operations
        for i in range(10):
            with tracker.track("normal_op"):
                time.sleep(0.1)
        
        # Set baseline
        tracker.set_baseline("normal_op")
        
        # Add anomalous operation
        with tracker.track("normal_op"):
            time.sleep(0.5)  # Much slower than normal
        
        # Detect anomalies
        anomalies = tracker.detect_anomalies()
        
        assert len(anomalies) > 0
        assert any("duration" in a["anomalies"][0]["type"] for a in anomalies)
    
    def test_compare_runs(self):
        """Test run comparison functionality."""
        tracker = PerformanceTracker("test")
        
        # First run
        with tracker.track("operation", {"run_id": "run1"}):
            time.sleep(0.1)
        
        # Second run (faster)
        with tracker.track("operation", {"run_id": "run2"}):
            time.sleep(0.05)
        
        # Compare runs
        comparison = tracker.compare_runs(["run1", "run2"])
        
        assert "run1" in comparison
        assert "run2" in comparison
        assert "relative_to_baseline" in comparison["run2"]
        assert comparison["run2"]["relative_to_baseline"]["duration_change"] < 0
    
    def test_export_prometheus(self):
        """Test Prometheus export format."""
        tracker = PerformanceTracker("test")
        
        with tracker.track("test_operation"):
            time.sleep(0.1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.prom', delete=False) as f:
            tracker.export(f.name, format="prometheus")
            
        # Read and verify format
        with open(f.name, 'r') as f:
            content = f.read()
            
        assert "daglab_operation_duration_seconds" in content
        assert "daglab_operation_cpu_percent" in content
        assert "daglab_operation_memory_bytes" in content
        
        # Clean up
        Path(f.name).unlink()


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_tracker_registration(self):
        """Test tracker registration and unregistration."""
        collector = MetricsCollector()
        tracker1 = PerformanceTracker("tracker1")
        tracker2 = PerformanceTracker("tracker2")
        
        collector.register_tracker(tracker1)
        collector.register_tracker(tracker2)
        
        assert len(collector.trackers) == 2
        assert "tracker1" in collector.trackers
        
        collector.unregister_tracker("tracker1")
        assert len(collector.trackers) == 1
        assert "tracker1" not in collector.trackers
    
    def test_system_metrics_collection(self):
        """Test system-wide metrics collection."""
        collector = MetricsCollector()
        
        metrics = collector.collect_system_metrics()
        
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert "network" in metrics
        
        assert metrics["cpu"]["percent"] >= 0
        assert metrics["memory"]["percent"] >= 0
        assert metrics["memory"]["total"] > 0
    
    def test_aggregated_metrics(self):
        """Test aggregated metrics across trackers."""
        collector = MetricsCollector()
        
        # Create trackers with metrics
        tracker1 = PerformanceTracker("tracker1")
        tracker2 = PerformanceTracker("tracker2")
        
        with tracker1.track("operation1"):
            time.sleep(0.1)
            
        with tracker2.track("operation1"):
            time.sleep(0.1)
            
        with tracker2.track("operation2"):
            time.sleep(0.05)
        
        collector.register_tracker(tracker1)
        collector.register_tracker(tracker2)
        
        # Get aggregated metrics
        aggregated = collector.get_aggregated_metrics()
        
        assert aggregated["total_operations"] == 3
        assert aggregated["total_trackers"] == 2
        assert "operation1" in aggregated["operation_types"]
        assert aggregated["operation_types"]["operation1"]["count"] == 2
    
    def test_html_export(self):
        """Test HTML report export."""
        collector = MetricsCollector()
        tracker = PerformanceTracker("test")
        
        with tracker.track("test_op"):
            time.sleep(0.1)
            
        collector.register_tracker(tracker)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            collector.export_report(f.name, format="html")
            
        # Verify HTML content
        with open(f.name, 'r') as f:
            html = f.read()
            
        assert "<html>" in html
        assert "DagLab Performance Report" in html
        assert "test_op" in html
        
        # Clean up
        Path(f.name).unlink()


class TestDashboardServer:
    """Test performance dashboard server."""
    
    @pytest.fixture
    def dashboard(self):
        """Create dashboard server instance."""
        config = DashboardConfig(host="127.0.0.1", port=8766)
        return DashboardServer(config)
    
    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.config.port == 8766
        assert len(dashboard.active_connections) == 0
        assert len(dashboard.alerts) == 0
    
    def test_api_status(self, dashboard):
        """Test status API endpoint."""
        client = TestClient(dashboard.app)
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "timestamp" in data
    
    def test_api_metrics(self, dashboard):
        """Test metrics API endpoint."""
        # Register a tracker
        tracker = PerformanceTracker("test")
        with tracker.track("test_op"):
            time.sleep(0.1)
            
        dashboard.register_tracker(tracker)
        
        client = TestClient(dashboard.app)
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_operations" in data
        assert "operation_types" in data
    
    def test_alert_generation(self, dashboard):
        """Test alert generation."""
        # Simulate high CPU metrics
        metrics = {
            "system": {
                "cpu": {"percent": 85},
                "memory": {"percent": 50}
            }
        }
        
        dashboard._check_alerts(metrics)
        
        assert len(dashboard.alerts) == 1
        assert dashboard.alerts[0].metric == "cpu_percent"
        assert dashboard.alerts[0].level == "warning"
    
    def test_static_html_export(self, dashboard):
        """Test static HTML export."""
        tracker = PerformanceTracker("test")
        with tracker.track("test_op"):
            time.sleep(0.1)
            
        dashboard.register_tracker(tracker)
        
        client = TestClient(dashboard.app)
        response = client.get("/api/export?format=html")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "DagLab Performance Report" in response.text


class TestMetricsStore:
    """Test metrics storage functionality."""
    
    @pytest.fixture
    def store(self):
        """Create temporary metrics store."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        store = MetricsStore(db_path)
        yield store
        
        # Clean up
        Path(db_path).unlink()
    
    def test_store_and_query_metrics(self, store):
        """Test storing and querying metrics."""
        # Create sample metric
        metric = PerformanceMetrics(
            operation="test_op",
            start_time=time.time(),
            end_time=time.time() + 1,
            duration=1.0,
            cpu_percent=50.0,
            memory_mb=1024.0,
            memory_percent=25.0,
            memory_delta_mb=10.0,
            io_read_mb=5.0,
            io_write_mb=3.0,
            errors=[],
            metadata={"test": True}
        )
        
        # Store metric
        store.store_metric(metric)
        
        # Query metrics
        results = store.query_metrics()
        
        assert len(results) == 1
        assert results[0]["operation"] == "test_op"
        assert results[0]["duration"] == 1.0
    
    def test_batch_storage(self, store):
        """Test batch metric storage."""
        metrics = []
        
        for i in range(10):
            metric = PerformanceMetrics(
                operation=f"op_{i}",
                start_time=time.time() + i,
                end_time=time.time() + i + 1,
                duration=1.0,
                cpu_percent=50.0,
                memory_mb=1024.0,
                memory_percent=25.0,
                memory_delta_mb=10.0,
                io_read_mb=5.0,
                io_write_mb=3.0,
                errors=[],
                metadata={}
            )
            metrics.append(metric)
        
        # Store batch
        store.store_metrics_batch(metrics)
        
        # Query all
        results = store.query_metrics()
        assert len(results) == 10
    
    def test_aggregation(self, store):
        """Test metric aggregation."""
        # Store metrics over time
        base_time = time.time()
        
        for hour in range(3):
            for i in range(5):
                metric = PerformanceMetrics(
                    operation="test_op",
                    start_time=base_time + (hour * 3600) + (i * 60),
                    end_time=base_time + (hour * 3600) + (i * 60) + 30,
                    duration=30.0 + i,
                    cpu_percent=50.0 + i,
                    memory_mb=1024.0,
                    memory_percent=25.0,
                    memory_delta_mb=10.0,
                    io_read_mb=5.0,
                    io_write_mb=3.0,
                    errors=[],
                    metadata={}
                )
                store.store_metric(metric)
        
        # Aggregate by hour
        df = store.aggregate_metrics(
            start_time=base_time,
            end_time=base_time + (3 * 3600),
            aggregation_period="hour"
        )
        
        assert len(df) == 3  # 3 hours
        assert "duration_mean" in df.columns
        assert "duration_min" in df.columns
        assert "duration_max" in df.columns
    
    def test_percentile_calculation(self, store):
        """Test percentile calculations."""
        # Store metrics with varying durations
        for i in range(100):
            metric = PerformanceMetrics(
                operation="test_op",
                start_time=time.time() + i,
                end_time=time.time() + i + 1,
                duration=np.random.exponential(1.0),  # Exponential distribution
                cpu_percent=50.0,
                memory_mb=1024.0,
                memory_percent=25.0,
                memory_delta_mb=10.0,
                io_read_mb=5.0,
                io_write_mb=3.0,
                errors=[],
                metadata={}
            )
            store.store_metric(metric)
        
        # Calculate percentiles
        percentiles = store.calculate_percentiles(
            "duration",
            operation="test_op",
            percentiles=[0.5, 0.95, 0.99]
        )
        
        assert 0.5 in percentiles
        assert 0.95 in percentiles
        assert 0.99 in percentiles
        assert percentiles[0.5] < percentiles[0.95] < percentiles[0.99]
    
    def test_retention_policy(self, store):
        """Test data retention policy."""
        # Store old metrics
        old_time = time.time() - (10 * 86400)  # 10 days ago
        
        for i in range(5):
            metric = PerformanceMetrics(
                operation="old_op",
                start_time=old_time + i,
                end_time=old_time + i + 1,
                duration=1.0,
                cpu_percent=50.0,
                memory_mb=1024.0,
                memory_percent=25.0,
                memory_delta_mb=10.0,
                io_read_mb=5.0,
                io_write_mb=3.0,
                errors=[],
                metadata={}
            )
            store.store_metric(metric)
        
        # Store recent metrics
        recent_time = time.time()
        
        for i in range(5):
            metric = PerformanceMetrics(
                operation="recent_op",
                start_time=recent_time + i,
                end_time=recent_time + i + 1,
                duration=1.0,
                cpu_percent=50.0,
                memory_mb=1024.0,
                memory_percent=25.0,
                memory_delta_mb=10.0,
                io_read_mb=5.0,
                io_write_mb=3.0,
                errors=[],
                metadata={}
            )
            store.store_metric(metric)
        
        # Apply retention policy
        store.apply_retention_policy()
        
        # Check that old metrics are removed
        results = store.query_metrics()
        assert all(r["operation"] != "old_op" for r in results)
        assert any(r["operation"] == "recent_op" for r in results)


class TestNotebookMetrics:
    """Test notebook-specific metrics functionality."""
    
    @pytest.fixture
    def tracker(self):
        """Create notebook tracker instance."""
        # Mock IPython environment
        with patch('daglab.helpers.notebook_metrics.get_ipython'):
            return NotebookPerformanceTracker("test")
    
    def test_cell_tracking(self, tracker):
        """Test cell execution tracking."""
        # Start cell
        tracker.start_cell("cell_1", "code", 1)
        
        # Simulate some work
        time.sleep(0.1)
        
        # End cell
        source_code = """
import numpy as np
import pandas as pd

def process_data(x):
    return x * 2

result = process_data(10)
"""
        metrics = tracker.end_cell("cell_1", source_code, output_size=100)
        
        assert metrics.cell_id == "cell_1"
        assert metrics.duration > 0.1
        assert metrics.output_size == 100
        assert "numpy" in metrics.imports
        assert "process_data" in metrics.functions_defined
    
    def test_variable_tracking(self, tracker):
        """Test variable metrics tracking."""
        # Track some variables
        tracker._track_variable("data", pd.DataFrame({'a': [1, 2, 3]}))
        tracker._track_variable("array", np.array([1, 2, 3, 4, 5]))
        tracker._track_variable("text", "Hello, World!")
        
        # Get variable report
        report = tracker.get_variable_report()
        
        assert len(report) == 3
        assert "data" in report["name"].values
        assert "array" in report["name"].values
        
        # Check types
        data_row = report[report["name"] == "data"].iloc[0]
        assert data_row["type"] == "DataFrame"
    
    def test_optimization_suggestions(self, tracker):
        """Test optimization suggestion generation."""
        # Add some problematic cells
        tracker.cell_metrics.append(
            CellMetrics(
                cell_id="slow_cell",
                cell_type="code",
                execution_count=1,
                start_time=time.time(),
                end_time=time.time() + 5,  # 5 seconds
                duration=5.0,
                memory_before=1000,
                memory_after=1200,
                memory_delta=200,  # 200MB increase
                cpu_percent=90,
                variables_created=[],
                variables_modified=[],
                imports=[],
                functions_defined=[],
                classes_defined=[],
                errors=[],
                output_size=0
            )
        )
        
        # Add large variable
        tracker.variable_metrics["big_data"] = VariableMetrics(
            name="big_data",
            type_name="ndarray",
            size_bytes=200 * 1024 * 1024,  # 200MB
            shape=(1000000, 200),
            created_time=time.time(),
            last_modified=time.time(),
            access_count=0  # Unused
        )
        
        # Get suggestions
        suggestions = tracker.generate_optimization_suggestions()
        
        # Should have suggestions for slow cells and large variables
        assert any(s["category"] == "slow_cells" for s in suggestions)
        assert any(s["category"] == "large_variables" for s in suggestions)
        assert any(s["category"] == "unused_variables" for s in suggestions)
    
    def test_report_generation(self, tracker):
        """Test HTML report generation."""
        # Add some metrics
        tracker.start_cell("cell_1", "code", 1)
        time.sleep(0.1)
        tracker.end_cell("cell_1", "import pandas as pd", 50)
        
        # Generate report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            html = tracker.generate_report(f.name)
            
        # Verify content
        assert "Notebook Performance Report" in html
        assert "cell_1" in html
        assert "pandas" in html
        
        # Clean up
        Path(f.name).unlink()


def test_memory_profiling_decorator():
    """Test memory profiling decorator."""
    
    @profile_memory_usage
    def memory_intensive_function():
        # Allocate some memory
        data = [i for i in range(1000000)]
        return sum(data)
    
    # Capture print output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        result = memory_intensive_function()
    
    output = f.getvalue()
    
    assert "Memory usage for memory_intensive_function" in output
    assert "RSS Delta:" in output
    assert "Final RSS:" in output


def test_resource_monitoring():
    """Test resource monitoring utility."""
    # Monitor for a short duration
    metrics = monitor_resource_usage(duration=2, interval=0.5)
    
    assert "timestamps" in metrics
    assert "cpu_percent" in metrics
    assert "memory_mb" in metrics
    
    # Should have approximately 4 samples
    assert len(metrics["timestamps"]) >= 3
    assert len(metrics["timestamps"]) <= 5
    
    # All values should be non-negative
    assert all(v >= 0 for v in metrics["cpu_percent"])
    assert all(v >= 0 for v in metrics["memory_mb"])