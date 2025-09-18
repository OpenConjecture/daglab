"""Pytest configuration and fixtures."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Any

from daglab.core import DAG, Node, Edge, Task
from daglab.helpers import Config, Security
from daglab.storage import LocalStorage, ArtifactStore
from daglab.runtime import Executor


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_dag() -> DAG:
    """Create a sample DAG for testing."""
    dag = DAG(name="test-dag", description="Test DAG")
    
    # Create nodes
    node1 = Node(name="Node1", task_type="python")
    node2 = Node(name="Node2", task_type="python")
    node3 = Node(name="Node3", task_type="python")
    
    # Add nodes
    dag.add_node(node1)
    dag.add_node(node2)
    dag.add_node(node3)
    
    # Create edges
    dag.add_edge(Edge(source=node1.id, target=node2.id))
    dag.add_edge(Edge(source=node2.id, target=node3.id))
    
    return dag


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        name="test-task",
        function="test_function",
        args=[1, 2, 3],
        kwargs={"key": "value"},
        timeout=30
    )


@pytest.fixture
def config(temp_dir: Path) -> Config:
    """Create a test configuration."""
    config_data = {
        "test": True,
        "data_dir": str(temp_dir),
        "max_workers": 2
    }
    
    config = Config()
    for key, value in config_data.items():
        config.set(key, value)
    
    return config


@pytest.fixture
def storage(temp_dir: Path) -> LocalStorage:
    """Create a local storage instance."""
    return LocalStorage(temp_dir)


@pytest.fixture
def artifact_store(storage: LocalStorage) -> ArtifactStore:
    """Create an artifact store."""
    return ArtifactStore(storage)


@pytest.fixture
def executor() -> Executor:
    """Create an executor instance."""
    return Executor(max_workers=2)


@pytest.fixture
def security() -> Security:
    """Create a security instance."""
    return Security()


@pytest.fixture
def cyclic_dag() -> DAG:
    """Create a DAG with cycles for testing validation."""
    dag = DAG(name="cyclic-dag", description="DAG with cycles")
    
    # Create nodes
    node1 = Node(name="Node1", task_type="python")
    node2 = Node(name="Node2", task_type="python")
    node3 = Node(name="Node3", task_type="python")
    
    # Add nodes
    dag.add_node(node1)
    dag.add_node(node2)
    dag.add_node(node3)
    
    # Create cyclic edges
    dag.add_edge(Edge(source=node1.id, target=node2.id))
    dag.add_edge(Edge(source=node2.id, target=node3.id))
    dag.add_edge(Edge(source=node3.id, target=node1.id))  # Creates cycle
    
    return dag


@pytest.fixture
def complex_dag() -> DAG:
    """Create a complex DAG for testing."""
    dag = DAG(name="complex-dag", description="Complex DAG")
    
    # Create multiple nodes
    nodes = []
    for i in range(10):
        node = Node(name=f"Node{i}", task_type="python")
        dag.add_node(node)
        nodes.append(node)
    
    # Create complex edge pattern
    for i in range(5):
        dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+5].id))
        if i < 4:
            dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))
            dag.add_edge(Edge(source=nodes[i+5].id, target=nodes[i+6].id))
    
    # Add conditional edges
    dag.add_edge(Edge(
        source=nodes[0].id, 
        target=nodes[9].id,
        condition="result > 0.5"
    ))
    
    return dag