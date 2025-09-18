"""GraphQL client for Dagster with connection management and error handling."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Union, List
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .auth import AuthConfig
from .models import GraphQLError, GraphQLResponse

logger = logging.getLogger(__name__)


class DagsterClientError(Exception):
    """Base exception for Dagster client errors."""
    pass


class GraphQLQueryError(DagsterClientError):
    """Exception raised when GraphQL query fails."""
    
    def __init__(self, errors: List[Dict[str, Any]], query: str):
        self.errors = errors
        self.query = query
        super().__init__(f"GraphQL query failed with {len(errors)} error(s)")


class DagsterClient:
    """Async GraphQL client for Dagster with connection pooling and retry logic."""
    
    def __init__(
        self,
        endpoint: str,
        auth_config: Optional[AuthConfig] = None,
        timeout: float = 30.0,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
        keepalive_expiry: float = 300.0,
        verify_ssl: bool = True,
        retry_attempts: int = 3,
        retry_wait_min: float = 1.0,
        retry_wait_max: float = 10.0,
    ):
        """Initialize Dagster GraphQL client.
        
        Args:
            endpoint: GraphQL endpoint URL
            auth_config: Authentication configuration
            timeout: Request timeout in seconds
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum number of keepalive connections
            keepalive_expiry: Keepalive connection expiry in seconds
            verify_ssl: Whether to verify SSL certificates
            retry_attempts: Number of retry attempts for failed requests
            retry_wait_min: Minimum wait time between retries
            retry_wait_max: Maximum wait time between retries
        """
        self.endpoint = endpoint.rstrip('/')
        self.auth_config = auth_config or AuthConfig()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.retry_attempts = retry_attempts
        self.retry_wait_min = retry_wait_min
        self.retry_wait_max = retry_wait_max
        
        # Configure connection pool limits
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )
        
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    headers = self.auth_config.get_headers()
                    self._client = httpx.AsyncClient(
                        limits=self.limits,
                        timeout=httpx.Timeout(self.timeout),
                        headers=headers,
                        verify=self.verify_ssl,
                    )
        return self._client
    
    @asynccontextmanager
    async def session(self):
        """Context manager for client session."""
        client = await self._get_client()
        try:
            yield self
        finally:
            # Keep connection alive for reuse
            pass
    
    async def close(self):
        """Close the HTTP client and release resources."""
        async with self._lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                self._client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> GraphQLResponse:
        """Execute a GraphQL query with retry logic.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Operation name for multi-operation documents
            
        Returns:
            GraphQLResponse object
            
        Raises:
            GraphQLQueryError: If the query returns errors
            DagsterClientError: For other client errors
        """
        client = await self._get_client()
        
        payload = {
            "query": query,
            "variables": variables or {},
        }
        
        if operation_name:
            payload["operationName"] = operation_name
        
        try:
            logger.debug(f"Executing GraphQL query: {operation_name or 'unnamed'}")
            
            # Refresh auth headers if needed
            headers = self.auth_config.get_headers()
            
            response = await client.post(
                self.endpoint,
                json=payload,
                headers=headers,
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            graphql_response = GraphQLResponse(
                data=data.get("data"),
                errors=[GraphQLError(**e) for e in data.get("errors", [])],
                extensions=data.get("extensions"),
            )
            
            # Check for errors
            if graphql_response.errors:
                logger.error(f"GraphQL errors: {graphql_response.errors}")
                raise GraphQLQueryError(
                    errors=[e.dict() for e in graphql_response.errors],
                    query=query,
                )
            
            return graphql_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise DagsterClientError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise DagsterClientError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise DagsterClientError(f"Invalid JSON response: {str(e)}")
    
    async def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query and return data.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Operation name
            
        Returns:
            Query result data
        """
        response = await self.execute(query, variables, operation_name)
        return response.data or {}
    
    async def mutate(
        self,
        mutation: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL mutation.
        
        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            operation_name: Operation name
            
        Returns:
            Mutation result data
        """
        return await self.query(mutation, variables, operation_name)
    
    async def subscribe(
        self,
        subscription: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ):
        """Execute a GraphQL subscription (WebSocket support required).
        
        Note: This is a placeholder for subscription support.
        Real implementation would require WebSocket connection.
        """
        raise NotImplementedError(
            "Subscription support requires WebSocket implementation. "
            "Use polling with queries for now."
        )
    
    async def health_check(self) -> bool:
        """Check if the Dagster instance is healthy."""
        try:
            # Simple query to check connectivity
            query = """
            query HealthCheck {
                version
            }
            """
            await self.query(query)
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"<DagsterClient endpoint={self.endpoint}>"


class DagsterClientSync:
    """Synchronous wrapper for DagsterClient."""
    
    def __init__(self, *args, **kwargs):
        self._client = DagsterClient(*args, **kwargs)
        self._loop = None
    
    def _ensure_loop(self):
        """Ensure we have an event loop."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        self._ensure_loop()
        
        if self._loop.is_running():
            # If loop is already running, schedule the coroutine
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # Run in the current loop
            return self._loop.run_until_complete(coro)
    
    def execute(self, *args, **kwargs) -> GraphQLResponse:
        """Execute a GraphQL query synchronously."""
        return self._run_async(self._client.execute(*args, **kwargs))
    
    def query(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute a GraphQL query synchronously."""
        return self._run_async(self._client.query(*args, **kwargs))
    
    def mutate(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute a GraphQL mutation synchronously."""
        return self._run_async(self._client.mutate(*args, **kwargs))
    
    def health_check(self) -> bool:
        """Check health synchronously."""
        return self._run_async(self._client.health_check())
    
    def close(self):
        """Close the client."""
        self._run_async(self._client.close())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()