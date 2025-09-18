"""Integrations with external tools and services."""

from typing import Any, Dict, Optional, List
import httpx
from abc import ABC, abstractmethod


class Integration(ABC):
    """Base class for all integrations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._client = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the external service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external service."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is working."""
        pass


class DagsterIntegration(Integration):
    """Integration with Dagster."""
    
    async def connect(self) -> None:
        """Connect to Dagster instance."""
        base_url = self.config.get("base_url", "http://localhost:3000")
        self._client = httpx.AsyncClient(base_url=base_url)
    
    async def disconnect(self) -> None:
        """Disconnect from Dagster."""
        if self._client:
            await self._client.aclose()
    
    async def test_connection(self) -> bool:
        """Test Dagster connection."""
        try:
            response = await self._client.get("/graphql")
            return response.status_code == 200
        except Exception:
            return False
    
    async def submit_job(self, job_name: str, config: Dict[str, Any]) -> str:
        """Submit a job to Dagster."""
        # Implementation would use Dagster GraphQL API
        return "job_id_placeholder"


class MarimoIntegration(Integration):
    """Integration with Marimo notebooks."""
    
    async def connect(self) -> None:
        """Connect to Marimo server."""
        base_url = self.config.get("base_url", "http://localhost:2718")
        self._client = httpx.AsyncClient(base_url=base_url)
    
    async def disconnect(self) -> None:
        """Disconnect from Marimo."""
        if self._client:
            await self._client.aclose()
    
    async def test_connection(self) -> bool:
        """Test Marimo connection."""
        try:
            response = await self._client.get("/api/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def create_notebook(self, name: str, content: str) -> str:
        """Create a new notebook."""
        # Implementation would use Marimo API
        return "notebook_id_placeholder"


class AirflowIntegration(Integration):
    """Integration with Apache Airflow."""
    
    async def connect(self) -> None:
        """Connect to Airflow instance."""
        base_url = self.config.get("base_url", "http://localhost:8080")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Content-Type": "application/json"}
        )
        
        # Add authentication if provided
        if "username" in self.config and "password" in self.config:
            self._client.auth = (
                self.config["username"], 
                self.config["password"]
            )
    
    async def disconnect(self) -> None:
        """Disconnect from Airflow."""
        if self._client:
            await self._client.aclose()
    
    async def test_connection(self) -> bool:
        """Test Airflow connection."""
        try:
            response = await self._client.get("/api/v1/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def trigger_dag(self, dag_id: str, conf: Optional[Dict[str, Any]] = None) -> str:
        """Trigger an Airflow DAG."""
        # Implementation would use Airflow REST API
        return "dag_run_id_placeholder"


class IntegrationManager:
    """Manages all integrations."""
    
    def __init__(self):
        self._integrations: Dict[str, Integration] = {}
    
    def register(self, name: str, integration: Integration) -> None:
        """Register an integration."""
        self._integrations[name] = integration
    
    async def connect_all(self) -> None:
        """Connect all registered integrations."""
        for integration in self._integrations.values():
            await integration.connect()
    
    async def disconnect_all(self) -> None:
        """Disconnect all integrations."""
        for integration in self._integrations.values():
            await integration.disconnect()
    
    def get(self, name: str) -> Optional[Integration]:
        """Get a specific integration."""
        return self._integrations.get(name)
    
    def list_integrations(self) -> List[str]:
        """List all registered integrations."""
        return list(self._integrations.keys())


__all__ = [
    "Integration",
    "DagsterIntegration",
    "MarimoIntegration",
    "AirflowIntegration",
    "IntegrationManager",
]