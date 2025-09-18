"""Tests for performance tracking helpers."""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from daglab.helpers.performance import (
    PerformanceTracker,
    PerformanceMetrics,
    get_memory_usage,
    monitor_resource_usage,
    profile_memory_usage
)


class TestPerformanceTracker:
    """Test PerformanceTracker class."""
    
    @pytest.fixture
    def tracker(self):
        """Create PerformanceTracker instance."""
        return PerformanceTracker("test_tracker")
    
    def test_basic_tracking(self, tracker):
        """Test basic operation tracking."""
        # Track an operation
        with tracker.track("test_operation"):
            time.sleep(0.1)
        
        # Verify metrics
        assert len(tracker.metrics) == 1
        metric = tracker.metrics[0]
        
        assert isinstance(metric, PerformanceMetrics)
        assert metric.operation == "test_operation"
        assert metric.duration >= 0.1
        assert metric.memory_mb > 0
        assert metric.errors == []
        assert metric.metadata["success"] is True
    
    def test_tracking_with_error(self, tracker):
        """Test tracking operations that raise errors."""
        with pytest.raises(ValueError):
            with tracker.track("failing_operation"):
                raise ValueError("Test error")
        
        # Verify error was recorded
        assert len(tracker.metrics) == 1
        metric = tracker.metrics[0]
        
        assert metric.operation == "failing_operation"
        assert metric.metadata["success"] is False
        assert len(metric.errors) == 1
        assert "Test error" in metric.errors[0]
    
    def test_tracking_with_metadata(self, tracker):
        """Test tracking with custom metadata."""
        metadata = {"user": "test_user", "version": "1.0"}
        
        with tracker.track("operation_with_metadata", metadata=metadata):
            pass
        
        metric = tracker.metrics[0]
        assert metric.metadata["user"] == "test_user"
        assert metric.metadata["version"] == "1.0"
        assert metric.metadata["success"] is True
    
    def test_manual_start_end(self, tracker):
        """Test manual start/end operation tracking."""
        tracker.start_operation("manual_op", metadata={"type": "manual"})
        time.sleep(0.05)
        tracker.end_operation("manual_op", success=True)
        
        assert len(tracker.metrics) == 1
        metric = tracker.metrics[0]
        
        assert metric.operation == "manual_op"
        assert metric.duration >= 0.05
        assert metric.metadata["type"] == "manual"
        assert metric.metadata["success"] is True
    
    def test_end_non_existent_operation(self, tracker):
        """Test ending a non-existent operation."""
        # Should not raise error
        tracker.end_operation("non_existent")
        assert len(tracker.metrics) == 0
    
    def test_get_summary_single_operation(self, tracker):
        """Test getting summary for a single operation type."""
        # Track multiple instances of same operation
        for i in range(3):
            with tracker.track("repeated_op"):
                time.sleep(0.01 * (i + 1))
        
        summary = tracker.get_summary("repeated_op")
        
        assert summary["operation_count"] == 3
        assert summary["duration"]["mean"] > 0
        assert summary["duration"]["std"] >= 0
        assert summary["success_rate"] == 1.0
    
    def test_get_summary_all_operations(self, tracker):
        """Test getting summary for all operations."""
        # Track different operations
        with tracker.track("op1"):
            pass
        
        with tracker.track("op2"):
            pass
        
        try:
            with tracker.track("op3"):
                raise Exception("Test error")
        except:
            pass
        
        summary = tracker.get_summary()
        
        assert summary["operation_count"] == 3
        assert summary["success_rate"] == 2/3
        assert summary["error_count"] == 1
    
    def test_get_operation_comparison(self, tracker):
        """Test comparing performance across operations."""
        # Track different operations
        for _ in range(2):
            with tracker.track("fast_op"):
                time.sleep(0.01)
        
        for _ in range(3):
            with tracker.track("slow_op"):
                time.sleep(0.05)
        
        comparison = tracker.get_operation_comparison()
        
        assert "fast_op" in comparison
        assert "slow_op" in comparison
        
        assert comparison["fast_op"]["count"] == 2
        assert comparison["slow_op"]["count"] == 3
        
        # Slow op should have higher average duration
        assert comparison["slow_op"]["avg_duration"] > comparison["fast_op"]["avg_duration"]
    
    def test_export_json(self, tracker):
        """Test exporting metrics to JSON."""
        # Track some operations
        with tracker.track("export_test"):
            pass
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tracker.export(f.name, format="json")
            
            # Load and verify
            with open(f.name) as rf:
                data = json.load(rf)
            
            assert data["tracker"] == "test_tracker"
            assert "timestamp" in data
            assert "summary" in data
            assert len(data["metrics"]) == 1
            assert data["metrics"][0]["operation"] == "export_test"
    
    def test_export_csv(self, tracker):
        """Test exporting metrics to CSV."""
        # Track operations
        with tracker.track("csv_test1"):
            pass
        
        with tracker.track("csv_test2"):
            pass
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            tracker.export(f.name, format="csv")
            
            # Verify CSV was created
            import csv
            with open(f.name) as rf:
                reader = csv.DictReader(rf)
                rows = list(reader)
            
            assert len(rows) == 2
            operations = [row["operation"] for row in rows]
            assert "csv_test1" in operations
            assert "csv_test2" in operations
    
    def test_export_invalid_format(self, tracker):
        """Test exporting with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            tracker.export("test.xyz", format="xyz")
    
    def test_reset(self, tracker):
        """Test resetting tracker."""
        # Add some metrics
        with tracker.track("op1"):
            pass
        
        tracker.start_operation("op2")
        
        assert len(tracker.metrics) == 1
        assert len(tracker.active_operations) == 1
        
        # Reset
        tracker.reset()
        
        assert len(tracker.metrics) == 0
        assert len(tracker.active_operations) == 0
    
    @patch('matplotlib.pyplot.show')
    def test_visualize_durations(self, mock_show, tracker):
        """Test duration visualization."""
        # Track operations
        for i in range(5):
            with tracker.track(f"op{i % 2}"):
                time.sleep(0.01 * (i + 1))
        
        fig = tracker.visualize("duration")
        assert fig is not None
    
    @patch('matplotlib.pyplot.show')
    def test_visualize_memory(self, mock_show, tracker):
        """Test memory visualization."""
        for i in range(3):
            with tracker.track(f"mem_op_{i}"):
                time.sleep(0.01)
        
        fig = tracker.visualize("memory")
        assert fig is not None
    
    @patch('matplotlib.pyplot.show')  
    def test_visualize_cpu(self, mock_show, tracker):
        """Test CPU visualization."""
        for _ in range(3):
            with tracker.track("cpu_op"):
                pass
        
        fig = tracker.visualize("cpu")
        assert fig is not None
    
    @patch('matplotlib.pyplot.show')
    def test_visualize_io(self, mock_show, tracker):
        """Test I/O visualization."""
        for _ in range(2):
            with tracker.track("io_op"):
                pass
        
        fig = tracker.visualize("io")
        assert fig is not None
    
    @patch('matplotlib.pyplot.show')
    def test_visualize_timeline(self, mock_show, tracker):
        """Test timeline visualization."""
        with tracker.track("op1"):
            time.sleep(0.05)
        
        with tracker.track("op2"):
            time.sleep(0.03)
        
        fig = tracker.visualize("timeline")
        assert fig is not None
    
    def test_visualize_invalid_type(self, tracker):
        """Test visualization with invalid type."""
        with pytest.raises(ValueError, match="Unknown metric type"):
            tracker.visualize("invalid_type")
    
    def test_visualize_no_metrics(self, tracker):
        """Test visualization with no metrics."""
        fig = tracker.visualize("duration")
        assert fig is not None  # Should return empty figure


class TestUtilityFunctions:
    """Test standalone utility functions."""
    
    def test_get_memory_usage(self):
        """Test get_memory_usage function."""
        memory = get_memory_usage()
        
        assert isinstance(memory, dict)
        assert "rss" in memory
        assert "vms" in memory
        assert "percent" in memory
        assert "available" in memory
        
        assert memory["rss"] > 0
        assert memory["vms"] > 0
        assert 0 <= memory["percent"] <= 100
        assert memory["available"] > 0
    
    @patch('time.sleep', side_effect=lambda x: None)  # Speed up test
    def test_monitor_resource_usage(self, mock_sleep):
        """Test monitor_resource_usage function."""
        metrics = monitor_resource_usage(duration=0.2, interval=0.05)
        
        assert isinstance(metrics, dict)
        assert all(key in metrics for key in [
            "timestamps", "cpu_percent", "memory_mb",
            "memory_percent", "io_read_mb", "io_write_mb"
        ])
        
        # Should have multiple samples
        assert len(metrics["timestamps"]) > 1
        assert len(metrics["cpu_percent"]) == len(metrics["timestamps"])
        
        # Values should be reasonable
        assert all(t >= 0 for t in metrics["timestamps"])
        assert all(m >= 0 for m in metrics["memory_mb"])
    
    def test_profile_memory_usage_decorator(self, capsys):
        """Test profile_memory_usage decorator."""
        @profile_memory_usage
        def test_function(size):
            # Allocate some memory
            data = [0] * size
            return len(data)
        
        result = test_function(1000000)
        assert result == 1000000
        
        # Check output
        captured = capsys.readouterr()
        assert "Memory usage for test_function" in captured.out
        assert "RSS Delta:" in captured.out
        assert "Final RSS:" in captured.out
        assert "MB" in captured.out