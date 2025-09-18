"""Load testing configuration for DagLab API using Locust."""

from locust import HttpUser, task, between
import json
import random


class DagLabUser(HttpUser):
    """Simulated user for load testing DagLab API."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session."""
        # Authenticate if needed
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token"
        }
        self.dag_ids = []
        self.execution_ids = []
    
    @task(3)
    def create_dag(self):
        """Create a new DAG."""
        dag_config = {
            "name": f"load_test_dag_{random.randint(1000, 9999)}",
            "description": "DAG created during load testing",
            "nodes": [
                {
                    "id": f"node_{i}",
                    "type": "compute",
                    "task": {
                        "function": "multiply",
                        "params": {"x": i, "y": 2}
                    }
                }
                for i in range(random.randint(5, 20))
            ],
            "edges": [
                {"source": f"node_{i}", "target": f"node_{i+1}"}
                for i in range(random.randint(4, 19))
            ]
        }
        
        with self.client.post(
            "/api/v1/dags",
            json=dag_config,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                dag_id = response.json().get("id")
                if dag_id:
                    self.dag_ids.append(dag_id)
                response.success()
            else:
                response.failure(f"Failed to create DAG: {response.status_code}")
    
    @task(5)
    def list_dags(self):
        """List all DAGs."""
        params = {
            "limit": random.choice([10, 20, 50]),
            "offset": random.choice([0, 10, 20])
        }
        
        self.client.get(
            "/api/v1/dags",
            params=params,
            headers=self.headers,
            name="/api/v1/dags?limit=[limit]&offset=[offset]"
        )
    
    @task(4)
    def get_dag(self):
        """Get a specific DAG."""
        if not self.dag_ids:
            return
        
        dag_id = random.choice(self.dag_ids)
        self.client.get(
            f"/api/v1/dags/{dag_id}",
            headers=self.headers,
            name="/api/v1/dags/[id]"
        )
    
    @task(6)
    def execute_dag(self):
        """Execute a DAG."""
        if not self.dag_ids:
            return
        
        dag_id = random.choice(self.dag_ids)
        execution_config = {
            "dag_id": dag_id,
            "params": {
                "input_data": list(range(random.randint(10, 100))),
                "mode": random.choice(["sequential", "parallel"])
            }
        }
        
        with self.client.post(
            "/api/v1/executions",
            json=execution_config,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 202:
                execution_id = response.json().get("execution_id")
                if execution_id:
                    self.execution_ids.append(execution_id)
                response.success()
            else:
                response.failure(f"Failed to execute DAG: {response.status_code}")
    
    @task(8)
    def check_execution_status(self):
        """Check execution status."""
        if not self.execution_ids:
            return
        
        execution_id = random.choice(self.execution_ids)
        self.client.get(
            f"/api/v1/executions/{execution_id}",
            headers=self.headers,
            name="/api/v1/executions/[id]"
        )
    
    @task(2)
    def get_execution_results(self):
        """Get execution results."""
        if not self.execution_ids:
            return
        
        execution_id = random.choice(self.execution_ids[-10:])  # Recent executions
        self.client.get(
            f"/api/v1/executions/{execution_id}/results",
            headers=self.headers,
            name="/api/v1/executions/[id]/results"
        )
    
    @task(1)
    def update_dag(self):
        """Update an existing DAG."""
        if not self.dag_ids:
            return
        
        dag_id = random.choice(self.dag_ids)
        update_data = {
            "description": f"Updated at load test iteration {random.randint(1000, 9999)}",
            "metadata": {
                "updated": True,
                "iteration": random.randint(1, 100)
            }
        }
        
        self.client.patch(
            f"/api/v1/dags/{dag_id}",
            json=update_data,
            headers=self.headers,
            name="/api/v1/dags/[id]"
        )
    
    @task(1)
    def delete_dag(self):
        """Delete a DAG."""
        if len(self.dag_ids) < 10:  # Keep some DAGs
            return
        
        dag_id = self.dag_ids.pop(0)  # Remove oldest
        self.client.delete(
            f"/api/v1/dags/{dag_id}",
            headers=self.headers,
            name="/api/v1/dags/[id]"
        )
    
    @task(3)
    def get_metrics(self):
        """Get system metrics."""
        metric_types = ["cpu", "memory", "execution_time", "queue_size"]
        metric_type = random.choice(metric_types)
        
        params = {
            "type": metric_type,
            "period": random.choice(["1h", "24h", "7d"])
        }
        
        self.client.get(
            "/api/v1/metrics",
            params=params,
            headers=self.headers,
            name="/api/v1/metrics?type=[type]&period=[period]"
        )
    
    @task(2)
    def health_check(self):
        """Perform health check."""
        self.client.get(
            "/api/v1/health",
            headers=self.headers
        )


class AdminUser(HttpUser):
    """Simulated admin user for load testing admin endpoints."""
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Initialize admin session."""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer admin-token"
        }
    
    @task(1)
    def get_system_stats(self):
        """Get system statistics."""
        self.client.get(
            "/api/v1/admin/stats",
            headers=self.headers
        )
    
    @task(1)
    def list_users(self):
        """List system users."""
        self.client.get(
            "/api/v1/admin/users",
            headers=self.headers
        )
    
    @task(1)
    def get_audit_log(self):
        """Get audit log entries."""
        params = {
            "limit": 100,
            "offset": random.choice([0, 100, 200])
        }
        
        self.client.get(
            "/api/v1/admin/audit",
            params=params,
            headers=self.headers,
            name="/api/v1/admin/audit?limit=[limit]&offset=[offset]"
        )