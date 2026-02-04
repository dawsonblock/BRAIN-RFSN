"""
Task Graph (DAG) for Hierarchical Planning.
Manages dependencies and execution order of sub-tasks.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import networkx as nx
import logging

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"

@dataclass
class TaskNode:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)

class TaskGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def add_task(self, task_id: str, description: str, dependencies: List[str] = None):
        """Add a task node to the graph."""
        node = TaskNode(
            id=task_id,
            description=description,
            dependencies=dependencies or []
        )
        self.graph.add_node(task_id, data=node)
        
        if dependencies:
            for dep in dependencies:
                self.graph.add_edge(dep, task_id)
                
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        if task_id in self.graph.nodes:
            return self.graph.nodes[task_id]['data']
        return None
        
    def get_ready_tasks(self) -> List[TaskNode]:
        """Return list of tasks that are PENDING and have all dependencies COMPLETED."""
        ready_tasks = []
        for task_id in self.graph.nodes:
            node = self.get_task(task_id)
            if node.status != TaskStatus.PENDING:
                continue
                
            is_blocked = False
            for parent in self.graph.predecessors(task_id):
                parent_node = self.get_task(parent)
                if parent_node.status != TaskStatus.COMPLETED:
                    is_blocked = True
                    break
            
            if not is_blocked:
                # Mark as READY internally if needed, but return them
                ready_tasks.append(node)
                
        return ready_tasks

    def update_task_status(self, task_id: str, status: TaskStatus, result: str = None):
        node = self.get_task(task_id)
        if node:
            node.status = status
            if result:
                node.result = result
            logger.info(f"📋 Task Update: [{task_id}] -> {status.value}")
            
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        for task_id in self.graph.nodes:
            if self.get_task(task_id).status != TaskStatus.COMPLETED:
                return False
        return True

    def to_dict(self) -> Dict:
        """Serialize for debugging/logging."""
        return {
            "nodes": [
                {
                    "id": n, 
                    "status": self.get_task(n).status.value,
                    "desc": self.get_task(n).description
                }
                for n in self.graph.nodes
            ]
        }
