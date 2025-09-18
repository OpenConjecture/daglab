"""Unit tests for Dagster GraphQL client."""
import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import httpx

from daglab.helpers import (
    DagsterClient,
    DagsterClientSync,
    DagsterClientError,
    GraphQLQueryError,
    AuthConfig,
    AuthType,
    BearerAuthProvider,
    BasicAuthProvider,
    TokenManager,
    GraphQLResponse,
    GraphQLError,
    RunInfo,
    RunStatus,
    RepositoryInfo,
    JobInfo,
    AssetInfo,
    AssetKey,
    Queries,
    Mutations,
    build_repository_selector,
    build_pipeline_selector,
    build_execution_params,
)


class TestDagsterClient:
    """Test cases for DagsterClient."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return DagsterClient(endpoint="http://localhost:3000/graphql")
    
    @pytest.fixture
    def auth_client(self):
        """Create a test client with authentication."""
        auth_config = AuthConfig.bearer("test-token")
        return DagsterClient(
            endpoint="http://localhost:3000/graphql",
            auth_config=auth_config
        )
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        client = DagsterClient(
            endpoint="http://localhost:3000/graphql",
            timeout=60.0,
            max_connections=20,
            verify_ssl=False,
        )
        
        assert client.endpoint == "http://localhost:3000/graphql"
        assert client.timeout == 60.0
        assert client.verify_ssl is False
        assert client.limits.max_connections == 20
    
    @pytest.mark.asyncio
    async def test_auth_config_from_env(self, monkeypatch):
        """Test auth config from environment variables."""
        # Test bearer auth
        monkeypatch.setenv("DAGSTER_TOKEN", "env-token")
        auth_config = AuthConfig.from_env()
        
        assert auth_config.auth_type == AuthType.BEARER
        headers = auth_config.get_headers()
        assert headers["Authorization"] == "Bearer env-token"
        
        # Test basic auth
        monkeypatch.delenv("DAGSTER_TOKEN")
        monkeypatch.setenv("DAGSTER_USERNAME", "user")
        monkeypatch.setenv("DAGSTER_PASSWORD", "pass")
        auth_config = AuthConfig.from_env()
        
        assert auth_config.auth_type == AuthType.BASIC
        headers = auth_config.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
    
    @pytest.mark.asyncio
    async def test_execute_query_success(self, client):
        """Test successful query execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "version": "1.7.0"
            }
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            response = await client.execute("query { version }")
            
            assert response.data == {"version": "1.7.0"}
            assert response.errors == []
            assert response.is_success
    
    @pytest.mark.asyncio
    async def test_execute_query_with_errors(self, client):
        """Test query execution with GraphQL errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": None,
            "errors": [
                {
                    "message": "Field 'invalid' not found",
                    "path": ["query", "invalid"],
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            with pytest.raises(GraphQLQueryError) as exc_info:
                await client.execute("query { invalid }")
            
            assert "GraphQL query failed" in str(exc_info.value)
            assert len(exc_info.value.errors) == 1
    
    @pytest.mark.asyncio
    async def test_execute_http_error(self, client):
        """Test query execution with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=mock_response
        )
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            with pytest.raises(DagsterClientError) as exc_info:
                await client.execute("query { version }")
            
            assert "HTTP 401" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_method(self, client):
        """Test query convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"repositories": [{"name": "test"}]}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            data = await client.query(Queries.GET_REPOSITORIES)
            
            assert data == {"repositories": [{"name": "test"}]}
    
    @pytest.mark.asyncio
    async def test_mutate_method(self, client):
        """Test mutate convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "launchRun": {
                    "__typename": "LaunchRunSuccess",
                    "run": {"runId": "test-run-id"}
                }
            }
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            data = await client.mutate(
                Mutations.LAUNCH_RUN,
                variables={"executionParams": {}}
            )
            
            assert data["launchRun"]["run"]["runId"] == "test-run-id"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"version": "1.7.0"}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            is_healthy = await client.health_check()
            
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test failed health check."""
        with patch.object(client, "query") as mock_query:
            mock_query.side_effect = Exception("Connection failed")
            
            is_healthy = await client.health_check()
            
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_client_close(self, client):
        """Test client close."""
        # Create a mock client
        mock_http_client = AsyncMock()
        client._client = mock_http_client
        
        await client.close()
        
        mock_http_client.aclose.assert_called_once()
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, client):
        """Test retry logic on timeout."""
        # First two attempts fail with timeout, third succeeds
        attempts = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise httpx.TimeoutException("Request timed out")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"version": "1.7.0"}}
            mock_response.raise_for_status = Mock()
            return mock_response
        
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = mock_post
            mock_get_client.return_value = mock_client
            
            # Should succeed after retries
            response = await client.execute("query { version }")
            assert response.data == {"version": "1.7.0"}
            assert attempts == 3


class TestDagsterClientSync:
    """Test cases for synchronous client wrapper."""
    
    def test_sync_query(self):
        """Test synchronous query execution."""
        client = DagsterClientSync(endpoint="http://localhost:3000/graphql")
        
        # Mock the async client
        mock_response = GraphQLResponse(data={"version": "1.7.0"})
        
        with patch.object(client._client, "query", return_value=mock_response):
            with patch.object(client, "_run_async", return_value={"version": "1.7.0"}):
                data = client.query("query { version }")
                assert data == {"version": "1.7.0"}
    
    def test_sync_context_manager(self):
        """Test synchronous client as context manager."""
        with DagsterClientSync(endpoint="http://localhost:3000/graphql") as client:
            assert isinstance(client, DagsterClientSync)
        
        # Client should be closed after context


class TestAuthProviders:
    """Test cases for authentication providers."""
    
    def test_bearer_auth_provider(self):
        """Test bearer authentication provider."""
        provider = BearerAuthProvider(token="test-token")
        headers = provider.get_headers()
        
        assert headers["Authorization"] == "Bearer test-token"
    
    def test_bearer_auth_with_custom_header(self):
        """Test bearer auth with custom header name."""
        provider = BearerAuthProvider(
            token="test-token",
            header_name="X-API-Key",
            prefix=""
        )
        headers = provider.get_headers()
        
        assert headers["X-API-Key"] == "test-token"
    
    def test_basic_auth_provider(self):
        """Test basic authentication provider."""
        provider = BasicAuthProvider(username="user", password="pass")
        headers = provider.get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        
        # Decode and verify
        import base64
        encoded = headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "user:pass"
    
    def test_custom_auth_provider(self):
        """Test custom header authentication provider."""
        custom_headers = {
            "X-API-Key": "api-key",
            "X-Custom": "value"
        }
        provider = CustomAuthProvider(headers=custom_headers)
        headers = provider.get_headers()
        
        assert headers == custom_headers
    
    def test_token_manager(self):
        """Test token manager with caching."""
        mock_provider = Mock()
        mock_provider.get_token.return_value = "token-1"
        
        manager = TokenManager(
            token_provider=mock_provider,
            cache_ttl=3600.0
        )
        
        # First call should fetch from provider
        token = manager.get_token()
        assert token == "token-1"
        mock_provider.get_token.assert_called_once()
        
        # Second call should use cache
        token = manager.get_token()
        assert token == "token-1"
        assert mock_provider.get_token.call_count == 1
        
        # Clear cache and fetch again
        manager.clear_cache()
        mock_provider.get_token.return_value = "token-2"
        token = manager.get_token()
        assert token == "token-2"
        assert mock_provider.get_token.call_count == 2


class TestModels:
    """Test cases for response models."""
    
    def test_asset_key(self):
        """Test AssetKey model."""
        key = AssetKey(path=["my", "asset", "key"])
        assert key.to_string == "my.asset.key"
        
        key2 = AssetKey.from_string("another.asset")
        assert key2.path == ["another", "asset"]
    
    def test_run_info(self):
        """Test RunInfo model."""
        run = RunInfo(
            runId="test-run",
            pipelineName="test-pipeline",
            mode="default",
            status=RunStatus.SUCCESS,
            startTime=1000.0,
            endTime=2000.0
        )
        
        assert run.is_finished
        assert not run.is_running
        assert run.duration == 1000.0
    
    def test_graphql_response(self):
        """Test GraphQLResponse model."""
        # Success response
        response = GraphQLResponse(data={"test": "data"})
        assert response.is_success
        assert not response.has_errors
        
        # Error response
        error_response = GraphQLResponse(
            errors=[GraphQLError(message="Test error")]
        )
        assert error_response.has_errors
        assert not error_response.is_success


class TestQueryBuilders:
    """Test cases for query builder functions."""
    
    def test_build_repository_selector(self):
        """Test repository selector builder."""
        selector = build_repository_selector(
            repository_name="test-repo",
            repository_location_name="test-location"
        )
        
        assert selector == {
            "repositoryName": "test-repo",
            "repositoryLocationName": "test-location"
        }
    
    def test_build_pipeline_selector(self):
        """Test pipeline selector builder."""
        selector = build_pipeline_selector(
            pipeline_name="test-pipeline",
            repository_name="test-repo",
            repository_location_name="test-location",
            solid_selection=["solid1", "solid2"]
        )
        
        assert selector == {
            "pipelineName": "test-pipeline",
            "repositoryName": "test-repo",
            "repositoryLocationName": "test-location",
            "solidSelection": ["solid1", "solid2"]
        }
    
    def test_build_execution_params(self):
        """Test execution params builder."""
        selector = {
            "pipelineName": "test-pipeline",
            "repositoryName": "test-repo",
            "repositoryLocationName": "test-location"
        }
        
        params = build_execution_params(
            selector=selector,
            run_config={"resources": {"io_manager": {"config": {}}}},
            mode="test",
            tags={"env": "staging", "user": "test"}
        )
        
        assert params["selector"] == selector
        assert params["mode"] == "test"
        assert params["runConfigData"] == {"resources": {"io_manager": {"config": {}}}}
        assert params["executionMetadata"]["tags"] == [
            {"key": "env", "value": "staging"},
            {"key": "user", "value": "test"}
        ]