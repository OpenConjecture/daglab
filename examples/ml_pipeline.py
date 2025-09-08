"""ML Pipeline DAG example with model training and inference."""

import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

from daglab import DAG, Node, Edge
from daglab.compute import LocalCompute
from daglab.storage import LocalStorage
from daglab.visual import DAGVisualizer


def create_ml_pipeline_dag():
    """Create an ML pipeline DAG."""
    dag = DAG(name="ml_classification_pipeline")
    
    # Data generation
    def generate_data():
        X, y = make_classification(
            n_samples=1000,
            n_features=20,
            n_informative=15,
            n_redundant=5,
            random_state=42
        )
        return {"X": X, "y": y}
    
    # Data splitting
    def split_data(data):
        X_train, X_test, y_train, y_test = train_test_split(
            data["X"], data["y"], test_size=0.2, random_state=42
        )
        return {
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test
        }
    
    # Feature preprocessing
    def preprocess_features(data):
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(data["X_train"])
        X_test_scaled = scaler.transform(data["X_test"])
        return {
            "X_train_scaled": X_train_scaled,
            "X_test_scaled": X_test_scaled,
            "y_train": data["y_train"],
            "y_test": data["y_test"],
            "scaler": scaler
        }
    
    # Model training
    def train_model(data):
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(data["X_train_scaled"], data["y_train"])
        return {
            "model": model,
            "X_test_scaled": data["X_test_scaled"],
            "y_test": data["y_test"]
        }
    
    # Model evaluation
    def evaluate_model(data):
        model = data["model"]
        predictions = model.predict(data["X_test_scaled"])
        accuracy = accuracy_score(data["y_test"], predictions)
        report = classification_report(data["y_test"], predictions)
        
        print(f"Model Accuracy: {accuracy:.4f}")
        print("\nClassification Report:")
        print(report)
        
        return {
            "accuracy": accuracy,
            "predictions": predictions,
            "report": report,
            "model": model
        }
    
    # Create nodes
    nodes = {
        "data_gen": Node(id="data_gen", function=generate_data),
        "data_split": Node(id="data_split", function=split_data),
        "preprocess": Node(id="preprocess", function=preprocess_features),
        "train": Node(id="train", function=train_model),
        "evaluate": Node(id="evaluate", function=evaluate_model),
    }
    
    # Add nodes to DAG
    for node in nodes.values():
        dag.add_node(node)
    
    # Define pipeline edges
    dag.add_edge(Edge(source="data_gen", target="data_split"))
    dag.add_edge(Edge(source="data_split", target="preprocess"))
    dag.add_edge(Edge(source="preprocess", target="train"))
    dag.add_edge(Edge(source="train", target="evaluate"))
    
    return dag


def main():
    """Run the ML pipeline example."""
    # Create DAG
    dag = create_ml_pipeline_dag()
    
    # Validate DAG
    dag.validate()
    print(f"ML Pipeline DAG '{dag.name}' is valid!\n")
    
    # Visualize DAG
    visualizer = DAGVisualizer()
    visualizer.visualize(dag, show=True)
    
    # Execute DAG
    compute = LocalCompute()
    result = compute.execute(dag)
    
    print(f"\nPipeline execution completed in {result.execution_time:.2f} seconds")
    
    # Save model if needed
    storage = LocalStorage(base_path="./ml_models")
    model = result.node_results["evaluate"]["model"]
    storage.save("random_forest_model.pkl", model)
    print("\nModel saved to ./ml_models/random_forest_model.pkl")


if __name__ == "__main__":
    main()