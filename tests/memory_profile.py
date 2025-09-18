#!/usr/bin/env python3
"""Memory profiling script for DagLab components."""

import gc
import tracemalloc
from memory_profiler import profile

from daglab import DAG, Node, Task
from daglab.storage import StorageManager
from daglab.runtime import ExecutionEngine


@profile
def profile_dag_creation():
    """Profile memory usage during DAG creation."""
    dags = []
    
    # Create multiple DAGs with increasing complexity
    for i in range(5):
        dag = DAG(f"memory_test_dag_{i}")
        
        # Create nodes
        nodes = []
        for j in range(100 * (i + 1)):
            node = Node(
                f"node_{i}_{j}",
                task=Task(lambda x=j: x * 2),
                metadata={"index": j, "dag": i}
            )
            nodes.append(node)
            dag.add_node(node)
        
        # Create edges
        for j in range(1, len(nodes)):
            dag.add_edge(nodes[j-1], nodes[j])
            
            # Add cross-connections
            if j % 10 == 0 and j > 10:
                dag.add_edge(nodes[j-10], nodes[j])
        
        dags.append(dag)
    
    return dags


@profile
def profile_dag_execution():
    """Profile memory usage during DAG execution."""
    dag = DAG("execution_memory_test")
    
    # Create a DAG that processes data
    results = []
    
    for i in range(50):
        def process_data(idx=i):
            # Simulate data processing
            data = list(range(1000))
            processed = [x * 2 for x in data]
            return sum(processed)
        
        node = Node(f"processor_{i}", task=Task(process_data))
        dag.add_node(node)
        
        if i > 0:
            dag.add_edge(dag.nodes[i-1], node)
    
    # Execute the DAG
    engine = ExecutionEngine()
    results = engine.execute(dag)
    
    return results


@profile
def profile_storage_operations():
    """Profile memory usage during storage operations."""
    storage = StorageManager()
    
    # Store large datasets
    datasets = []
    for i in range(10):
        data = {
            "id": i,
            "values": list(range(10000)),
            "metadata": {
                "created": "2024-01-01",
                "type": "test_data",
                "size": 10000
            }
        }
        
        key = f"dataset_{i}"
        storage.store(key, data)
        datasets.append(key)
    
    # Retrieve datasets
    for key in datasets:
        data = storage.retrieve(key)
    
    # Clean up
    for key in datasets:
        storage.delete(key)
    
    return storage


@profile
def profile_parallel_execution():
    """Profile memory usage during parallel execution."""
    dag = DAG("parallel_memory_test")
    
    # Create parallel branches
    for branch in range(10):
        prev_node = None
        
        for i in range(20):
            def compute(b=branch, idx=i):
                # Memory-intensive computation
                matrix = [[j * k for j in range(100)] for k in range(100)]
                return sum(sum(row) for row in matrix)
            
            node = Node(f"compute_{branch}_{i}", task=Task(compute))
            dag.add_node(node)
            
            if prev_node:
                dag.add_edge(prev_node, node)
            prev_node = node
    
    # Execute with parallel executor
    engine = ExecutionEngine(executor_type="parallel", max_workers=4)
    results = engine.execute(dag)
    
    return results


def main():
    """Run memory profiling tests."""
    print("Starting memory profiling...")
    
    # Start memory tracking
    tracemalloc.start()
    
    # Run profiling functions
    print("\n1. Profiling DAG creation...")
    dags = profile_dag_creation()
    
    # Get memory snapshot
    snapshot1 = tracemalloc.take_snapshot()
    
    print("\n2. Profiling DAG execution...")
    exec_results = profile_dag_execution()
    
    snapshot2 = tracemalloc.take_snapshot()
    
    print("\n3. Profiling storage operations...")
    storage = profile_storage_operations()
    
    snapshot3 = tracemalloc.take_snapshot()
    
    print("\n4. Profiling parallel execution...")
    parallel_results = profile_parallel_execution()
    
    snapshot4 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    print("\n\nMemory usage statistics:")
    print("-" * 50)
    
    for stat in snapshot4.statistics('lineno')[:10]:
        print(stat)
    
    # Show differences
    print("\n\nMemory usage changes:")
    print("-" * 50)
    
    top_stats = snapshot4.compare_to(snapshot1, 'lineno')
    for stat in top_stats[:10]:
        print(stat)
    
    # Force garbage collection
    gc.collect()
    
    # Stop tracking
    tracemalloc.stop()
    
    print("\nMemory profiling complete!")


if __name__ == "__main__":
    main()