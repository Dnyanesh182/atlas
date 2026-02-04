"""
Long-term memory implementation with vector storage.
Persistent memory for knowledge retention.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.base_memory import BaseMemory
from atlas.core.schemas import MemoryEntry
from atlas.memory.vector_store import VectorStore


class LongTermMemory(BaseMemory):
    """
    Long-term memory with vector search.
    
    Features:
    - Persistent storage
    - Vector similarity search
    - Importance-based retention
    - Automatic consolidation
    """
    
    def __init__(
        self,
        persist_path: Optional[Path] = None,
        min_importance: float = 0.3,
        **kwargs
    ):
        super().__init__(memory_type="long_term", **kwargs)
        self.min_importance = min_importance
        self.vector_store = VectorStore(persist_path=persist_path)
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """Store a long-term memory."""
        # Only store if meets importance threshold
        if importance < self.min_importance:
            return None
        
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            memory_type=self.memory_type,
            importance=importance
        )
        
        # Store in local dict and vector store
        self.entries[entry.id] = entry
        await self.vector_store.add_entries([entry])
        
        return entry.id
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Retrieve relevant memories using vector search."""
        results = await self.vector_store.search(
            query=query,
            top_k=top_k,
            filter_dict=filters
        )
        
        # Update access stats
        entries = []
        for entry, score in results:
            entry.access_count += 1
            entries.append(entry)
        
        return entries
    
    async def update(self, memory_id: UUID, **kwargs) -> bool:
        """Update a memory entry."""
        if memory_id not in self.entries:
            return False
        
        entry = self.entries[memory_id]
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        # Re-index if content changed
        if "content" in kwargs:
            await self.vector_store.add_entries([entry])
        
        return True
    
    async def delete(self, memory_id: UUID) -> bool:
        """Delete a memory entry."""
        if memory_id in self.entries:
            del self.entries[memory_id]
            await self.vector_store.delete_entry(memory_id)
            return True
        return False
    
    async def consolidate(self) -> int:
        """Consolidate and compress memories."""
        # Remove low-importance, rarely-accessed memories
        to_remove = []
        
        for entry_id, entry in self.entries.items():
            if entry.importance < self.min_importance and entry.access_count < 2:
                to_remove.append(entry_id)
        
        for entry_id in to_remove:
            await self.delete(entry_id)
        
        # Save to disk
        self.vector_store.save()
        
        return len(to_remove)
    
    async def batch_store(
        self,
        contents: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        importance_list: Optional[List[float]] = None
    ) -> List[UUID]:
        """Store multiple memories efficiently."""
        if metadata_list is None:
            metadata_list = [{}] * len(contents)
        if importance_list is None:
            importance_list = [0.5] * len(contents)
        
        entries = []
        for content, metadata, importance in zip(contents, metadata_list, importance_list):
            if importance >= self.min_importance:
                entry = MemoryEntry(
                    content=content,
                    metadata=metadata,
                    memory_type=self.memory_type,
                    importance=importance
                )
                entries.append(entry)
                self.entries[entry.id] = entry
        
        # Batch add to vector store
        if entries:
            await self.vector_store.add_entries(entries)
        
        return [entry.id for entry in entries]
    
    def save(self):
        """Persist memories to disk."""
        self.vector_store.save()
    
    def load(self):
        """Load memories from disk."""
        self.vector_store.load()
