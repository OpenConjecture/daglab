"""Core components for DAG construction and management."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Node(BaseModel):
    """Represents a node in the DAG."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    task_type: str = "python"
    params: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class Edge(BaseModel):
    """Represents an edge between nodes in the DAG."""
    source: str
    target: str
    condition: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """Represents an executable task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    function: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    

class DAG(BaseModel):
    """Directed Acyclic Graph for workflow orchestration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the DAG."""
        self.nodes.append(node)
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the DAG."""
        self.edges.append(edge)


class Pipeline(BaseModel):
    """A linear sequence of tasks."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tasks: List[Task] = Field(default_factory=list)
    

class Workflow(BaseModel):
    """A complete workflow definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    dag: DAG
    schedule: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "Node",
    "Edge",
    "Task",
    "DAG",
    "Pipeline",
    "Workflow",
]