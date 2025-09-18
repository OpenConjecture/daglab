"""
Helper functions for DagLab notebooks.

This module provides helper functions that are available in generated notebooks
for interacting with Dagster, managing state, and tracking performance.
"""

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from dagster import DagsterInstance, RunRequest
from dagster._core.definitions.run_config import RunConfig
from dagster._core.storage.tags import RUN_METADATA_TAGS


class NotebookHelpers:
    """Container for notebook helper functions."""
    
    def __init__(self, dagster_instance: Optional[DagsterInstance] = None):
        """
        Initialize helpers with optional Dagster instance.
        
        Args:
            dagster_instance: Dagster instance to use (creates default if None)
        """
        self.instance = dagster_instance or DagsterInstance.get()
        self._state_storage = {}
        self._performance_metrics = []
    
    def run_job(
        self,
        job_name: str,
        run_config: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        wait_for_completion: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Execute a Dagster job via GraphQL.
        
        Args:
            job_name: Name of the job to run
            run_config: Configuration for the job run
            tags: Tags to attach to the run
            wait_for_completion: Whether to wait for job completion
            timeout: Maximum time to wait in seconds
            
        Returns:
            Dict containing run_id, status, and other metadata
        """
        # Prepare GraphQL mutation
        mutation = """
        mutation LaunchRun($executionParams: ExecutionParams!) {
            launchRun(executionParams: $executionParams) {
                __typename
                ... on LaunchRunSuccess {
                    run {
                        id
                        status
                        pipelineName
                        tags {
                            key
                            value
                        }
                    }
                }
                ... on RunConfigValidationError {
                    errors {
                        message
                        path
                        reason
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        """
        
        # Build execution parameters
        execution_params = {
            "selector": {
                "pipelineName": job_name,
                "repositoryLocationName": "daglab_repo",
                "repositoryName": "daglab"
            },
            "runConfigData": run_config or {},
            "tags": [{"key": k, "value": v} for k, v in (tags or {}).items()],
            "executionMetadata": {
                "runId": None,
                "tags": []
            }
        }
        
        # Execute GraphQL request
        response = self._graphql_request(mutation, {"executionParams": execution_params})
        
        if "errors" in response:
            raise RuntimeError(f"GraphQL errors: {response['errors']}")
        
        launch_result = response["data"]["launchRun"]
        
        if launch_result["__typename"] != "LaunchRunSuccess":
            raise RuntimeError(f"Launch failed: {launch_result}")
        
        run = launch_result["run"]
        run_id = run["id"]
        
        # Wait for completion if requested
        if wait_for_completion:
            status = self._wait_for_run_completion(run_id, timeout)
            run["status"] = status
        
        return {
            "run_id": run_id,
            "status": run["status"],
            "job_name": job_name,
            "tags": {tag["key"]: tag["value"] for tag in run["tags"]},
            "url": f"http://localhost:3000/instance/runs/{run_id}"
        }
    
    def run_asset(
        self,
        asset_key: Union[str, List[str]],
        partition_key: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Materialize a Dagster asset.
        
        Args:
            asset_key: Asset key or list of key components
            partition_key: Optional partition to materialize
            tags: Tags to attach to the run
            wait_for_completion: Whether to wait for completion
            
        Returns:
            Dict containing materialization details
        """
        # Normalize asset key
        if isinstance(asset_key, str):
            asset_key_list = [asset_key]
        else:
            asset_key_list = asset_key
        
        # GraphQL mutation for asset materialization
        mutation = """
        mutation LaunchAssetMaterialization($assetKeys: [AssetKeyInput!]!, $tags: [TagInput!]) {
            launchAssetMaterialization(assetKeys: $assetKeys, tags: $tags) {
                __typename
                ... on LaunchRunSuccess {
                    run {
                        id
                        status
                        tags {
                            key
                            value
                        }
                    }
                }
                ... on RunConfigValidationError {
                    errors {
                        message
                    }
                }
            }
        }
        """
        
        variables = {
            "assetKeys": [{"path": asset_key_list}],
            "tags": [{"key": k, "value": v} for k, v in (tags or {}).items()]
        }
        
        if partition_key:
            variables["tags"].append({"key": "dagster/partition", "value": partition_key})
        
        response = self._graphql_request(mutation, variables)
        
        if "errors" in response:
            raise RuntimeError(f"GraphQL errors: {response['errors']}")
        
        result = response["data"]["launchAssetMaterialization"]
        
        if result["__typename"] != "LaunchRunSuccess":
            raise RuntimeError(f"Materialization failed: {result}")
        
        run = result["run"]
        run_id = run["id"]
        
        if wait_for_completion:
            status = self._wait_for_run_completion(run_id)
            run["status"] = status
        
        return {
            "run_id": run_id,
            "status": run["status"],
            "asset_key": asset_key_list,
            "partition_key": partition_key,
            "url": f"http://localhost:3000/instance/runs/{run_id}"
        }
    
    def discover(
        self,
        entity_type: str = "all"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover Dagster entities (jobs, assets, sensors, schedules).
        
        Args:
            entity_type: Type to discover ('jobs', 'assets', 'sensors', 'schedules', 'all')
            
        Returns:
            Dict mapping entity types to lists of discovered entities
        """
        results = {}
        
        # GraphQL queries for different entity types
        queries = {
            "jobs": """
                query {
                    pipelinesOrError {
                        __typename
                        ... on PipelineConnection {
                            nodes {
                                name
                                description
                                tags {
                                    key
                                    value
                                }
                            }
                        }
                    }
                }
            """,
            "assets": """
                query {
                    assetsOrError {
                        __typename
                        ... on AssetConnection {
                            nodes {
                                key {
                                    path
                                }
                                description
                                partitionDefinition
                            }
                        }
                    }
                }
            """,
            "sensors": """
                query {
                    sensorsOrError {
                        __typename
                        ... on Sensors {
                            results {
                                name
                                description
                                status
                            }
                        }
                    }
                }
            """,
            "schedules": """
                query {
                    schedulesOrError {
                        __typename
                        ... on Schedules {
                            results {
                                name
                                description
                                status
                                cronSchedule
                            }
                        }
                    }
                }
            """
        }
        
        # Determine which queries to run
        if entity_type == "all":
            query_types = queries.keys()
        elif entity_type in queries:
            query_types = [entity_type]
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        # Execute queries
        for query_type in query_types:
            response = self._graphql_request(queries[query_type])
            
            if "errors" in response:
                results[query_type] = {"error": response["errors"]}
                continue
            
            # Extract results based on query type
            data = response["data"]
            
            if query_type == "jobs":
                if data["pipelinesOrError"]["__typename"] == "PipelineConnection":
                    results["jobs"] = data["pipelinesOrError"]["nodes"]
            elif query_type == "assets":
                if data["assetsOrError"]["__typename"] == "AssetConnection":
                    results["assets"] = [
                        {
                            "key": ".".join(node["key"]["path"]),
                            "description": node["description"],
                            "partitioned": bool(node.get("partitionDefinition"))
                        }
                        for node in data["assetsOrError"]["nodes"]
                    ]
            elif query_type == "sensors":
                if data["sensorsOrError"]["__typename"] == "Sensors":
                    results["sensors"] = data["sensorsOrError"]["results"]
            elif query_type == "schedules":
                if data["schedulesOrError"]["__typename"] == "Schedules":
                    results["schedules"] = data["schedulesOrError"]["results"]
        
        return results
    
    def attach_metadata(
        self,
        run_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Attach metadata to a Dagster run.
        
        Args:
            run_id: ID of the run
            metadata: Metadata to attach
            
        Returns:
            True if successful
        """
        try:
            run = self.instance.get_run_by_id(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            # Update run tags with metadata
            updated_tags = run.tags.copy()
            for key, value in metadata.items():
                # Prefix metadata keys
                tag_key = f"daglab.metadata.{key}"
                updated_tags[tag_key] = json.dumps(value) if not isinstance(value, str) else value
            
            # Update the run
            self.instance.add_run_tags(run_id, updated_tags)
            return True
            
        except Exception as e:
            print(f"Failed to attach metadata: {e}")
            return False
    
    def validate_config(
        self,
        job_name: str,
        run_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate run configuration for a job.
        
        Args:
            job_name: Name of the job
            run_config: Configuration to validate
            
        Returns:
            Dict with validation result and any errors
        """
        query = """
        query ValidateConfig($selector: PipelineSelector!, $runConfigData: RunConfigData!) {
            isPipelineConfigValid(pipeline: $selector, runConfigData: $runConfigData) {
                __typename
                ... on PipelineConfigValidationValid {
                    isPipelineConfigValid
                }
                ... on RunConfigValidationError {
                    errors {
                        message
                        path
                        reason
                    }
                }
            }
        }
        """
        
        variables = {
            "selector": {
                "pipelineName": job_name,
                "repositoryLocationName": "daglab_repo",
                "repositoryName": "daglab"
            },
            "runConfigData": run_config
        }
        
        response = self._graphql_request(query, variables)
        
        if "errors" in response:
            return {
                "valid": False,
                "errors": response["errors"]
            }
        
        result = response["data"]["isPipelineConfigValid"]
        
        if result["__typename"] == "PipelineConfigValidationValid":
            return {
                "valid": True,
                "errors": []
            }
        else:
            return {
                "valid": False,
                "errors": result["errors"]
            }
    
    @contextmanager
    def track_performance(self, operation_name: str):
        """
        Context manager for performance tracking.
        
        Args:
            operation_name: Name of the operation being tracked
            
        Example:
            with track_performance("data_processing"):
                # Your code here
                pass
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            metric = {
                "operation": operation_name,
                "duration_seconds": end_time - start_time,
                "memory_delta_mb": end_memory - start_memory,
                "timestamp": datetime.now().isoformat()
            }
            
            self._performance_metrics.append(metric)
            
            # Also store in state for persistence
            perf_key = f"performance.{operation_name}.{int(start_time)}"
            self._state_storage[perf_key] = metric
    
    def manage_state(
        self,
        key: str,
        value: Any = None,
        operation: str = "get"
    ) -> Any:
        """
        Manage state persistence across notebook cells.
        
        Args:
            key: State key
            value: Value to store (for set operation)
            operation: 'get', 'set', 'delete', 'list'
            
        Returns:
            State value for get, True/False for set/delete, list of keys for list
        """
        if operation == "get":
            return self._state_storage.get(key)
        elif operation == "set":
            self._state_storage[key] = value
            return True
        elif operation == "delete":
            if key in self._state_storage:
                del self._state_storage[key]
                return True
            return False
        elif operation == "list":
            return list(self._state_storage.keys())
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get a performance report for all tracked operations.
        
        Returns:
            Dict containing performance summary and metrics
        """
        if not self._performance_metrics:
            return {"message": "No performance metrics collected"}
        
        total_duration = sum(m["duration_seconds"] for m in self._performance_metrics)
        total_memory = sum(m["memory_delta_mb"] for m in self._performance_metrics)
        
        return {
            "summary": {
                "total_operations": len(self._performance_metrics),
                "total_duration_seconds": total_duration,
                "average_duration_seconds": total_duration / len(self._performance_metrics),
                "total_memory_delta_mb": total_memory
            },
            "metrics": self._performance_metrics
        }
    
    def _graphql_request(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL request against Dagster."""
        url = "http://localhost:3000/graphql"
        
        response = requests.post(
            url,
            json={
                "query": query,
                "variables": variables or {}
            },
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        return response.json()
    
    def _wait_for_run_completion(
        self,
        run_id: str,
        timeout: int = 300
    ) -> str:
        """Wait for a run to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            run = self.instance.get_run_by_id(run_id)
            
            if run.is_finished:
                return run.status.value
            
            time.sleep(2)
        
        raise TimeoutError(f"Run {run_id} did not complete within {timeout} seconds")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0


# Create singleton instance for easy import
_helpers = NotebookHelpers()

# Export helper functions
run_job = _helpers.run_job
run_asset = _helpers.run_asset
discover = _helpers.discover
attach_metadata = _helpers.attach_metadata
validate_config = _helpers.validate_config
track_performance = _helpers.track_performance
manage_state = _helpers.manage_state
get_performance_report = _helpers.get_performance_report