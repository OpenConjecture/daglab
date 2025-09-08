"""Simple DAG example demonstrating basic functionality."""

from daglab import DAG, Node, Edge
from daglab.compute import LocalCompute
from daglab.visual import DAGVisualizer


def create_simple_dag():
    """Create a simple computational DAG."""
    # Initialize DAG
    dag = DAG(name="simple_math_dag")
    
    # Define node functions
    def input_data():
        return {"values": [1, 2, 3, 4, 5]}
    
    def double_values(data):
        return {"doubled": [v * 2 for v in data["values"]]}
    
    def sum_values(data):
        return {"sum": sum(data["doubled"])}
    
    def print_result(data):
        print(f"Final result: {data['sum']}")
        return data
    
    # Create nodes
    input_node = Node(id="input", function=input_data)
    double_node = Node(id="double", function=double_values)
    sum_node = Node(id="sum", function=sum_values)
    output_node = Node(id="output", function=print_result)
    
    # Add nodes to DAG
    dag.add_node(input_node)
    dag.add_node(double_node)
    dag.add_node(sum_node)
    dag.add_node(output_node)
    
    # Define edges
    dag.add_edge(Edge(source="input", target="double"))
    dag.add_edge(Edge(source="double", target="sum"))
    dag.add_edge(Edge(source="sum", target="output"))
    
    return dag


def main():
    """Run the simple DAG example."""
    # Create DAG
    dag = create_simple_dag()
    
    # Validate DAG
    dag.validate()
    print(f"DAG '{dag.name}' is valid!")
    
    # Visualize DAG
    visualizer = DAGVisualizer()
    visualizer.visualize(dag, show=True)
    
    # Execute DAG
    compute = LocalCompute()
    result = compute.execute(dag)
    
    print(f"Execution completed in {result.execution_time:.2f} seconds")
    print(f"Node results: {result.node_results}")


if __name__ == "__main__":
    main()