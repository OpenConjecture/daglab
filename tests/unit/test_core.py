"""Unit tests for core DAG components."""

import pytest
from daglab.core import DAG, Node, Edge, Task, Pipeline, Workflow
from daglab.helpers import Validator


class TestNode:
    """Test Node class."""
    
    def test_node_creation(self):
        """Test basic node creation."""
        node = Node(name="TestNode", task_type="python")
        assert node.name == "TestNode"
        assert node.task_type == "python"
        assert node.id is not None
        assert len(node.id) > 0
    
    def test_node_with_params(self):
        """Test node with parameters."""
        params = {"arg1": "value1", "arg2": 42}
        node = Node(name="ParamNode", params=params)
        assert node.params == params
    
    def test_node_with_metadata(self):
        """Test node with metadata."""
        metadata = {"owner": "test", "priority": "high"}
        node = Node(name="MetaNode", metadata=metadata)
        assert node.metadata == metadata


class TestEdge:
    """Test Edge class."""
    
    def test_edge_creation(self):
        """Test basic edge creation."""
        edge = Edge(source="node1", target="node2")
        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.condition is None
    
    def test_edge_with_condition(self):
        """Test edge with condition."""
        edge = Edge(source="node1", target="node2", condition="value > 10")
        assert edge.condition == "value > 10"


class TestTask:
    """Test Task class."""
    
    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(name="TestTask", function="test_func")
        assert task.name == "TestTask"
        assert task.function == "test_func"
        assert task.id is not None
    
    def test_task_with_args_kwargs(self):
        """Test task with arguments."""
        args = [1, 2, 3]
        kwargs = {"key": "value"}
        task = Task(name="ArgTask", function="func", args=args, kwargs=kwargs)
        assert task.args == args
        assert task.kwargs == kwargs
    
    def test_task_with_retry_policy(self):
        """Test task with retry policy."""
        retry_policy = {"max_attempts": 3, "delay": 5}
        task = Task(name="RetryTask", function="func", retry_policy=retry_policy)
        assert task.retry_policy == retry_policy


class TestDAG:
    """Test DAG class."""
    
    def test_dag_creation(self):
        """Test basic DAG creation."""
        dag = DAG(name="TestDAG")
        assert dag.name == "TestDAG"
        assert dag.id is not None
        assert len(dag.nodes) == 0
        assert len(dag.edges) == 0
    
    def test_add_node(self, sample_dag):
        """Test adding nodes to DAG."""
        initial_count = len(sample_dag.nodes)
        new_node = Node(name="NewNode")
        sample_dag.add_node(new_node)
        assert len(sample_dag.nodes) == initial_count + 1
        assert new_node in sample_dag.nodes
    
    def test_add_edge(self, sample_dag):
        """Test adding edges to DAG."""
        initial_count = len(sample_dag.edges)
        # Get two nodes from the DAG
        if len(sample_dag.nodes) >= 2:
            edge = Edge(source=sample_dag.nodes[0].id, target=sample_dag.nodes[1].id)
            sample_dag.add_edge(edge)
            assert len(sample_dag.edges) == initial_count + 1


class TestPipeline:
    """Test Pipeline class."""
    
    def test_pipeline_creation(self):
        """Test basic pipeline creation."""
        pipeline = Pipeline(name="TestPipeline")
        assert pipeline.name == "TestPipeline"
        assert pipeline.id is not None
        assert len(pipeline.tasks) == 0
    
    def test_pipeline_with_tasks(self):
        """Test pipeline with tasks."""
        tasks = [
            Task(name="Task1", function="func1"),
            Task(name="Task2", function="func2"),
        ]
        pipeline = Pipeline(name="TestPipeline", tasks=tasks)
        assert len(pipeline.tasks) == 2
        assert pipeline.tasks == tasks


class TestWorkflow:
    """Test Workflow class."""
    
    def test_workflow_creation(self, sample_dag):
        """Test basic workflow creation."""
        workflow = Workflow(name="TestWorkflow", dag=sample_dag)
        assert workflow.name == "TestWorkflow"
        assert workflow.dag == sample_dag
        assert workflow.schedule is None
    
    def test_workflow_with_schedule(self, sample_dag):
        """Test workflow with schedule."""
        workflow = Workflow(
            name="ScheduledWorkflow",
            dag=sample_dag,
            schedule="0 0 * * *"
        )
        assert workflow.schedule == "0 0 * * *"
    
    def test_workflow_with_config(self, sample_dag):
        """Test workflow with configuration."""
        config = {"max_retries": 3, "timeout": 3600}
        workflow = Workflow(
            name="ConfiguredWorkflow",
            dag=sample_dag,
            config=config
        )
        assert workflow.config == config


class TestValidator:
    """Test DAG validation."""
    
    def test_valid_dag(self, sample_dag):
        """Test validation of a valid DAG."""
        assert Validator.validate_dag(sample_dag) is True
    
    def test_cyclic_dag(self, cyclic_dag):
        """Test validation of a DAG with cycles."""
        with pytest.raises(ValueError, match="DAG contains cycles"):
            Validator.validate_dag(cyclic_dag)
    
    def test_invalid_edge_source(self, sample_dag):
        """Test validation with invalid edge source."""
        # Add edge with non-existent source
        invalid_edge = Edge(source="non_existent", target=sample_dag.nodes[0].id)
        sample_dag.add_edge(invalid_edge)
        
        with pytest.raises(ValueError, match="Edge source .* not found in nodes"):
            Validator.validate_dag(sample_dag)
    
    def test_invalid_edge_target(self, sample_dag):
        """Test validation with invalid edge target."""
        # Add edge with non-existent target
        invalid_edge = Edge(source=sample_dag.nodes[0].id, target="non_existent")
        sample_dag.add_edge(invalid_edge)
        
        with pytest.raises(ValueError, match="Edge target .* not found in nodes"):
            Validator.validate_dag(sample_dag)