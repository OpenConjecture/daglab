"""Visualization components for DAGs and results."""

import plotly.graph_objects as go
import networkx as nx
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class DAGVisualizer:
    """Visualize DAG structures."""
    
    def __init__(self):
        self.layout_engine = "spring"
        self.node_colors = {
            "default": "#1f77b4",
            "running": "#ff7f0e",
            "success": "#2ca02c",
            "failed": "#d62728",
            "pending": "#9467bd"
        }
    
    def create_graph(self, dag: Any) -> nx.DiGraph:
        """Convert DAG to NetworkX graph."""
        G = nx.DiGraph()
        
        # Add nodes
        for node in dag.nodes:
            G.add_node(node.id, label=node.name, **node.metadata)
        
        # Add edges
        for edge in dag.edges:
            G.add_edge(edge.source, edge.target, **edge.metadata)
        
        return G
    
    def plot_interactive(self, dag: Any, status_map: Optional[Dict[str, str]] = None) -> go.Figure:
        """Create interactive Plotly visualization."""
        G = self.create_graph(dag)
        
        # Calculate layout
        if self.layout_engine == "spring":
            pos = nx.spring_layout(G)
        elif self.layout_engine == "hierarchical":
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        else:
            pos = nx.circular_layout(G)
        
        # Create edge trace
        edge_trace = go.Scatter(
            x=[],
            y=[],
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += (x0, x1, None)
            edge_trace['y'] += (y0, y1, None)
        
        # Create node trace
        node_trace = go.Scatter(
            x=[],
            y=[],
            mode='markers+text',
            hoverinfo='text',
            text=[],
            textposition="top center",
            marker=dict(
                showscale=False,
                size=20,
                color=[],
                line_width=2
            )
        )
        
        for node in G.nodes():
            x, y = pos[node]
            node_trace['x'] += (x,)
            node_trace['y'] += (y,)
            
            # Node color based on status
            if status_map and node in status_map:
                color = self.node_colors.get(status_map[node], self.node_colors["default"])
            else:
                color = self.node_colors["default"]
            
            node_trace['marker']['color'] += (color,)
            node_trace['text'] += (G.nodes[node].get('label', node),)
        
        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dag.name,
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
        )
        
        return fig
    
    def plot_static(self, dag: Any, output_path: Optional[str] = None) -> None:
        """Create static matplotlib visualization."""
        G = self.create_graph(dag)
        
        plt.figure(figsize=(12, 8))
        
        # Calculate layout
        if self.layout_engine == "spring":
            pos = nx.spring_layout(G, k=2, iterations=50)
        else:
            pos = nx.circular_layout(G)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.5, width=2)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color=self.node_colors["default"], 
                              node_size=2000, alpha=0.8)
        
        # Draw labels
        labels = {node: G.nodes[node].get('label', node) for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=10)
        
        plt.title(dag.name, fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()


class MetricsVisualizer:
    """Visualize execution metrics and results."""
    
    def __init__(self):
        sns.set_style("whitegrid")
        self.colors = sns.color_palette("husl", 8)
    
    def plot_execution_timeline(self, execution_data: List[Dict[str, Any]]) -> go.Figure:
        """Create Gantt chart of execution timeline."""
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(execution_data)
        
        fig = go.Figure()
        
        for idx, row in df.iterrows():
            fig.add_trace(go.Scatter(
                x=[row['start_time'], row['end_time']],
                y=[row['task_name'], row['task_name']],
                mode='lines+markers',
                line=dict(color=self.colors[idx % len(self.colors)], width=20),
                name=row['task_name'],
                showlegend=False
            ))
        
        fig.update_layout(
            title="Task Execution Timeline",
            xaxis_title="Time",
            yaxis_title="Tasks",
            height=400 + len(df) * 30,
            showlegend=False
        )
        
        return fig
    
    def plot_resource_usage(self, metrics: Dict[str, List[Tuple[float, float]]]) -> go.Figure:
        """Plot resource usage over time."""
        fig = go.Figure()
        
        for metric_name, values in metrics.items():
            times, measurements = zip(*values)
            fig.add_trace(go.Scatter(
                x=times,
                y=measurements,
                mode='lines',
                name=metric_name
            ))
        
        fig.update_layout(
            title="Resource Usage",
            xaxis_title="Time",
            yaxis_title="Usage",
            hovermode='x unified'
        )
        
        return fig
    
    def plot_success_rates(self, task_stats: Dict[str, Dict[str, int]]) -> go.Figure:
        """Plot task success rates."""
        tasks = list(task_stats.keys())
        success_rates = []
        
        for task in tasks:
            stats = task_stats[task]
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            
            if total > 0:
                success_rates.append(success / total * 100)
            else:
                success_rates.append(0)
        
        fig = go.Figure(data=[
            go.Bar(x=tasks, y=success_rates, marker_color=self.colors[2])
        ])
        
        fig.update_layout(
            title="Task Success Rates",
            xaxis_title="Task",
            yaxis_title="Success Rate (%)",
            yaxis_range=[0, 100]
        )
        
        return fig


__all__ = [
    "DAGVisualizer",
    "MetricsVisualizer",
]