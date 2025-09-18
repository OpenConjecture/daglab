"""Tests for the telemetry module."""

import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from daglab.runtime.telemetry import (
    Event,
    Metric,
    PerformanceTracker,
    TelemetryClient,
    get_telemetry_client,
    setup_telemetry,
)


class TestMetric:
    """Test Metric dataclass."""
    
    def test_metric_creation(self):
        """Test creating a metric."""
        metric = Metric(name="test_metric", value=42.5)
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert isinstance(metric.timestamp, float)
        assert metric.tags == {}
        assert metric.metadata == {}
    
    def test_metric_with_tags_and_metadata(self):
        """Test metric with tags and metadata."""
        metric = Metric(
            name="cpu_usage",
            value=75.3,
            tags={"host": "server1", "env": "prod"},
            metadata={"unit": "percent", "threshold": 80}
        )
        
        assert metric.tags["host"] == "server1"
        assert metric.metadata["unit"] == "percent"


class TestEvent:
    """Test Event dataclass."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(name="user_login")
        
        assert event.name == "user_login"
        assert isinstance(event.timestamp, float)
        assert event.properties == {}
        assert event.user_id is None
        assert event.session_id is None
    
    def test_event_with_properties(self):
        """Test event with properties."""
        event = Event(
            name="button_clicked",
            properties={"button_id": "submit", "page": "checkout"},
            user_id="user123",
            session_id="session456"
        )
        
        assert event.properties["button_id"] == "submit"
        assert event.user_id == "user123"
        assert event.session_id == "session456"


class TestTelemetryClient:
    """Test TelemetryClient class."""
    
    def test_initialization_disabled(self):
        """Test client initialization when disabled."""
        client = TelemetryClient(enabled=True, opt_in=False)
        assert client.enabled is False
        
        client = TelemetryClient(enabled=False, opt_in=True)
        assert client.enabled is False
    
    def test_initialization_enabled(self):
        """Test client initialization when enabled."""
        with TemporaryDirectory() as tmp_dir:
            client = TelemetryClient(
                enabled=True,
                opt_in=True,
                storage_path=Path(tmp_dir) / "telemetry"
            )
            assert client.enabled is True
            assert client.storage_path.exists()
    
    def test_is_enabled(self):
        """Test is_enabled method."""
        client = TelemetryClient(enabled=True, opt_in=True)
        assert client.is_enabled() is True
        
        client = TelemetryClient(enabled=True, opt_in=False)
        assert client.is_enabled() is False
    
    def test_record_metric_disabled(self):
        """Test that metrics are not recorded when disabled."""
        client = TelemetryClient(enabled=False)
        
        client.record_metric("test", 100)
        assert len(client._metrics_buffer) == 0
    
    def test_record_metric_enabled(self):
        """Test recording metrics when enabled."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.record_metric("test_metric", 42.5, tags={"env": "test"})
        
        assert len(client._metrics_buffer) == 1
        metric = client._metrics_buffer[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.tags["env"] == "test"
    
    def test_record_event_disabled(self):
        """Test that events are not recorded when disabled."""
        client = TelemetryClient(enabled=False)
        
        client.record_event("test_event")
        assert len(client._events_buffer) == 0
    
    def test_record_event_enabled(self):
        """Test recording events when enabled."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.record_event("user_action", properties={"action": "click"})
        
        assert len(client._events_buffer) == 1
        event = client._events_buffer[0]
        assert event.name == "user_action"
        assert event.properties["action"] == "click"
        assert event.session_id == client.session_id
    
    def test_increment_counter(self):
        """Test counter increment."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.increment_counter("requests")
        client.increment_counter("requests", 5)
        
        assert client._counters["requests"] == 6
        # Should also record metrics
        assert any(m.name == "counter.requests" for m in client._metrics_buffer)
    
    def test_timer_context_manager(self):
        """Test timer context manager."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        with client.timer("operation", tags={"type": "test"}):
            time.sleep(0.01)  # Sleep for 10ms
        
        # Check that metric was recorded
        timer_metrics = [m for m in client._metrics_buffer if m.name == "timer.operation"]
        assert len(timer_metrics) == 1
        assert timer_metrics[0].value >= 0.01
        assert timer_metrics[0].tags["type"] == "test"
    
    def test_start_stop_timer(self):
        """Test manual timer start/stop."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.start_timer("manual_timer")
        time.sleep(0.01)
        duration = client.stop_timer("manual_timer")
        
        assert duration >= 0.01
        assert "manual_timer" not in client._timers
        
        # Check metric was recorded
        assert any(m.name == "timer.manual_timer" for m in client._metrics_buffer)
    
    def test_gauge(self):
        """Test gauge metric."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.gauge("memory_usage", 1024.5, tags={"unit": "MB"})
        
        gauge_metrics = [m for m in client._metrics_buffer if m.name == "gauge.memory_usage"]
        assert len(gauge_metrics) == 1
        assert gauge_metrics[0].value == 1024.5
        assert gauge_metrics[0].tags["unit"] == "MB"
    
    def test_histogram(self):
        """Test histogram metric."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        buckets = [0, 10, 25, 50, 100]
        client.histogram("response_time", 35, buckets=buckets, tags={"endpoint": "/api"})
        
        hist_metrics = [m for m in client._metrics_buffer if m.name == "histogram.response_time"]
        assert len(hist_metrics) == 1
        assert hist_metrics[0].value == 35
        assert hist_metrics[0].metadata["bucket"] == 3  # Falls in bucket index 3 (25-50)
        assert hist_metrics[0].tags["endpoint"] == "/api"
    
    def test_buffer_overflow_triggers_flush(self, tmp_path):
        """Test that buffer overflow triggers flush."""
        client = TelemetryClient(
            enabled=True,
            opt_in=True,
            buffer_size=5,
            storage_path=tmp_path / "telemetry"
        )
        
        # Add metrics to exceed buffer
        for i in range(6):
            client.record_metric(f"metric_{i}", i)
        
        # Buffer should have been flushed
        assert len(client._metrics_buffer) == 1
        
        # Check that file was created
        metrics_files = list(client.storage_path.glob("metrics_*.json"))
        assert len(metrics_files) == 1
    
    def test_flush_metrics(self, tmp_path):
        """Test metrics flushing."""
        client = TelemetryClient(
            enabled=True,
            opt_in=True,
            storage_path=tmp_path / "telemetry"
        )
        
        client.record_metric("test", 100)
        client.flush_metrics()
        
        # Buffer should be empty
        assert len(client._metrics_buffer) == 0
        
        # File should exist
        metrics_files = list(client.storage_path.glob("metrics_*.json"))
        assert len(metrics_files) == 1
        
        # Verify content
        with open(metrics_files[0]) as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["name"] == "test"
            assert data[0]["value"] == 100
    
    def test_flush_events(self, tmp_path):
        """Test events flushing."""
        client = TelemetryClient(
            enabled=True,
            opt_in=True,
            storage_path=tmp_path / "telemetry"
        )
        
        client.record_event("test_event", properties={"key": "value"})
        client.flush_events()
        
        # Buffer should be empty
        assert len(client._events_buffer) == 0
        
        # File should exist
        events_files = list(client.storage_path.glob("events_*.json"))
        assert len(events_files) == 1
        
        # Verify content
        with open(events_files[0]) as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["name"] == "test_event"
            assert data[0]["properties"]["key"] == "value"
    
    def test_flush_all(self, tmp_path):
        """Test flushing all buffers."""
        client = TelemetryClient(
            enabled=True,
            opt_in=True,
            storage_path=tmp_path / "telemetry"
        )
        
        client.record_metric("metric", 1)
        client.record_event("event")
        client.flush_all()
        
        assert len(client._metrics_buffer) == 0
        assert len(client._events_buffer) == 0
    
    def test_get_session_summary(self):
        """Test session summary."""
        client = TelemetryClient(enabled=True, opt_in=True)
        
        client.record_metric("test", 1)
        client.record_event("event")
        client.increment_counter("counter")
        client.start_timer("timer")
        
        summary = client.get_session_summary()
        
        assert summary["session_id"] == client.session_id
        assert summary["metrics_count"] == 2  # metric + counter
        assert summary["events_count"] == 1
        assert summary["counters"]["counter"] == 1
        assert "timer" in summary["active_timers"]
    
    def test_context_manager(self, tmp_path):
        """Test using client as context manager."""
        with TelemetryClient(
            enabled=True,
            opt_in=True,
            storage_path=tmp_path / "telemetry"
        ) as client:
            client.record_metric("test", 1)
            client.record_event("event")
        
        # Should have flushed on exit
        files = list((tmp_path / "telemetry").glob("*.json"))
        assert len(files) == 2  # metrics and events


class TestPerformanceTracker:
    """Test PerformanceTracker class."""
    
    def test_track_operation_success(self):
        """Test tracking successful operation."""
        client = TelemetryClient(enabled=True, opt_in=True)
        tracker = PerformanceTracker(client)
        
        with tracker.track_operation("test_op", metadata={"version": "1.0"}):
            time.sleep(0.01)
        
        # Check events
        events = [e for e in client._events_buffer if e.name.startswith("test_op")]
        assert len(events) == 2
        assert any(e.name == "test_op.start" for e in events)
        assert any(e.name == "test_op.complete" for e in events)
        
        # Check completion event
        complete_event = next(e for e in events if e.name == "test_op.complete")
        assert complete_event.properties["success"] is True
        assert complete_event.properties["error"] is None
        assert complete_event.properties["version"] == "1.0"
    
    def test_track_operation_failure(self):
        """Test tracking failed operation."""
        client = TelemetryClient(enabled=True, opt_in=True)
        tracker = PerformanceTracker(client)
        
        with pytest.raises(ValueError):
            with tracker.track_operation("failing_op"):
                raise ValueError("Test error")
        
        # Check completion event
        complete_events = [e for e in client._events_buffer if e.name == "failing_op.complete"]
        assert len(complete_events) == 1
        assert complete_events[0].properties["success"] is False
        assert "Test error" in complete_events[0].properties["error"]
    
    @patch('daglab.runtime.telemetry.psutil')
    def test_track_resource_usage(self, mock_psutil):
        """Test tracking resource usage."""
        # Mock psutil
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = MagicMock(
            rss=1024 * 1024 * 512,  # 512 MB
            vms=1024 * 1024 * 1024  # 1 GB
        )
        mock_process.num_threads.return_value = 10
        mock_psutil.Process.return_value = mock_process
        
        client = TelemetryClient(enabled=True, opt_in=True)
        tracker = PerformanceTracker(client)
        
        usage = tracker.track_resource_usage()
        
        assert usage["cpu_percent"] == 25.5
        assert usage["memory_rss_mb"] == 512
        assert usage["memory_vms_mb"] == 1024
        assert usage["num_threads"] == 10
        
        # Check gauges were recorded
        gauge_names = [m.name for m in client._metrics_buffer if m.name.startswith("gauge.resource")]
        assert "gauge.resource.cpu_percent" in gauge_names
        assert "gauge.resource.memory_rss_mb" in gauge_names
    
    def test_track_resource_usage_no_psutil(self):
        """Test resource tracking without psutil."""
        # Mock ImportError for psutil
        with patch('daglab.runtime.telemetry.psutil', side_effect=ImportError):
            client = TelemetryClient(enabled=True, opt_in=True)
            tracker = PerformanceTracker(client)
            
            usage = tracker.track_resource_usage()
            assert usage == {}


class TestGlobalFunctions:
    """Test module-level global functions."""
    
    def test_get_telemetry_client_singleton(self):
        """Test that get_telemetry_client returns singleton."""
        client1 = get_telemetry_client()
        client2 = get_telemetry_client()
        
        assert client1 is client2
    
    @patch.dict(os.environ, {"DAGLAB_TELEMETRY_OPT_IN": "true"})
    def test_get_telemetry_client_opt_in(self):
        """Test opt-in via environment variable."""
        # Reset global client
        import daglab.runtime.telemetry as telemetry_module
        telemetry_module._global_telemetry_client = None
        
        client = get_telemetry_client()
        assert client.enabled is True
    
    def test_setup_telemetry(self):
        """Test setup_telemetry function."""
        client = setup_telemetry(
            enabled=True,
            opt_in=True,
            service_name="test_service"
        )
        
        assert client.enabled is True
        assert client.service_name == "test_service"
        
        # Should be the global client now
        assert get_telemetry_client() is client
    
    def test_telemetry_disabled_by_default(self):
        """Test that telemetry is disabled by default."""
        # Reset global client
        import daglab.runtime.telemetry as telemetry_module
        telemetry_module._global_telemetry_client = None
        
        # Clear opt-in env var
        os.environ.pop("DAGLAB_TELEMETRY_OPT_IN", None)
        
        client = get_telemetry_client()
        assert client.enabled is False