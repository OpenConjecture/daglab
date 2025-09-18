"""Performance benchmarks for DAG operations."""

import pytest
from daglab import DAG, Node, Task


class TestDAGPerformance:
    """Benchmark tests for DAG operations."""
    
    def test_dag_creation_small(self, benchmark):
        """Benchmark creating a small DAG (10 nodes)."""
        def create_dag():
            dag = DAG("small_dag")
            nodes = []
            for i in range(10):
                node = Node(f"node_{i}", task=Task(lambda x=i: x))
                nodes.append(node)
                dag.add_node(node)
            
            # Add some edges
            for i in range(1, 10):
                dag.add_edge(nodes[i-1], nodes[i])
            
            return dag
        
        result = benchmark(create_dag)
        assert len(result.nodes) == 10
    
    def test_dag_creation_large(self, benchmark):
        """Benchmark creating a large DAG (1000 nodes)."""
        def create_dag():
            dag = DAG("large_dag")
            nodes = []
            for i in range(1000):
                node = Node(f"node_{i}", task=Task(lambda x=i: x))
                nodes.append(node)
                dag.add_node(node)
            
            # Add edges to create a complex graph
            for i in range(1, 1000):
                dag.add_edge(nodes[i-1], nodes[i])
                if i % 10 == 0 and i > 10:
                    dag.add_edge(nodes[i-10], nodes[i])
            
            return dag
        
        result = benchmark(create_dag)
        assert len(result.nodes) == 1000
    
    def test_dag_topological_sort(self, benchmark):
        """Benchmark topological sorting."""
        # Setup
        dag = DAG("sort_dag")
        nodes = []
        for i in range(100):
            node = Node(f"node_{i}", task=Task(lambda x=i: x))
            nodes.append(node)
            dag.add_node(node)
        
        # Create a complex dependency graph
        for i in range(1, 100):
            dag.add_edge(nodes[i-1], nodes[i])
            if i % 5 == 0 and i > 5:
                dag.add_edge(nodes[i-5], nodes[i])
        
        # Benchmark the sort
        result = benchmark(dag.topological_sort)
        assert len(result) == 100
    
    def test_dag_cycle_detection(self, benchmark):
        """Benchmark cycle detection."""
        # Setup
        dag = DAG("cycle_dag")
        nodes = []
        for i in range(50):
            node = Node(f"node_{i}", task=Task(lambda x=i: x))
            nodes.append(node)
            dag.add_node(node)
        
        # Create edges without cycles
        for i in range(1, 50):
            dag.add_edge(nodes[i-1], nodes[i])
        
        # Benchmark cycle detection
        result = benchmark(dag.has_cycle)
        assert result is False
    
    def test_dag_execution_sequential(self, benchmark):
        """Benchmark sequential DAG execution."""
        # Setup
        dag = DAG("exec_dag")
        results = []
        
        for i in range(20):
            def task_func(x=i):
                return x * 2
            
            node = Node(f"node_{i}", task=Task(task_func))
            dag.add_node(node)
            
            if i > 0:
                dag.add_edge(dag.nodes[i-1], node)
        
        # Benchmark execution
        result = benchmark(dag.execute)
        assert len(result) == 20
    
    def test_dag_parallel_execution(self, benchmark):
        """Benchmark parallel DAG execution."""
        # Setup
        dag = DAG("parallel_dag")
        
        # Create parallel branches
        for branch in range(5):
            prev_node = None
            for i in range(10):
                def task_func(b=branch, idx=i):
                    return b * 100 + idx
                
                node = Node(f"node_{branch}_{i}", task=Task(task_func))
                dag.add_node(node)
                
                if prev_node:
                    dag.add_edge(prev_node, node)
                prev_node = node
        
        # Benchmark parallel execution
        result = benchmark(dag.execute, executor="parallel")
        assert len(result) == 50
    
    @pytest.mark.parametrize("num_nodes", [10, 50, 100, 500])
    def test_dag_validation_scaling(self, benchmark, num_nodes):
        """Benchmark DAG validation at different scales."""
        # Setup
        dag = DAG(f"validation_dag_{num_nodes}")
        nodes = []
        
        for i in range(num_nodes):
            node = Node(f"node_{i}", task=Task(lambda x=i: x))
            nodes.append(node)
            dag.add_node(node)
        
        # Create a moderately connected graph
        for i in range(1, num_nodes):
            dag.add_edge(nodes[i-1], nodes[i])
            if i % 10 == 0 and i >= 20:
                dag.add_edge(nodes[i-20], nodes[i])
        
        # Benchmark validation
        result = benchmark(dag.validate)
        assert result is True