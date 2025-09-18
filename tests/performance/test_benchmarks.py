"""Performance benchmarks and load testing for DagLab."""

import time
import pytest
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import List, Dict, Any

from daglab.core import DAG, Node, Edge, Task
from daglab.helpers import Config, Validator
from daglab.runtime import Executor
from daglab.storage import LocalStorage


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.performance
    @pytest.mark.benchmark(group="dag_creation")
    def test_dag_creation_performance(self, benchmark, benchmark_data):
        """Benchmark DAG creation performance."""
        def create_large_dag():
            dag = DAG(name="large-dag", description="Large performance test DAG")
            
            # Create 1000 nodes
            nodes = []
            for i in range(1000):
                node = Node(
                    name=f"node_{i}",
                    task_type="python",
                    params={"iteration": i, "data": benchmark_data["small_dataset"]}
                )
                dag.add_node(node)
                nodes.append(node)
            
            # Create edges in a complex pattern
            for i in range(999):
                dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))
                if i % 10 == 0 and i + 10 < len(nodes):
                    dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+10].id))
            
            return dag
        
        result = benchmark(create_large_dag)
        assert len(result.nodes) == 1000
        assert len(result.edges) >= 999
    
    @pytest.mark.performance
    @pytest.mark.benchmark(group="validation")
    def test_dag_validation_performance(self, benchmark, complex_dag):
        """Benchmark DAG validation performance."""
        # Add more complexity
        for i in range(100):
            node = Node(name=f"perf_node_{i}", task_type="python")
            complex_dag.add_node(node)
        
        result = benchmark(Validator.validate_dag, complex_dag)
        assert result is True
    
    @pytest.mark.performance
    @pytest.mark.benchmark(group="storage")
    def test_storage_performance(self, benchmark, temp_dir, benchmark_data):
        """Benchmark storage operations performance."""
        storage = LocalStorage(temp_dir)
        
        def storage_operations():
            # Write multiple files
            for i, data in enumerate(benchmark_data["medium_dataset"][:100]):
                storage.write(f"perf_file_{i}.txt", str(data))
            
            # Read files back
            results = []
            for i in range(100):
                content = storage.read(f"perf_file_{i}.txt")
                results.append(content)
            
            return results
        
        result = benchmark(storage_operations)
        assert len(result) == 100
    
    @pytest.mark.performance
    @pytest.mark.memory_intensive
    def test_memory_usage_large_dag(self, memory_monitor, benchmark_data):
        """Test memory usage with large DAGs."""
        initial_memory = memory_monitor.memory_info().rss
        
        # Create very large DAG
        dag = DAG(name="memory-test", description="Memory usage test")
        nodes = []
        
        # Create 10,000 nodes with data
        for i in range(10000):
            node = Node(
                name=f"memory_node_{i}",
                task_type="python",
                params={"large_data": benchmark_data["medium_dataset"]},
                metadata={"index": i, "batch": i // 100}
            )
            dag.add_node(node)
            nodes.append(node)
        
        # Create complex edge pattern
        for i in range(9999):
            dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))
            if i % 100 == 0 and i + 100 < len(nodes):
                dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+100].id))
        
        final_memory = memory_monitor.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory should be reasonable (less than 500MB increase)
        assert memory_increase < 500 * 1024 * 1024
        assert len(dag.nodes) == 10000
    
    @pytest.mark.performance
    @pytest.mark.cpu_intensive
    def test_concurrent_dag_processing(self, benchmark_data, performance_config):
        """Test concurrent DAG processing performance."""
        def create_test_dag(dag_id: int) -> DAG:
            dag = DAG(name=f"concurrent_dag_{dag_id}")
            
            # Create nodes
            nodes = []
            for i in range(50):  # Smaller DAGs for concurrency test
                node = Node(
                    name=f"node_{dag_id}_{i}",
                    task_type="python",
                    params={"data": benchmark_data["small_dataset"][:10]}
                )
                dag.add_node(node)
                nodes.append(node)
            
            # Connect nodes
            for i in range(49):
                dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))
            
            return dag
        
        def validate_dag(dag: DAG) -> bool:
            return Validator.validate_dag(dag)
        
        start_time = time.time()
        
        # Test with thread pool
        with ThreadPoolExecutor(max_workers=4) as executor:
            dags = list(executor.map(create_test_dag, range(20)))
            validation_results = list(executor.map(validate_dag, dags))
        
        thread_time = time.time() - start_time
        
        # Test with process pool
        start_time = time.time()
        with ProcessPoolExecutor(max_workers=4) as executor:
            dags = list(executor.map(create_test_dag, range(20)))
            validation_results = list(executor.map(validate_dag, dags))
        
        process_time = time.time() - start_time
        
        assert all(validation_results)
        assert len(dags) == 20
        assert thread_time < performance_config["max_execution_time"]
        assert process_time < performance_config["max_execution_time"]
    
    @pytest.mark.performance
    @pytest.mark.benchmark(group="serialization")
    def test_serialization_performance(self, benchmark, complex_dag):
        """Benchmark DAG serialization performance."""
        import json
        import pickle
        
        def serialize_dag():
            # Convert to dict for JSON serialization
            dag_dict = {
                "name": complex_dag.name,
                "description": complex_dag.description,
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "task_type": node.task_type,
                        "params": node.params
                    }
                    for node in complex_dag.nodes
                ],
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "condition": edge.condition
                    }
                    for edge in complex_dag.edges
                ]
            }\n            \n            json_data = json.dumps(dag_dict)\n            pickle_data = pickle.dumps(complex_dag)\n            \n            return json_data, pickle_data\n        \n        json_result, pickle_result = benchmark(serialize_dag)\n        assert len(json_result) > 0\n        assert len(pickle_result) > 0\n    \n    @pytest.mark.performance\n    @pytest.mark.slow\n    def test_stress_test_dag_operations(self, temp_dir, performance_config):\n        \"\"\"Stress test with intensive DAG operations.\"\"\"\n        storage = LocalStorage(temp_dir)\n        \n        # Create multiple DAGs with different patterns\n        dags = []\n        \n        for pattern in range(5):\n            dag = DAG(name=f\"stress_dag_{pattern}\")\n            \n            if pattern == 0:  # Linear chain\n                nodes = []\n                for i in range(200):\n                    node = Node(name=f\"linear_{i}\", task_type=\"python\")\n                    dag.add_node(node)\n                    nodes.append(node)\n                    if i > 0:\n                        dag.add_edge(Edge(source=nodes[i-1].id, target=node.id))\n            \n            elif pattern == 1:  # Star pattern\n                center_node = Node(name=\"center\", task_type=\"python\")\n                dag.add_node(center_node)\n                for i in range(100):\n                    leaf_node = Node(name=f\"leaf_{i}\", task_type=\"python\")\n                    dag.add_node(leaf_node)\n                    dag.add_edge(Edge(source=center_node.id, target=leaf_node.id))\n            \n            elif pattern == 2:  # Fan-in pattern\n                sink_node = Node(name=\"sink\", task_type=\"python\")\n                dag.add_node(sink_node)\n                for i in range(100):\n                    source_node = Node(name=f\"source_{i}\", task_type=\"python\")\n                    dag.add_node(source_node)\n                    dag.add_edge(Edge(source=source_node.id, target=sink_node.id))\n            \n            elif pattern == 3:  # Grid pattern\n                grid_size = 20\n                grid_nodes = {}\n                for row in range(grid_size):\n                    for col in range(grid_size):\n                        node = Node(name=f\"grid_{row}_{col}\", task_type=\"python\")\n                        dag.add_node(node)\n                        grid_nodes[(row, col)] = node\n                        \n                        # Connect to neighbors\n                        if row > 0:\n                            dag.add_edge(Edge(\n                                source=grid_nodes[(row-1, col)].id,\n                                target=node.id\n                            ))\n                        if col > 0:\n                            dag.add_edge(Edge(\n                                source=grid_nodes[(row, col-1)].id,\n                                target=node.id\n                            ))\n            \n            elif pattern == 4:  # Random pattern\n                nodes = []\n                for i in range(150):\n                    node = Node(name=f\"random_{i}\", task_type=\"python\")\n                    dag.add_node(node)\n                    nodes.append(node)\n                \n                import random\n                random.seed(42)  # Reproducible\n                for i in range(300):  # Add random edges\n                    source_idx = random.randint(0, len(nodes) - 1)\n                    target_idx = random.randint(0, len(nodes) - 1)\n                    if source_idx != target_idx:\n                        try:\n                            dag.add_edge(Edge(\n                                source=nodes[source_idx].id,\n                                target=nodes[target_idx].id\n                            ))\n                        except:\n                            pass  # Ignore cycles or duplicates\n            \n            dags.append(dag)\n        \n        # Perform stress operations\n        start_time = time.time()\n        \n        for i, dag in enumerate(dags):\n            # Validate\n            try:\n                Validator.validate_dag(dag)\n            except:\n                pass  # Some patterns might create cycles\n            \n            # Store and retrieve\n            dag_data = {\n                \"name\": dag.name,\n                \"node_count\": len(dag.nodes),\n                \"edge_count\": len(dag.edges)\n            }\n            storage.write(f\"stress_dag_{i}.json\", str(dag_data))\n            retrieved = storage.read(f\"stress_dag_{i}.json\")\n            assert retrieved is not None\n        \n        total_time = time.time() - start_time\n        \n        # Should complete within time limit\n        assert total_time < performance_config[\"max_execution_time\"]\n        \n        # Verify all DAGs were processed\n        assert len(dags) == 5\n        for dag in dags:\n            assert len(dag.nodes) > 0\n\n\nclass TestLoadTesting:\n    \"\"\"Load testing scenarios.\"\"\"\n    \n    @pytest.mark.performance\n    @pytest.mark.slow\n    def test_high_load_dag_creation(self, performance_config):\n        \"\"\"Test system under high load of DAG creation.\"\"\"\n        dags_created = []\n        \n        def create_dag_batch(batch_id: int) -> List[DAG]:\n            batch_dags = []\n            for i in range(10):  # 10 DAGs per batch\n                dag = DAG(name=f\"load_dag_{batch_id}_{i}\")\n                \n                # Add nodes\n                nodes = []\n                for j in range(20):\n                    node = Node(\n                        name=f\"node_{batch_id}_{i}_{j}\",\n                        task_type=\"python\",\n                        params={\"batch\": batch_id, \"dag\": i, \"node\": j}\n                    )\n                    dag.add_node(node)\n                    nodes.append(node)\n                \n                # Connect nodes\n                for k in range(19):\n                    dag.add_edge(Edge(source=nodes[k].id, target=nodes[k+1].id))\n                \n                batch_dags.append(dag)\n            \n            return batch_dags\n        \n        start_time = time.time()\n        \n        # Create 20 batches in parallel (200 DAGs total)\n        with ThreadPoolExecutor(max_workers=8) as executor:\n            batch_results = list(executor.map(create_dag_batch, range(20)))\n        \n        # Flatten results\n        for batch in batch_results:\n            dags_created.extend(batch)\n        \n        total_time = time.time() - start_time\n        \n        assert len(dags_created) == 200\n        assert total_time < performance_config[\"max_execution_time\"]\n        \n        # Verify all DAGs are valid\n        for dag in dags_created[:10]:  # Sample check\n            assert len(dag.nodes) == 20\n            assert len(dag.edges) == 19\n    \n    @pytest.mark.performance\n    @pytest.mark.memory_intensive\n    def test_memory_leak_detection(self, memory_monitor):\n        \"\"\"Test for memory leaks during repeated operations.\"\"\"\n        initial_memory = memory_monitor.memory_info().rss\n        \n        # Perform many create/destroy cycles\n        for cycle in range(100):\n            dag = DAG(name=f\"leak_test_{cycle}\")\n            \n            # Create and destroy nodes\n            nodes = []\n            for i in range(50):\n                node = Node(name=f\"node_{i}\", task_type=\"python\", params={\"data\": list(range(100))})\n                dag.add_node(node)\n                nodes.append(node)\n            \n            # Add edges\n            for i in range(49):\n                dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))\n            \n            # \"Use\" the DAG\n            Validator.validate_dag(dag)\n            \n            # Clear references\n            del dag\n            del nodes\n            \n            # Check memory every 10 cycles\n            if cycle % 10 == 0:\n                current_memory = memory_monitor.memory_info().rss\n                memory_increase = current_memory - initial_memory\n                \n                # Memory shouldn't grow too much (allow 100MB max)\n                assert memory_increase < 100 * 1024 * 1024, f\"Memory leak detected: {memory_increase / 1024 / 1024:.1f}MB increase\"\n    \n    @pytest.mark.performance\n    @pytest.mark.cpu_intensive\n    def test_cpu_intensive_operations(self, performance_config):\n        \"\"\"Test CPU-intensive operations.\"\"\"\n        start_time = time.time()\n        \n        def cpu_intensive_task(task_id: int):\n            \"\"\"Simulate CPU-intensive task.\"\"\"\n            dag = DAG(name=f\"cpu_task_{task_id}\")\n            \n            # Create complex nested structure\n            for level in range(5):  # 5 levels deep\n                for item in range(20):  # 20 items per level\n                    node = Node(\n                        name=f\"cpu_node_{task_id}_{level}_{item}\",\n                        task_type=\"python\",\n                        params={\n                            \"computation\": [i ** 2 for i in range(100)],\n                            \"level\": level,\n                            \"item\": item\n                        }\n                    )\n                    dag.add_node(node)\n            \n            # Validate multiple times\n            for _ in range(10):\n                try:\n                    Validator.validate_dag(dag)\n                except:\n                    pass\n            \n            return len(dag.nodes)\n        \n        # Run CPU-intensive tasks\n        with ThreadPoolExecutor(max_workers=psutil.cpu_count()) as executor:\n            results = list(executor.map(cpu_intensive_task, range(20)))\n        \n        total_time = time.time() - start_time\n        \n        assert len(results) == 20\n        assert all(result == 100 for result in results)  # Each task creates 100 nodes\n        assert total_time < performance_config[\"max_execution_time\"]\n\n\nclass TestScalabilityTests:\n    \"\"\"Scalability testing scenarios.\"\"\"\n    \n    @pytest.mark.performance\n    @pytest.mark.slow\n    @pytest.mark.parametrize(\"node_count\", [10, 100, 500, 1000, 2000])\n    def test_dag_scalability(self, node_count, assert_timing):\n        \"\"\"Test DAG operations scale appropriately with size.\"\"\"\n        with assert_timing(max_time=node_count * 0.01):  # Allow 10ms per node\n            dag = DAG(name=f\"scale_test_{node_count}\")\n            \n            # Create nodes\n            nodes = []\n            for i in range(node_count):\n                node = Node(name=f\"scale_node_{i}\", task_type=\"python\")\n                dag.add_node(node)\n                nodes.append(node)\n            \n            # Create edges (chain pattern for predictable complexity)\n            for i in range(node_count - 1):\n                dag.add_edge(Edge(source=nodes[i].id, target=nodes[i+1].id))\n            \n            # Validate\n            assert Validator.validate_dag(dag) is True\n            assert len(dag.nodes) == node_count\n            assert len(dag.edges) == node_count - 1\n    \n    @pytest.mark.performance\n    @pytest.mark.slow\n    @pytest.mark.parametrize(\"edge_density\", [0.1, 0.3, 0.5, 0.7, 0.9])\n    def test_edge_density_scalability(self, edge_density, assert_timing):\n        \"\"\"Test how edge density affects performance.\"\"\"\n        node_count = 100\n        max_edges = node_count * (node_count - 1) // 2  # Complete graph\n        target_edges = int(max_edges * edge_density)\n        \n        with assert_timing(max_time=30.0):  # 30 second limit\n            dag = DAG(name=f\"density_test_{edge_density}\")\n            \n            # Create nodes\n            nodes = []\n            for i in range(node_count):\n                node = Node(name=f\"density_node_{i}\", task_type=\"python\")\n                dag.add_node(node)\n                nodes.append(node)\n            \n            # Add edges based on density\n            import random\n            random.seed(42)  # Reproducible\n            edges_added = 0\n            \n            while edges_added < target_edges:\n                source_idx = random.randint(0, node_count - 1)\n                target_idx = random.randint(0, node_count - 1)\n                \n                if source_idx != target_idx:\n                    try:\n                        dag.add_edge(Edge(\n                            source=nodes[source_idx].id,\n                            target=nodes[target_idx].id\n                        ))\n                        edges_added += 1\n                    except:\n                        pass  # Edge might already exist or create cycle\n            \n            # Validate (may fail for high density due to cycles)\n            try:\n                is_valid = Validator.validate_dag(dag)\n            except:\n                is_valid = False\n            \n            assert len(dag.nodes) == node_count\n            # Lower density should be more likely to be valid\n            if edge_density <= 0.3:\n                assert is_valid is True