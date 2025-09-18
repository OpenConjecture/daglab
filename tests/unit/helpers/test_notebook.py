"""Tests for notebook helper functions."""

import json
import time
from unittest.mock import Mock, patch, MagicMock
import pytest

from daglab.helpers.notebook import NotebookHelpers


class TestNotebookHelpers:
    """Test NotebookHelpers class."""
    
    @pytest.fixture
    def helpers(self):
        """Create NotebookHelpers instance."""
        with patch('daglab.helpers.notebook.DagsterInstance'):
            return NotebookHelpers()
    
    @pytest.fixture
    def mock_graphql_response(self):
        """Mock GraphQL response."""
        def _response(data):
            return {"data": data}
        return _response
    
    def test_run_job_success(self, helpers, mock_graphql_response):
        """Test successful job execution."""
        # Mock GraphQL response
        mock_response = mock_graphql_response({
            "launchRun": {
                "__typename": "LaunchRunSuccess",
                "run": {
                    "id": "test-run-123",
                    "status": "STARTED",
                    "pipelineName": "test_job",
                    "tags": [{"key": "env", "value": "test"}]
                }
            }
        })
        
        with patch.object(helpers, '_graphql_request', return_value=mock_response):
            with patch.object(helpers, '_wait_for_run_completion', return_value="SUCCESS"):
                result = helpers.run_job(
                    "test_job",
                    run_config={"ops": {"my_op": {"config": {"value": 42}}}},
                    tags={"env": "test"}
                )
        
        assert result["run_id"] == "test-run-123"
        assert result["status"] == "SUCCESS"
        assert result["job_name"] == "test_job"
        assert "url" in result
    
    def test_run_job_validation_error(self, helpers):
        """Test job execution with validation error."""
        mock_response = {
            "data": {
                "launchRun": {
                    "__typename": "RunConfigValidationError",
                    "errors": [
                        {
                            "message": "Invalid config",
                            "path": ["ops", "my_op"],
                            "reason": "MISSING_REQUIRED_FIELD"
                        }
                    ]
                }
            }
        }
        
        with patch.object(helpers, '_graphql_request', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Launch failed"):
                helpers.run_job("test_job")
    
    def test_run_asset_success(self, helpers, mock_graphql_response):
        """Test successful asset materialization."""
        mock_response = mock_graphql_response({
            "launchAssetMaterialization": {
                "__typename": "LaunchRunSuccess",
                "run": {
                    "id": "asset-run-123",
                    "status": "STARTED",
                    "tags": []
                }
            }
        })
        
        with patch.object(helpers, '_graphql_request', return_value=mock_response):
            with patch.object(helpers, '_wait_for_run_completion', return_value="SUCCESS"):
                result = helpers.run_asset("my_asset", partition_key="2024-01-01")
        
        assert result["run_id"] == "asset-run-123"
        assert result["status"] == "SUCCESS"
        assert result["asset_key"] == ["my_asset"]
        assert result["partition_key"] == "2024-01-01"
    
    def test_discover_all_entities(self, helpers):
        """Test discovering all entity types."""
        mock_responses = {
            "pipelinesOrError": {
                "__typename": "PipelineConnection",
                "nodes": [
                    {"name": "job1", "description": "Test job", "tags": []}
                ]
            },
            "assetsOrError": {
                "__typename": "AssetConnection",
                "nodes": [
                    {
                        "key": {"path": ["models", "my_model"]},
                        "description": "Test model",
                        "partitionDefinition": None
                    }
                ]
            },
            "sensorsOrError": {
                "__typename": "Sensors",
                "results": [
                    {"name": "sensor1", "description": "Test sensor", "status": "RUNNING"}
                ]
            },
            "schedulesOrError": {
                "__typename": "Schedules",
                "results": [
                    {
                        "name": "schedule1",
                        "description": "Test schedule",
                        "status": "RUNNING",
                        "cronSchedule": "0 0 * * *"
                    }
                ]
            }
        }
        
        def mock_graphql(query, variables=None):
            # Determine which query based on content
            if "pipelinesOrError" in query:
                return {"data": {"pipelinesOrError": mock_responses["pipelinesOrError"]}}
            elif "assetsOrError" in query:
                return {"data": {"assetsOrError": mock_responses["assetsOrError"]}}
            elif "sensorsOrError" in query:
                return {"data": {"sensorsOrError": mock_responses["sensorsOrError"]}}
            elif "schedulesOrError" in query:
                return {"data": {"schedulesOrError": mock_responses["schedulesOrError"]}}
        
        with patch.object(helpers, '_graphql_request', side_effect=mock_graphql):
            result = helpers.discover("all")
        
        assert "jobs" in result
        assert "assets" in result
        assert "sensors" in result
        assert "schedules" in result
        assert len(result["jobs"]) == 1
        assert result["assets"][0]["key"] == "models.my_model"
    
    def test_attach_metadata(self, helpers):
        """Test attaching metadata to run."""
        mock_run = Mock()
        mock_run.tags = {"existing": "tag"}
        
        mock_instance = Mock()
        mock_instance.get_run_by_id.return_value = mock_run
        mock_instance.add_run_tags.return_value = None
        
        helpers.instance = mock_instance
        
        result = helpers.attach_metadata(
            "run-123",
            {"custom": "metadata", "number": 42}
        )
        
        assert result is True
        mock_instance.add_run_tags.assert_called_once()
        
        # Check tags were updated correctly
        call_args = mock_instance.add_run_tags.call_args
        assert call_args[0][0] == "run-123"
        tags = call_args[0][1]
        assert "daglab.metadata.custom" in tags
        assert tags["daglab.metadata.custom"] == "metadata"
        assert tags["daglab.metadata.number"] == "42"
    
    def test_validate_config_valid(self, helpers):
        """Test config validation with valid config."""
        mock_response = {
            "data": {
                "isPipelineConfigValid": {
                    "__typename": "PipelineConfigValidationValid",
                    "isPipelineConfigValid": True
                }
            }
        }
        
        with patch.object(helpers, '_graphql_request', return_value=mock_response):
            result = helpers.validate_config(
                "test_job",
                {"ops": {"my_op": {"config": {"value": 42}}}}
            )
        
        assert result["valid"] is True
        assert result["errors"] == []
    
    def test_validate_config_invalid(self, helpers):
        """Test config validation with invalid config."""
        mock_response = {
            "data": {
                "isPipelineConfigValid": {
                    "__typename": "RunConfigValidationError",
                    "errors": [
                        {
                            "message": "Missing required field",
                            "path": ["ops", "my_op", "config"],
                            "reason": "MISSING_REQUIRED_FIELD"
                        }
                    ]
                }
            }
        }
        
        with patch.object(helpers, '_graphql_request', return_value=mock_response):
            result = helpers.validate_config("test_job", {})
        
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["reason"] == "MISSING_REQUIRED_FIELD"
    
    def test_track_performance(self, helpers):
        """Test performance tracking context manager."""
        with helpers.track_performance("test_operation"):
            time.sleep(0.1)  # Simulate work
        
        # Check metrics were recorded
        assert len(helpers._performance_metrics) == 1
        metric = helpers._performance_metrics[0]
        
        assert metric["operation"] == "test_operation"
        assert metric["duration_seconds"] >= 0.1
        assert "memory_delta_mb" in metric
        assert "timestamp" in metric
    
    def test_manage_state_operations(self, helpers):
        """Test state management operations."""
        # Set value
        result = helpers.manage_state("test_key", "test_value", "set")
        assert result is True
        
        # Get value
        result = helpers.manage_state("test_key", operation="get")
        assert result == "test_value"
        
        # List keys
        helpers.manage_state("another_key", "another_value", "set")
        keys = helpers.manage_state(None, operation="list")
        assert "test_key" in keys
        assert "another_key" in keys
        
        # Delete value
        result = helpers.manage_state("test_key", operation="delete")
        assert result is True
        
        # Verify deleted
        result = helpers.manage_state("test_key", operation="get")
        assert result is None
    
    def test_get_performance_report(self, helpers):
        """Test performance report generation."""
        # Track some operations
        with helpers.track_performance("op1"):
            time.sleep(0.05)
        
        with helpers.track_performance("op2"):
            time.sleep(0.1)
        
        report = helpers.get_performance_report()
        
        assert report["summary"]["total_operations"] == 2
        assert report["summary"]["total_duration_seconds"] >= 0.15
        assert "average_duration_seconds" in report["summary"]
        assert len(report["metrics"]) == 2
    
    def test_wait_for_run_completion_timeout(self, helpers):
        """Test run completion waiting with timeout."""
        mock_run = Mock()
        mock_run.is_finished = False
        mock_run.status.value = "STARTED"
        
        helpers.instance.get_run_by_id.return_value = mock_run
        
        with pytest.raises(TimeoutError):
            helpers._wait_for_run_completion("run-123", timeout=0.1)
    
    def test_graphql_request_error(self, helpers):
        """Test GraphQL request with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(Exception, match="HTTP Error"):
                helpers._graphql_request("query { test }")
    
    def test_get_memory_usage_without_psutil(self, helpers):
        """Test memory usage when psutil is not available."""
        with patch('daglab.helpers.notebook.psutil', side_effect=ImportError):
            memory = helpers._get_memory_usage()
            assert memory == 0.0