"""Enhanced pytest configuration and fixtures for comprehensive testing."""

import pytest
import asyncio
import os
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Generator, Any, Dict, List
from unittest.mock import Mock, MagicMock, patch

import hypothesis
from hypothesis import strategies as st

from daglab.core import DAG, Node, Edge, Task
from daglab.helpers import Config, Security
from daglab.storage import LocalStorage, ArtifactStore
from daglab.runtime import Executor
from daglab.helpers.graphql import DagsterClient, DagsterClientSync
from daglab.helpers.auth import AuthConfig, AuthType
from daglab.runtime.errors import DagLabError, SecurityError, ValidationError

# Configure Hypothesis for property-based testing
hypothesis.settings.register_profile("default", max_examples=100, deadline=5000)
hypothesis.settings.load_profile("default")


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


# ===============================
# Enhanced Test Fixtures
# ===============================

@pytest.fixture(scope="session")
def test_data_dir():
    """Create persistent test data directory."""
    data_dir = Path.cwd() / "tests" / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def mock_dagster_client():
    """Mock Dagster client for testing."""
    mock_client = Mock(spec=DagsterClientSync)
    mock_client.health_check.return_value = True
    mock_client.query.return_value = {
        "repositoriesOrError": {
            "nodes": [
                {
                    "name": "test_repo",
                    "location": {"name": "test_location"},
                    "jobs": [
                        {"name": "test_job", "description": "Test job"}
                    ]
                }
            ]
        }
    }
    return mock_client


@pytest.fixture
def mock_dagster_async_client():
    """Mock async Dagster client for testing."""
    mock_client = Mock(spec=DagsterClient)
    mock_client.health_check = AsyncMock(return_value=True)
    mock_client.query = AsyncMock(return_value={
        "repositoriesOrError": {
            "nodes": [
                {
                    "name": "async_test_repo",
                    "location": {"name": "async_test_location"},
                    "jobs": [
                        {"name": "async_test_job", "description": "Async test job"}
                    ]
                }
            ]
        }
    })
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def auth_config():
    """Create test authentication configuration."""
    return AuthConfig(
        auth_type=AuthType.NONE,
        username="test_user",
        password="test_password",
        token="test_token"
    )


@pytest.fixture
def sample_env_vars():
    """Sample environment variables for testing."""
    return {
        "DAGLAB_TEST_VAR": "test_value",
        "DAGLAB_DEBUG": "true",
        "DAGLAB_MAX_WORKERS": "4"
    }


@pytest.fixture
def performance_config():
    """Configuration for performance testing."""
    return {
        "max_execution_time": 30.0,
        "memory_limit_mb": 512,
        "cpu_threshold": 80.0,
        "test_iterations": 10
    }


@pytest.fixture
def benchmark_data():
    """Generate benchmark test data."""
    return {
        "small_dataset": list(range(100)),
        "medium_dataset": list(range(10000)),
        "large_dataset": list(range(100000)),
        "test_matrices": [
            [[1, 2], [3, 4]],
            [[i for i in range(10)] for _ in range(10)]
        ]
    }


@pytest.fixture
def mock_cloud_storage():
    """Mock cloud storage for testing."""
    mock_storage = Mock()
    mock_storage.upload.return_value = "mock_file_id"
    mock_storage.download.return_value = b"mock_file_content"
    mock_storage.list_files.return_value = ["file1.txt", "file2.json"]
    mock_storage.delete.return_value = True
    return mock_storage


@pytest.fixture
def test_database_url():
    """Test database URL for integration tests."""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///test.db")


@pytest.fixture
def security_test_cases():
    """Security test cases for validation."""
    return {
        "malicious_inputs": [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "\x00\x01\x02",
            "' OR '1'='1"
        ],
        "safe_inputs": [
            "normal text",
            "user@example.com",
            "file_name.txt",
            "valid-identifier"
        ],
        "edge_cases": [
            "",
            " ",
            "\n\t\r",
            "a" * 10000,  # Very long string
            "🚀🔥💻"  # Unicode emojis
        ]
    }


@pytest.fixture
def workflow_test_data():
    """Complex workflow test data."""
    return {
        "linear_workflow": {
            "name": "linear_test",
            "tasks": [
                {"name": "extract", "type": "extract", "dependencies": []},
                {"name": "transform", "type": "transform", "dependencies": ["extract"]},
                {"name": "load", "type": "load", "dependencies": ["transform"]}
            ]
        },
        "parallel_workflow": {
            "name": "parallel_test",
            "tasks": [
                {"name": "source", "type": "source", "dependencies": []},
                {"name": "branch1", "type": "process", "dependencies": ["source"]},
                {"name": "branch2", "type": "process", "dependencies": ["source"]},
                {"name": "merge", "type": "merge", "dependencies": ["branch1", "branch2"]}
            ]
        },
        "conditional_workflow": {
            "name": "conditional_test",
            "tasks": [
                {"name": "check", "type": "condition", "dependencies": []},
                {"name": "success_path", "type": "process", "dependencies": ["check"], "condition": "success"},
                {"name": "failure_path", "type": "process", "dependencies": ["check"], "condition": "failure"}
            ]
        }
    }


# ===============================
# Property-based Testing Strategies
# ===============================

@pytest.fixture
def node_strategy():
    """Hypothesis strategy for generating Node objects."""
    return st.builds(
        Node,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        task_type=st.sampled_from(["python", "sql", "bash", "docker"]),
        params=st.one_of(st.none(), st.dictionaries(st.text(), st.text()))
    )


@pytest.fixture
def dag_strategy():
    """Hypothesis strategy for generating DAG objects."""
    return st.builds(
        DAG,
        name=st.text(min_size=1, max_size=30),
        description=st.one_of(st.none(), st.text(max_size=200))
    )


# ===============================
# Test Markers and Categories
# ===============================

pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning"),
]


# ===============================
# Test Utilities
# ===============================

@pytest.fixture
def assert_timing():
    """Context manager for asserting execution time."""
    class TimingAssertion:
        def __init__(self, max_time: float):
            self.max_time = max_time
            self.start_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.time() - self.start_time
            assert elapsed <= self.max_time, f"Execution took {elapsed:.2f}s, expected <= {self.max_time}s"
    
    return TimingAssertion


@pytest.fixture
def capture_logs():
    """Capture and analyze log output."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger("daglab")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    logger.removeHandler(handler)


@pytest.fixture
def memory_monitor():
    """Monitor memory usage during tests."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    yield process
    
    final_memory = process.memory_info().rss
    memory_diff = final_memory - initial_memory
    
    # Warning if memory increased by more than 100MB
    if memory_diff > 100 * 1024 * 1024:
        pytest.warns(ResourceWarning, f"Memory increased by {memory_diff / 1024 / 1024:.1f}MB")


# ===============================
# Cleanup and Session Management
# ===============================

@pytest.fixture(scope="session", autouse=True)
def test_session_setup():
    """Setup for entire test session."""
    # Create test directories
    test_dirs = ["tests/data", "tests/logs", "tests/output"]
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup after all tests
    for dir_path in test_dirs:
        if Path(dir_path).exists():
            shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def test_isolation():
    """Ensure test isolation."""
    # Store original environment
    original_env = dict(os.environ)
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)