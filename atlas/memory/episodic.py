"""
Episodic memory for task history and experiences.
Stores past task executions and outcomes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.base_memory import BaseMemory
from atlas.core.schemas import MemoryEntry, Task, ExecutionTrace


class EpisodicMemory(BaseMemory):
    """
    Episodic memory for task execution history.
    
    Features:
    - Task outcome storage
    - Success/failure pattern recognition
    - Experience-based learning
    - Temporal organization
    """
    
    def __init__(self, **kwargs):
        super().__init__(memory_type="episodic", **kwargs)
        self.task_history: Dict[UUID, Dict[str, Any]] = {}
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """Store an episodic memory."""
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            memory_type=self.memory_type,
            importance=importance
        )
        
        self.entries[entry.id] = entry
        return entry.id
    
    async def store_task_execution(
        self,
        task: Task,
        trace: ExecutionTrace,
        outcome: str,
        lessons_learned: Optional[str] = None
    ) -> UUID:
        """
        Store a task execution episode.
        
        Args:
            task: Executed task
            trace: Execution trace
            outcome: Success/failure description
            lessons_learned: Reflection on the task
            
        Returns:
            Memory entry ID
        """
        content = f"""
        Task Execution Episode:
        
        Task: {task.description}
        Status: {task.status}
        Agent: {trace.agent_type}
        Outcome: {outcome}
        Duration: {trace.duration}s
        Cost: ${trace.cost:.4f}
        
        {f"Lessons Learned: {lessons_learned}" if lessons_learned else ""}
        """
        
        metadata = {
            "task_id": str(task.id),
            "task_status": task.status.value,
            "agent_type": trace.agent_type.value,
            "duration": trace.duration,
            "cost": trace.cost,
            "timestamp": trace.timestamp.isoformat(),
            "success": task.status.value == "completed"
        }
        
        entry_id = await self.store(
            content=content.strip(),
            metadata=metadata,
            importance=0.8 if metadata["success"] else 0.9  # Failures more important
        )
        
        # Also store in task history
        self.task_history[task.id] = {
            "task": task,
            "trace": trace,
            "outcome": outcome,
            "lessons_learned": lessons_learned,
            "entry_id": entry_id
        }
        
        return entry_id
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Retrieve relevant episodes."""
        # Simple text-based search
        results = []
        
        for entry in self.entries.values():
            # Apply filters
            if filters:
                if not all(
                    entry.metadata.get(k) == v
                    for k, v in filters.items()
                ):
                    continue
            
            # Text match
            if query.lower() in entry.content.lower():
                results.append(entry)
                if len(results) >= top_k:
                    break
        
        # Sort by importance and recency
        results.sort(
            key=lambda e: (e.importance, e.created_at),
            reverse=True
        )
        
        return results[:top_k]
    
    async def update(self, memory_id: UUID, **kwargs) -> bool:
        """Update an episode."""
        if memory_id not in self.entries:
            return False
        
        entry = self.entries[memory_id]
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        return True
    
    async def delete(self, memory_id: UUID) -> bool:
        """Delete an episode."""
        if memory_id in self.entries:
            del self.entries[memory_id]
            return True
        return False
    
    async def consolidate(self) -> int:
        """Consolidate episodes - summarize patterns."""
        # In production, use LLM to summarize patterns
        # For now, just remove old low-importance entries
        
        # Keep last 1000 episodes
        if len(self.entries) > 1000:
            sorted_entries = sorted(
                self.entries.items(),
                key=lambda x: x[1].created_at
            )
            
            to_remove = sorted_entries[:-1000]
            for entry_id, _ in to_remove:
                del self.entries[entry_id]
            
            return len(to_remove)
        
        return 0
    
    async def get_similar_past_tasks(
        self,
        task_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past task executions."""
        entries = await self.retrieve(
            query=task_description,
            top_k=limit
        )
        
        # Map back to task history
        similar_tasks = []
        for entry in entries:
            task_id = entry.metadata.get("task_id")
            if task_id:
                task_uuid = UUID(task_id)
                if task_uuid in self.task_history:
                    similar_tasks.append(self.task_history[task_uuid])
        
        return similar_tasks
    
    async def get_success_rate(
        self,
        task_type: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> float:
        """Calculate success rate for tasks."""
        relevant_entries = []
        
        for entry in self.entries.values():
            if task_type and entry.metadata.get("task_type") != task_type:
                continue
            if agent_type and entry.metadata.get("agent_type") != agent_type:
                continue
            relevant_entries.append(entry)
        
        if not relevant_entries:
            return 0.0
        
        successful = sum(
            1 for e in relevant_entries
            if e.metadata.get("success", False)
        )
        
        return successful / len(relevant_entries)
