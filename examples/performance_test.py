#!/usr/bin/env python3
"""Performance testing example for CI/CD pipeline profiling."""

import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from daglab import DAG, Node, Task
from daglab.runtime import ExecutionEngine
from daglab.storage import StorageManager


def cpu_intensive_task(n: int = 1000000) -> float:
    """CPU-intensive task for profiling."""
    result = 0.0
    for i in range(n):
        result += (i ** 0.5) * random.random()
    return result


def memory_intensive_task(size: int = 1000000) -> List[int]:
    """Memory-intensive task for profiling."""
    data = []
    for i in range(size):
        data.append(random.randint(0, 1000000))
    
    # Sort the data
    data.sort()
    
    # Create some additional data structures
    unique_data = list(set(data))
    grouped_data = {i: [] for i in range(10)}
    
    for value in data:
        bucket = value % 10
        grouped_data[bucket].append(value)
    
    return unique_data


def io_intensive_task(iterations: int = 100) -> Dict[str, Any]:
    """I/O-intensive task for profiling."""
    storage = StorageManager()
    results = {}
    
    for i in range(iterations):
        key = f"test_key_{i}"
        data = {
            "iteration": i,
            "timestamp": time.time(),
            "random_data": [random.random() for _ in range(100)]
        }
        
        # Store data
        storage.store(key, data)
        
        # Retrieve and verify
        retrieved = storage.retrieve(key)
        results[key] = retrieved
        
        # Clean up
        storage.delete(key)
    
    return results


def create_complex_dag(num_nodes: int = 50) -> DAG:
    """Create a complex DAG for performance testing."""
    dag = DAG("performance_test_dag")
    nodes = []
    
    # Create nodes with different task types
    for i in range(num_nodes):
        if i % 3 == 0:
            task = Task(cpu_intensive_task, n=100000)
        elif i % 3 == 1:
            task = Task(memory_intensive_task, size=10000)
        else:
            task = Task(io_intensive_task, iterations=10)
        
        node = Node(f"node_{i}", task=task)
        nodes.append(node)
        dag.add_node(node)
    
    # Create complex dependencies
    for i in range(1, num_nodes):
        # Linear dependencies
        dag.add_edge(nodes[i-1], nodes[i])
        
        # Additional cross-dependencies
        if i % 5 == 0 and i >= 10:
            dag.add_edge(nodes[i-10], nodes[i])
        
        if i % 7 == 0 and i >= 14:
            dag.add_edge(nodes[i-14], nodes[i])
    
    return dag


def parallel_execution_test(num_workers: int = 4) -> Dict[str, Any]:
    """Test parallel execution performance."""
    results = {
        "start_time": time.time(),
        "tasks_completed": 0,
        "errors": 0
    }
    
    def worker_task(task_id: int) -> Dict[str, Any]:
        """Individual worker task."""
        start = time.time()
        
        try:
            if task_id % 4 == 0:
                result = cpu_intensive_task(500000)
            elif task_id % 4 == 1:
                result = memory_intensive_task(50000)
            elif task_id % 4 == 2:
                result = io_intensive_task(20)
            else:
                # Mixed workload
                cpu_result = cpu_intensive_task(100000)
                mem_result = len(memory_intensive_task(10000))
                result = {"cpu": cpu_result, "memory": mem_result}
            
            return {
                "task_id": task_id,
                "result": result,
                "duration": time.time() - start,
                "success": True
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "error": str(e),
                "duration": time.time() - start,
                "success": False
            }
    
    # Execute tasks in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(worker_task, i): i for i in range(100)}
        
        for future in as_completed(futures):
            result = future.result()
            
            if result["success"]:
                results["tasks_completed"] += 1
            else:
                results["errors"] += 1
    
    results["end_time"] = time.time()
    results["total_duration"] = results["end_time"] - results["start_time"]
    
    return results


def main():
    """Run performance tests."""
    print("Starting performance tests...")
    
    # Test 1: Complex DAG execution
    print("\n1. Testing complex DAG execution...")
    start = time.time()
    
    dag = create_complex_dag(30)
    engine = ExecutionEngine(executor_type="threaded", max_workers=4)
    dag_results = engine.execute(dag)
    
    dag_duration = time.time() - start
    print(f"   DAG execution completed in {dag_duration:.2f} seconds")
    print(f"   Nodes executed: {len(dag_results)}")
    
    # Test 2: Parallel execution
    print("\n2. Testing parallel execution...")
    parallel_results = parallel_execution_test(num_workers=8)
    
    print(f"   Parallel execution completed in {parallel_results['total_duration']:.2f} seconds")
    print(f"   Tasks completed: {parallel_results['tasks_completed']}")
    print(f"   Errors: {parallel_results['errors']}")
    
    # Test 3: Memory stress test
    print("\n3. Testing memory performance...")
    start = time.time()
    
    memory_results = []
    for i in range(10):
        result = memory_intensive_task(100000)
        memory_results.append(len(result))
    
    memory_duration = time.time() - start
    print(f"   Memory test completed in {memory_duration:.2f} seconds")
    print(f"   Total unique values: {sum(memory_results)}")
    
    # Test 4: I/O stress test
    print("\n4. Testing I/O performance...")
    start = time.time()
    
    io_results = io_intensive_task(50)
    
    io_duration = time.time() - start
    print(f"   I/O test completed in {io_duration:.2f} seconds")
    print(f"   Operations completed: {len(io_results)}")
    
    print("\nPerformance tests completed!")


if __name__ == "__main__":
    main()