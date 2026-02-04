"""
Unified memory manager coordinating all memory systems.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.schemas import MemoryEntry, Task, ExecutionTrace
from atlas.memory.short_term import ShortTermMemory
from atlas.memory.long_term import LongTermMemory
from atlas.memory.episodic import EpisodicMemory
from atlas.memory.semantic import SemanticMemory


class MemoryManager:
    """
    Unified memory manager for ATLAS.
    
    Coordinates:
    - Short-term memory (working memory)
    - Long-term memory (persistent knowledge)
    - Episodic memory (task history)
    - Semantic memory (facts and concepts)
    
    Handles:
    - Memory promotion (short -> long term)
    - Cross-memory search
    - Consolidation and cleanup
    """
    
    def __init__(
        self,
        persist_dir: Optional[Path] = None
    ):
        self.persist_dir = persist_dir or Path("data/memory")
        
        # Initialize memory systems
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(
            persist_path=self.persist_dir / "long_term"
        )
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(
            persist_path=self.persist_dir / "semantic"
        )
    
    async def remember(
        self,
        content: str,
        memory_type: str = "short_term",
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """
        Store a memory in the appropriate system.
        
        Args:
            content: Memory content
            memory_type: Type of memory (short_term, long_term, episodic, semantic)
            metadata: Additional metadata
            importance: Importance score
            
        Returns:
            Memory ID
        """
        memory_systems = {
            "short_term": self.short_term,
            "long_term": self.long_term,
            "episodic": self.episodic,
            "semantic": self.semantic
        }
        
        memory = memory_systems.get(memory_type, self.short_term)
        return await memory.store(content, metadata, importance)
    
    async def recall(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict[str, List[MemoryEntry]]:
        """
        Recall memories from multiple systems.
        
        Args:
            query: Search query
            memory_types: Types to search (None = all)
            top_k: Results per memory type
            
        Returns:
            Dictionary of memory type -> entries
        """
        if memory_types is None:
            memory_types = ["short_term", "long_term", "episodic", "semantic"]
        
        results = {}
        
        if "short_term" in memory_types:
            results["short_term"] = await self.short_term.retrieve(query, top_k)
        
        if "long_term" in memory_types:
            results["long_term"] = await self.long_term.retrieve(query, top_k)
        
        if "episodic" in memory_types:
            results["episodic"] = await self.episodic.retrieve(query, top_k)
        
        if "semantic" in memory_types:
            results["semantic"] = await self.semantic.retrieve(query, top_k)
        
        return results
    
    async def remember_task_execution(
        self,
        task: Task,
        trace: ExecutionTrace,
        outcome: str,
        lessons_learned: Optional[str] = None
    ) -> UUID:
        """Remember a task execution in episodic memory."""
        return await self.episodic.store_task_execution(
            task=task,
            trace=trace,
            outcome=outcome,
            lessons_learned=lessons_learned
        )
    
    async def learn_fact(
        self,
        fact: str,
        category: str,
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> UUID:
        """Learn a new fact in semantic memory."""
        return await self.semantic.store_fact(
            fact=fact,
            category=category,
            source=source,
            confidence=confidence
        )
    
    async def promote_to_long_term(
        self,
        memory_id: UUID,
        importance: Optional[float] = None
    ) -> Optional[UUID]:
        """
        Promote a short-term memory to long-term.
        
        Args:
            memory_id: Short-term memory ID
            importance: New importance score
            
        Returns:
            Long-term memory ID or None
        """
        entry = await self.short_term.get_by_id(memory_id)
        if not entry:
            return None
        
        # Store in long-term with updated importance
        new_importance = importance or entry.importance
        long_term_id = await self.long_term.store(
            content=entry.content,
            metadata=entry.metadata,
            importance=new_importance
        )
        
        # Optionally remove from short-term
        # await self.short_term.delete(memory_id)
        
        return long_term_id
    
    async def consolidate_all(self) -> Dict[str, int]:
        """
        Consolidate all memory systems.
        
        Returns:
            Dictionary of consolidation stats per memory type
        """
        results = {}
        
        results["short_term"] = await self.short_term.consolidate()
        results["long_term"] = await self.long_term.consolidate()
        results["episodic"] = await self.episodic.consolidate()
        results["semantic"] = await self.semantic.consolidate()
        
        return results
    
    async def get_context_for_task(
        self,
        task: Task,
        max_entries: int = 10
    ) -> str:
        """
        Build contextual memory for a task.
        
        Args:
            task: Task to build context for
            max_entries: Maximum memory entries
            
        Returns:
            Formatted context string
        """
        # Get recent short-term memories
        short_term_entries = await self.short_term.get_recent(limit=5)
        
        # Get relevant long-term memories
        long_term_results = await self.long_term.retrieve(
            query=task.description,
            top_k=5
        )
        
        # Get similar past tasks
        similar_tasks = await self.episodic.get_similar_past_tasks(
            task_description=task.description,
            limit=3
        )
        
        # Format context
        context_parts = []
        
        if short_term_entries:
            context_parts.append("## Recent Context")
            for entry in short_term_entries[:3]:
                context_parts.append(f"- {entry.content[:200]}")
        
        if long_term_results:
            context_parts.append("\n## Relevant Knowledge")
            for entry in long_term_results[:3]:
                context_parts.append(f"- {entry.content[:200]}")
        
        if similar_tasks:
            context_parts.append("\n## Similar Past Tasks")
            for task_info in similar_tasks:
                outcome = task_info.get("outcome", "Unknown")
                context_parts.append(f"- Outcome: {outcome}")
        
        return "\n".join(context_parts)
    
    def save_all(self):
        """Persist all memory systems to disk."""
        self.long_term.save()
        self.semantic.vector_store.save()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory systems."""
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats(),
            "episodic": self.episodic.get_stats(),
            "semantic": self.semantic.get_stats()
        }
