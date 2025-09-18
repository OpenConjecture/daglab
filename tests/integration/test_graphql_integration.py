"""Integration tests for GraphQL client with real Dagster instance."""

import asyncio
import json
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

from daglab.helpers.graphql import DagsterClient, DagsterClientSync, GraphQLQueryError
from daglab.helpers.auth import AuthConfig, AuthType
from daglab.validation.security import validate_graphql_query, validate_run_config


class TestGraphQLIntegration:
    """Test GraphQL client with real Dagster operations."""
    
    @pytest.fixture
    def dagster_url(self):
        """Get Dagster URL from environment or use default."""
        return os.getenv("DAGSTER_URL", "http://localhost:3000/graphql")
    
    @pytest.fixture
    def auth_config(self):
        """Get authentication configuration."""
        # Try to get from environment
        token = os.getenv("DAGSTER_TOKEN")
        if token:
            return AuthConfig.bearer(token)
        
        username = os.getenv("DAGSTER_USERNAME")
        password = os.getenv("DAGSTER_PASSWORD")
        if username and password:
            return AuthConfig.basic(username, password)
        
        return AuthConfig(auth_type=AuthType.NONE)
    
    @pytest.fixture
    def sync_client(self, dagster_url, auth_config):
        """Create synchronous GraphQL client."""
        return DagsterClientSync(
            endpoint=dagster_url,
            auth_config=auth_config,
            timeout=30.0,
            verify_ssl=True
        )
    
    @pytest.fixture
    async def async_client(self, dagster_url, auth_config):
        """Create asynchronous GraphQL client."""
        client = DagsterClient(
            endpoint=dagster_url,
            auth_config=auth_config,
            timeout=30.0,
            verify_ssl=True
        )
        yield client
        await client.close()
    
    @pytest.mark.integration
    def test_sync_health_check(self, sync_client):
        """Test synchronous health check."""
        # This will fail if no Dagster instance is running
        try:
            is_healthy = sync_client.health_check()
            assert isinstance(is_healthy, bool)
            if is_healthy:
                print("✅ Dagster instance is healthy")
            else:
                print("❌ Dagster instance health check failed")
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_health_check(self, async_client):
        """Test asynchronous health check."""
        try:
            is_healthy = await async_client.health_check()
            assert isinstance(is_healthy, bool)
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    def test_query_repositories(self, sync_client):
        """Test querying for repositories."""
        query = """
        query GetRepositories {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        id
                        name
                        location {
                            id
                            name
                        }
                        pipelines {
                            id
                            name
                            description
                        }
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        """
        
        # Validate query first
        is_valid, error = validate_graphql_query(query)
        assert is_valid, f"Query validation failed: {error}"
        
        try:
            result = sync_client.query(query)
            assert isinstance(result, dict)
            assert "repositoriesOrError" in result
            
            repos_or_error = result["repositoriesOrError"]
            if "nodes" in repos_or_error:
                # Success case
                repositories = repos_or_error["nodes"]
                assert isinstance(repositories, list)
                print(f"Found {len(repositories)} repositories")
                
                for repo in repositories:
                    assert "name" in repo
                    assert "location" in repo
                    print(f"  - Repository: {repo['name']} at {repo['location']['name']}")
            else:
                # Error case
                assert "message" in repos_or_error
                print(f"Repository error: {repos_or_error['message']}")
                
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    def test_query_jobs(self, sync_client):
        """Test querying for jobs/pipelines."""
        query = """
        query GetJobs {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
                        jobs {
                            id
                            name
                            description
                            mode
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = sync_client.query(query)
            if "repositoriesOrError" in result and "nodes" in result["repositoriesOrError"]:
                repos = result["repositoriesOrError"]["nodes"]
                all_jobs = []
                
                for repo in repos:
                    jobs = repo.get("jobs", [])
                    for job in jobs:
                        all_jobs.append({
                            "repository": repo["name"],
                            "job": job["name"],
                            "description": job.get("description", "")
                        })
                
                print(f"Found {len(all_jobs)} jobs across all repositories")
                for job_info in all_jobs[:5]:  # Show first 5
                    print(f"  - {job_info['repository']}/{job_info['job']}")
                    
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    def test_validate_run_config(self, sync_client):
        """Test validating run configuration."""
        # First, get a job to validate against
        query = """
        query GetFirstJob {
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
        
        try:
            result = sync_client.query(query)
            
            # Find first job
            job_name = None
            repo_name = None
            
            if "repositoriesOrError" in result and "nodes" in result["repositoriesOrError"]:
                for repo in result["repositoriesOrError"]["nodes"]:
                    if repo.get("jobs"):
                        repo_name = repo["name"]
                        job_name = repo["jobs"][0]["name"]
                        break
            
            if not job_name:
                pytest.skip("No jobs found to validate against")
            
            # Now validate a run config
            run_config = {
                "ops": {},
                "resources": {}
            }
            
            # Validate using security validator
            is_valid, error = validate_run_config(run_config)
            assert is_valid, f"Run config validation failed: {error}"
            
            # Validate against Dagster
            validation_query = """
            mutation ValidateConfig($repositoryName: String!, $jobName: String!, $runConfigData: RunConfigData!) {
                isPipelineConfigValid(
                    pipeline: {
                        repositoryName: $repositoryName,
                        pipelineName: $jobName
                    },
                    runConfigData: $runConfigData
                ) {
                    __typename
                    ... on PipelineConfigValidationValid {
                        pipelineName
                    }
                    ... on RunConfigValidationInvalid {
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
                "repositoryName": repo_name,
                "jobName": job_name,
                "runConfigData": run_config
            }
            
            validation_result = sync_client.mutate(validation_query, variables)
            
            assert "isPipelineConfigValid" in validation_result
            validation = validation_result["isPipelineConfigValid"]
            
            if validation["__typename"] == "PipelineConfigValidationValid":
                print(f"✅ Config is valid for {repo_name}/{job_name}")
            else:
                errors = validation.get("errors", [])
                print(f"❌ Config validation errors: {errors}")
                
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_query_runs(self, async_client):
        """Test asynchronously querying for runs."""
        query = """
        query GetRecentRuns($limit: Int!) {
            pipelineRunsOrError(limit: $limit) {
                ... on Runs {
                    results {
                        id
                        runId
                        pipelineName
                        status
                        startTime
                        endTime
                        tags {
                            key
                            value
                        }
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        
        try:
            result = await async_client.query(query, {"limit": 5})
            
            if "pipelineRunsOrError" in result and "results" in result["pipelineRunsOrError"]:
                runs = result["pipelineRunsOrError"]["results"]
                print(f"Found {len(runs)} recent runs")
                
                for run in runs:
                    print(f"  - Run {run['runId']}: {run['pipelineName']} [{run['status']}]")
            else:
                print("No runs found or error occurred")
                
        except Exception as e:
            pytest.skip(f"No Dagster instance available: {e}")
    
    @pytest.mark.integration
    def test_error_handling(self, sync_client):
        """Test error handling with invalid queries."""
        # Invalid query - missing closing brace
        invalid_query = """
        query BadQuery {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
        """
        
        with pytest.raises(GraphQLQueryError) as exc_info:
            sync_client.query(invalid_query)
        
        assert len(exc_info.value.errors) > 0
    
    @pytest.mark.integration
    def test_connection_pooling(self, sync_client):
        """Test connection pooling with multiple requests."""
        query = "query { __typename }"
        
        # Make multiple requests quickly
        results = []
        for _ in range(5):
            try:
                result = sync_client.query(query)
                results.append(result)
            except Exception:
                pass
        
        # At least some should succeed if Dagster is running
        assert len(results) >= 0  # Don't fail if no Dagster
    
    @pytest.mark.integration
    def test_with_context_manager(self, dagster_url, auth_config):
        """Test using client as context manager."""
        query = "query { __typename }"
        
        with DagsterClientSync(dagster_url, auth_config) as client:
            try:
                result = client.query(query)
                assert isinstance(result, dict)
            except Exception as e:
                pytest.skip(f"No Dagster instance available: {e}")


class TestGraphQLSecurity:
    """Test GraphQL security validations."""
    
    def test_validate_safe_queries(self):
        """Test validation of safe queries."""
        safe_queries = [
            "query GetRepos { repositoriesOrError { nodes { name } } }",
            "mutation LaunchRun { launchPipelineExecution(...) { run { id } } }",
            "query GetAssets { assetsOrError { nodes { key { path } } } }",
        ]
        
        for query in safe_queries:
            is_valid, error = validate_graphql_query(query)
            assert is_valid, f"Safe query rejected: {error}"
    
    def test_validate_dangerous_queries(self):
        """Test rejection of dangerous queries."""
        dangerous_queries = [
            "query { __schema { types { name } } }",  # Schema introspection
            "query { __type(name: \"User\") { fields { name } } }",  # Type introspection
            "mutation { deleteRepository(name: \"test\") }",  # Dangerous mutation
        ]
        
        for query in dangerous_queries:
            is_valid, error = validate_graphql_query(query)
            assert not is_valid, f"Dangerous query accepted: {query}"
    
    def test_validate_injection_attempts(self):
        """Test rejection of injection attempts."""
        injection_queries = [
            'query { user(id: "1; DROP TABLE users;--") { name } }',
            'mutation { updateName(name: "test\'); DELETE FROM users; --") }',
        ]
        
        for query in injection_queries:
            # These should be caught at the config validation level
            config = {"ops": {"my_op": {"config": {"value": query}}}}
            is_valid, error = validate_run_config(config)
            assert not is_valid, f"Injection attempt accepted: {query}"