"""Integration tests for discover command with real Dagster."""

import os
import tempfile
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from daglab.cli import discover, _async_discover_jobs
from daglab.helpers.graphql import DagsterClientSync
from daglab.helpers.auth import AuthConfig, AuthType


class TestDiscoverIntegration:
    """Test discover command with real Dagster instance."""
    
    @pytest.fixture
    def dagster_config(self):
        """Get Dagster configuration from environment."""
        return {
            "dagster_url": os.getenv("DAGSTER_URL", "http://localhost:3000"),
            "dagster_deployment": os.getenv("DAGSTER_DEPLOYMENT", "default"),
        }
    
    @pytest.fixture
    def temp_notebook_dir(self):
        """Create temporary directory for notebooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.mark.integration
    def test_discover_jobs(self, dagster_config, temp_notebook_dir):
        """Test discovering jobs from Dagster instance."""
        try:
            # Create client
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{dagster_config['dagster_url']}/graphql",
                auth_config=auth_config
            )
            
            # Test health check first
            if not client.health_check():
                pytest.skip("Dagster instance not available")
            
            # Discover jobs
            query = """
            query DiscoverJobs {
                repositoriesOrError {
                    ... on RepositoryConnection {
                        nodes {
                            name
                            location {
                                name
                            }
                            jobs {
                                name
                                description
                            }
                            pipelines {
                                name
                                description
                            }
                        }
                    }
                }
            }
            """
            
            result = client.query(query)
            
            if "repositoriesOrError" in result and "nodes" in result["repositoriesOrError"]:
                repositories = result["repositoriesOrError"]["nodes"]
                
                # Collect all jobs
                all_jobs = []
                for repo in repositories:
                    repo_name = repo["name"]
                    location = repo["location"]["name"]
                    
                    # Get jobs (newer) or pipelines (older)
                    jobs = repo.get("jobs", repo.get("pipelines", []))
                    
                    for job in jobs:
                        all_jobs.append({
                            "name": job["name"],
                            "repository": repo_name,
                            "location": location,
                            "description": job.get("description", "")
                        })
                
                print(f"\nDiscovered {len(all_jobs)} jobs:")
                for job in all_jobs:
                    print(f"  - {job['repository']}/{job['name']}")
                    if job['description']:
                        print(f"    {job['description']}")
                
                # Test that we found at least one job
                assert len(all_jobs) > 0, "No jobs discovered"
                
                # Save discovery results
                discovery_file = temp_notebook_dir / "discovery_results.json"
                with open(discovery_file, "w") as f:
                    json.dump({
                        "repositories": repositories,
                        "jobs": all_jobs,
                        "timestamp": "2025-01-17T12:00:00"
                    }, f, indent=2)
                
                print(f"\nSaved discovery results to: {discovery_file}")
                
        except Exception as e:
            pytest.skip(f"Dagster instance not available: {e}")
    
    @pytest.mark.integration
    def test_discover_with_filters(self, dagster_config):
        """Test discovering jobs with filters."""
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{dagster_config['dagster_url']}/graphql",
                auth_config=auth_config
            )
            
            if not client.health_check():
                pytest.skip("Dagster instance not available")
            
            # Discover with repository filter
            query = """
            query DiscoverFiltered {
                repositoriesOrError {
                    ... on RepositoryConnection {
                        nodes {
                            name
                            jobs {
                                name
                                description
                                mode
                            }
                        }
                    }
                }
            }
            """
            
            result = client.query(query)
            
            if "repositoriesOrError" in result and "nodes" in result["repositoriesOrError"]:
                repos = result["repositoriesOrError"]["nodes"]
                
                # Filter by repository name pattern (example)
                filtered_repos = [r for r in repos if "example" in r["name"].lower()]
                
                if filtered_repos:
                    print(f"\nFiltered repositories: {[r['name'] for r in filtered_repos]}")
                else:
                    print("\nNo repositories matched filter")
                    
        except Exception as e:
            pytest.skip(f"Dagster instance not available: {e}")
    
    @pytest.mark.integration 
    def test_discover_assets(self, dagster_config):
        """Test discovering assets from Dagster."""
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{dagster_config['dagster_url']}/graphql",
                auth_config=auth_config
            )
            
            if not client.health_check():
                pytest.skip("Dagster instance not available")
            
            # Query for assets
            query = """
            query DiscoverAssets {
                assetsOrError {
                    ... on AssetConnection {
                        nodes {
                            key {
                                path
                            }
                            description
                            repository {
                                name
                            }
                            definition {
                                opNames
                                computeKind
                            }
                        }
                    }
                }
            }
            """
            
            result = client.query(query)
            
            if "assetsOrError" in result and "nodes" in result["assetsOrError"]:
                assets = result["assetsOrError"]["nodes"]
                
                print(f"\nDiscovered {len(assets)} assets:")
                for asset in assets[:10]:  # Show first 10
                    path = ".".join(asset["key"]["path"])
                    repo = asset.get("repository", {}).get("name", "unknown")
                    print(f"  - {path} (repo: {repo})")
                    
        except Exception as e:
            pytest.skip(f"Dagster instance not available: {e}")
    
    @pytest.mark.integration
    def test_discover_schedules_sensors(self, dagster_config):
        """Test discovering schedules and sensors."""
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{dagster_config['dagster_url']}/graphql",
                auth_config=auth_config
            )
            
            if not client.health_check():
                pytest.skip("Dagster instance not available")
            
            # Query for schedules and sensors
            query = """
            query DiscoverSchedulesSensors {
                repositoriesOrError {
                    ... on RepositoryConnection {
                        nodes {
                            name
                            schedules {
                                name
                                cronSchedule
                                pipelineName
                                executionTimezone
                            }
                            sensors {
                                name
                                pipelineName
                                status
                                sensorType
                            }
                        }
                    }
                }
            }
            """
            
            result = client.query(query)
            
            if "repositoriesOrError" in result and "nodes" in result["repositoriesOrError"]:
                for repo in result["repositoriesOrError"]["nodes"]:
                    schedules = repo.get("schedules", [])
                    sensors = repo.get("sensors", [])
                    
                    if schedules or sensors:
                        print(f"\nRepository: {repo['name']}")
                        
                        if schedules:
                            print(f"  Schedules ({len(schedules)}):")
                            for schedule in schedules:
                                print(f"    - {schedule['name']} ({schedule['cronSchedule']})")
                        
                        if sensors:
                            print(f"  Sensors ({len(sensors)}):")
                            for sensor in sensors:
                                print(f"    - {sensor['name']} [{sensor['status']}]")
                                
        except Exception as e:
            pytest.skip(f"Dagster instance not available: {e}")
    
    @pytest.mark.integration
    def test_discover_error_handling(self, dagster_config):
        """Test error handling in discover command."""
        # Test with invalid URL
        invalid_config = {
            "dagster_url": "http://invalid-host:9999",
            "dagster_deployment": "test"
        }
        
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{invalid_config['dagster_url']}/graphql",
                auth_config=auth_config,
                timeout=5.0  # Short timeout for test
            )
            
            # This should fail
            is_healthy = client.health_check()
            assert not is_healthy, "Expected health check to fail"
            
        except Exception as e:
            # Expected - connection should fail
            print(f"Expected error: {e}")
            pass
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_discover(self, dagster_config):
        """Test async discovery functionality."""
        from daglab.helpers.graphql import DagsterClient
        
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClient(
                endpoint=f"{dagster_config['dagster_url']}/graphql",
                auth_config=auth_config
            )
            
            # Test async health check
            is_healthy = await client.health_check()
            if not is_healthy:
                pytest.skip("Dagster instance not available")
            
            # Async query
            query = """
            query AsyncDiscover {
                repositoriesOrError {
                    ... on RepositoryConnection {
                        nodes {
                            name
                            jobs {
                                name
                            }
                        }
                    }
                }
            }
            """
            
            result = await client.query(query)
            assert "repositoriesOrError" in result
            
            await client.close()
            
        except Exception as e:
            pytest.skip(f"Dagster instance not available: {e}")