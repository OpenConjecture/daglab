"""Test suite for the discover command."""

import json
from unittest.mock import Mock, patch, MagicMock
import pytest
from typer.testing import CliRunner
from daglab.commands.discover import (
    app, 
    DagsterDiscoveryClient,
    filter_by_pattern,
    filter_by_tags,
    display_repositories,
    display_jobs,
    display_assets,
    display_sensors,
    display_schedules,
    export_to_json
)


runner = CliRunner()


class TestDagsterDiscoveryClient:
    """Test DagsterDiscoveryClient class."""
    
    def test_init(self):
        """Test client initialization."""
        client = DagsterDiscoveryClient(host="test", port=3001, auth_token="token123")
        assert client.host == "test"
        assert client.port == 3001
        assert client.auth_token == "token123"
        assert client.base_url == "http://test:3001"
        assert client.graphql_url == "http://test:3001/graphql"
        
    @patch('requests.post')
    def test_make_request_success(self, mock_post):
        """Test successful GraphQL request."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = DagsterDiscoveryClient()
        result = client._make_request("query { test }")
        
        assert result == {"data": {"test": "value"}}
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_make_request_with_auth(self, mock_post):
        """Test GraphQL request with authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = DagsterDiscoveryClient(auth_token="secret")
        client._make_request("query { test }")
        
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer secret"
        
    @patch('requests.post')
    def test_make_request_failure(self, mock_post):
        """Test failed GraphQL request."""
        mock_post.side_effect = Exception("Connection error")
        
        client = DagsterDiscoveryClient()
        result = client._make_request("query { test }")
        
        assert result == {}
        
    @patch('daglab.commands.discover.DagsterDiscoveryClient._make_request')
    def test_discover_repositories(self, mock_request):
        """Test repository discovery."""
        mock_request.return_value = {
            "data": {
                "repositoriesOrError": {
                    "nodes": [
                        {
                            "id": "repo1",
                            "name": "test_repo",
                            "location": {
                                "id": "loc1",
                                "name": "test_location"
                            }
                        }
                    ]
                }
            }
        }
        
        client = DagsterDiscoveryClient()
        repos = client.discover_repositories()
        
        assert len(repos) == 1
        assert repos[0]["name"] == "test_repo"
        assert repos[0]["location"]["name"] == "test_location"
        
    @patch('daglab.commands.discover.DagsterDiscoveryClient._make_request')
    def test_discover_jobs(self, mock_request):
        """Test job discovery."""
        mock_request.return_value = {
            "data": {
                "pipelinesOrError": {
                    "nodes": [
                        {
                            "id": "job1",
                            "name": "daily_etl",
                            "description": "Daily ETL job",
                            "tags": [
                                {"key": "env", "value": "prod"}
                            ],
                            "solidHandles": [
                                {
                                    "handleID": "op1",
                                    "solid": {
                                        "name": "extract",
                                        "definition": {
                                            "name": "extract_op",
                                            "description": "Extract data"
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        }
        
        client = DagsterDiscoveryClient()
        jobs = client.discover_jobs()
        
        assert len(jobs) == 1
        assert jobs[0]["name"] == "daily_etl"
        assert jobs[0]["description"] == "Daily ETL job"
        assert len(jobs[0]["tags"]) == 1
        assert len(jobs[0]["solidHandles"]) == 1
        
    @patch('daglab.commands.discover.DagsterDiscoveryClient._make_request')
    def test_discover_assets(self, mock_request):
        """Test asset discovery."""
        mock_request.return_value = {
            "data": {
                "assetsOrError": {
                    "nodes": [
                        {
                            "id": "asset1",
                            "key": {"path": ["raw", "users"]},
                            "description": "Raw user data",
                            "computeKind": "dbt",
                            "tags": [
                                {"key": "layer", "value": "bronze"}
                            ],
                            "dependencies": [
                                {
                                    "asset": {
                                        "key": {"path": ["source", "db"]}
                                    }
                                }
                            ],
                            "dependedBy": [
                                {
                                    "asset": {
                                        "key": {"path": ["clean", "users"]}
                                    }
                                }
                            ],
                            "repository": {
                                "id": "repo1",
                                "name": "data_pipeline",
                                "location": {
                                    "id": "loc1",
                                    "name": "prod"
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        client = DagsterDiscoveryClient()
        assets = client.discover_assets()
        
        assert len(assets) == 1
        assert assets[0]["key"]["path"] == ["raw", "users"]
        assert assets[0]["computeKind"] == "dbt"
        assert len(assets[0]["dependencies"]) == 1
        assert len(assets[0]["dependedBy"]) == 1
        
    @patch('daglab.commands.discover.DagsterDiscoveryClient._make_request')
    def test_discover_sensors(self, mock_request):
        """Test sensor discovery."""
        mock_request.return_value = {
            "data": {
                "sensorsOrError": {
                    "results": [
                        {
                            "id": "sensor1",
                            "name": "file_watcher",
                            "description": "Watch for new files",
                            "sensorType": "STANDARD",
                            "targets": [
                                {
                                    "pipelineName": "process_file",
                                    "mode": "default"
                                }
                            ],
                            "sensorState": {
                                "id": "state1",
                                "status": "RUNNING"
                            }
                        }
                    ]
                }
            }
        }
        
        client = DagsterDiscoveryClient()
        sensors = client.discover_sensors()
        
        assert len(sensors) == 1
        assert sensors[0]["name"] == "file_watcher"
        assert sensors[0]["sensorType"] == "STANDARD"
        assert sensors[0]["sensorState"]["status"] == "RUNNING"
        
    @patch('daglab.commands.discover.DagsterDiscoveryClient._make_request')
    def test_discover_schedules(self, mock_request):
        """Test schedule discovery."""
        mock_request.return_value = {
            "data": {
                "schedulesOrError": {
                    "results": [
                        {
                            "id": "schedule1",
                            "name": "daily_refresh",
                            "description": "Daily data refresh",
                            "cronSchedule": "0 1 * * *",
                            "pipelineName": "refresh_pipeline",
                            "mode": "default",
                            "scheduleState": {
                                "id": "state1",
                                "status": "RUNNING"
                            }
                        }
                    ]
                }
            }
        }
        
        client = DagsterDiscoveryClient()
        schedules = client.discover_schedules()
        
        assert len(schedules) == 1
        assert schedules[0]["name"] == "daily_refresh"
        assert schedules[0]["cronSchedule"] == "0 1 * * *"
        assert schedules[0]["scheduleState"]["status"] == "RUNNING"


class TestFilterFunctions:
    """Test filtering functions."""
    
    def test_filter_by_pattern(self):
        """Test pattern filtering."""
        items = [
            {"name": "daily_etl"},
            {"name": "weekly_report"},
            {"name": "daily_backup"},
            {"name": "monthly_aggregate"}
        ]
        
        # Test wildcard pattern
        filtered = filter_by_pattern(items, "daily_*", "name")
        assert len(filtered) == 2
        assert all("daily_" in item["name"] for item in filtered)
        
        # Test partial match
        filtered = filter_by_pattern(items, "*report", "name")
        assert len(filtered) == 1
        assert filtered[0]["name"] == "weekly_report"
        
        # Test no pattern
        filtered = filter_by_pattern(items, None, "name")
        assert len(filtered) == 4
        
    def test_filter_by_tags(self):
        """Test tag filtering."""
        items = [
            {
                "name": "job1",
                "tags": [
                    {"key": "env", "value": "prod"},
                    {"key": "team", "value": "data"}
                ]
            },
            {
                "name": "job2",
                "tags": [
                    {"key": "env", "value": "dev"},
                    {"key": "team", "value": "data"}
                ]
            },
            {
                "name": "job3",
                "tags": [
                    {"key": "env", "value": "prod"},
                    {"key": "team", "value": "analytics"}
                ]
            }
        ]
        
        # Filter by single tag
        filtered = filter_by_tags(items, ["env=prod"])
        assert len(filtered) == 2
        assert all(any(t["key"] == "env" and t["value"] == "prod" 
                      for t in item["tags"]) for item in filtered)
        
        # Filter by multiple tags
        filtered = filter_by_tags(items, ["env=prod", "team=data"])
        assert len(filtered) == 1
        assert filtered[0]["name"] == "job1"
        
        # Filter by tag existence
        filtered = filter_by_tags(items, ["env"])
        assert len(filtered) == 3
        
        # No tags
        filtered = filter_by_tags(items, None)
        assert len(filtered) == 3


class TestDisplayFunctions:
    """Test display functions."""
    
    def test_display_repositories(self, capsys):
        """Test repository display."""
        repos = [
            {
                "id": "repo1",
                "name": "test_repo",
                "location": {
                    "id": "loc1",
                    "name": "test_location"
                }
            }
        ]
        
        display_repositories(repos, verbose=False)
        captured = capsys.readouterr()
        assert "test_repo" in captured.out
        assert "test_location" in captured.out
        assert "..." in captured.out
        
        # Test verbose mode
        display_repositories(repos, verbose=True)
        captured = capsys.readouterr()
        assert "repo1" in captured.out
        
    def test_display_jobs(self, capsys):
        """Test job display."""
        jobs = [
            {
                "name": "daily_etl",
                "description": "Daily ETL job",
                "tags": [
                    {"key": "env", "value": "prod"}
                ],
                "solidHandles": [
                    {
                        "solid": {
                            "name": "extract",
                            "definition": {
                                "description": "Extract data"
                            }
                        }
                    },
                    {
                        "solid": {
                            "name": "transform",
                            "definition": {}
                        }
                    }
                ]
            }
        ]
        
        display_jobs(jobs, verbose=False)
        captured = capsys.readouterr()
        assert "daily_etl" in captured.out
        assert "Daily ETL job" in captured.out
        assert "env=prod" in captured.out
        assert "2" in captured.out  # ops count
        
        # Test verbose mode
        display_jobs(jobs, verbose=True)
        captured = capsys.readouterr()
        assert "extract" in captured.out
        assert "Extract data" in captured.out
        assert "transform" in captured.out
        
    def test_display_assets(self, capsys):
        """Test asset display."""
        assets = [
            {
                "key": {"path": ["raw", "users"]},
                "computeKind": "dbt",
                "description": "Raw user data",
                "tags": [
                    {"key": "layer", "value": "bronze"}
                ],
                "dependencies": [
                    {"asset": {"key": {"path": ["source", "db"]}}},
                    {"asset": {"key": {"path": ["source", "api"]}}}
                ],
                "dependedBy": [
                    {"asset": {"key": {"path": ["clean", "users"]}}}
                ]
            }
        ]
        
        display_assets(assets, verbose=False)
        captured = capsys.readouterr()
        assert "raw.users" in captured.out
        assert "dbt" in captured.out
        assert "source.db" in captured.out
        assert "clean.users" in captured.out
        assert "layer=bronze" in captured.out
        
        # Test verbose mode
        display_assets(assets, verbose=True)
        captured = capsys.readouterr()
        assert "Raw user data" in captured.out
        assert "Dependencies:" in captured.out
        assert "Used by:" in captured.out


class TestCLI:
    """Test CLI interface."""
    
    @patch('requests.get')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_repositories')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_jobs')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_assets')
    def test_discover_all(self, mock_assets, mock_jobs, mock_repos, mock_get):
        """Test discovering all entities."""
        # Mock connection check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Mock discovery results
        mock_repos.return_value = [{"name": "test_repo", "location": {"name": "test_loc"}, "id": "1"}]
        mock_jobs.return_value = [{"name": "test_job", "tags": [], "solidHandles": []}]
        mock_assets.return_value = [{"key": {"path": ["test", "asset"]}, "dependencies": [], "dependedBy": [], "tags": []}]
        
        with patch('subprocess.run'):
            result = runner.invoke(app, ["--filter", "all"])
        
        assert result.exit_code == 0
        assert "Discovering Dagster entities" in result.output
        assert "test_repo" in result.output
        assert "test_job" in result.output
        assert "test.asset" in result.output
        assert "Discovery Summary" in result.output
        
    @patch('requests.get')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_assets')
    def test_discover_assets_with_pattern(self, mock_assets, mock_get):
        """Test discovering assets with pattern filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        mock_assets.return_value = [
            {"key": {"path": ["daily", "sales"]}, "tags": [], "dependencies": [], "dependedBy": []},
            {"key": {"path": ["weekly", "report"]}, "tags": [], "dependencies": [], "dependedBy": []},
            {"key": {"path": ["daily", "inventory"]}, "tags": [], "dependencies": [], "dependedBy": []}
        ]
        
        with patch('subprocess.run'):
            result = runner.invoke(app, ["--filter", "assets", "--pattern", "daily.*"])
        
        assert result.exit_code == 0
        assert "daily.sales" in result.output
        assert "daily.inventory" in result.output
        assert "weekly.report" not in result.output
        
    @patch('requests.get')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_jobs')
    def test_discover_jobs_with_tags(self, mock_jobs, mock_get):
        """Test discovering jobs with tag filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        mock_jobs.return_value = [
            {
                "name": "prod_job",
                "tags": [{"key": "env", "value": "prod"}],
                "solidHandles": []
            },
            {
                "name": "dev_job",
                "tags": [{"key": "env", "value": "dev"}],
                "solidHandles": []
            }
        ]
        
        with patch('subprocess.run'):
            result = runner.invoke(app, ["--filter", "jobs", "--tags", "env=prod"])
        
        assert result.exit_code == 0
        assert "prod_job" in result.output
        assert "dev_job" not in result.output
        
    @patch('requests.get')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_assets')
    def test_discover_json_output(self, mock_assets, mock_get):
        """Test JSON output format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        mock_assets.return_value = [
            {"key": {"path": ["test", "asset"]}, "tags": [], "dependencies": [], "dependedBy": []}
        ]
        
        with patch('subprocess.run'):
            result = runner.invoke(app, ["--filter", "assets", "--json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output = result.output
        json_start = output.find('{')
        json_data = json.loads(output[json_start:])
        
        assert json_data["filter"] == "assets"
        assert len(json_data["entities"]["assets"]) == 1
        assert json_data["entities"]["assets"][0]["key"]["path"] == ["test", "asset"]
        
    @patch('requests.get')
    def test_discover_connection_error(self, mock_get):
        """Test handling connection errors."""
        mock_get.side_effect = Exception("Connection refused")
        
        result = runner.invoke(app, ["--filter", "all"])
        
        assert result.exit_code == 1
        assert "Cannot connect to Dagster" in result.output
        assert "Make sure Dagster is running" in result.output
        
    @patch('requests.get')
    @patch('daglab.commands.discover.DagsterDiscoveryClient.discover_assets')
    @patch('pathlib.Path.write_text')
    def test_discover_export_to_file(self, mock_write, mock_assets, mock_get):
        """Test exporting results to file."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        mock_assets.return_value = [
            {"key": {"path": ["test", "asset"]}, "tags": [], "dependencies": [], "dependedBy": []}
        ]
        
        with patch('subprocess.run'):
            result = runner.invoke(app, [
                "--filter", "assets",
                "--json",
                "--output", "entities.json"
            ])
        
        assert result.exit_code == 0
        assert "Exported to entities.json" in result.output
        
        # Check that file write was called
        mock_write.assert_called_once()
        written_data = mock_write.call_args[0][0]
        json_data = json.loads(written_data)
        assert len(json_data["entities"]["assets"]) == 1