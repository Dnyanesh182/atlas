"""
Base memory abstraction for ATLAS memory systems.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.schemas import MemoryEntry


class BaseMemory(ABC):
    """
    Abstract base class for memory systems.
    
    Supports:
    - Storage and retrieval
    - Vector similarity search
    - Memory consolidation
    - Importance-based retention
    """
    
    def __init__(self, memory_type: str, **kwargs):
        self.memory_type = memory_type
        self.config = kwargs
        self.entries: Dict[UUID, MemoryEntry] = {}
    
    @abstractmethod
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """
        Store a memory entry.
        
        Args:
            content: Memory content
            metadata: Additional metadata
            importance: Importance score (0-1)
            
        Returns:
            Memory entry ID
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """
        Retrieve relevant memories.
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            List of relevant memory entries
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        memory_id: UUID,
        **kwargs
    ) -> bool:
        """
        Update a memory entry.
        
        Args:
            memory_id: Memory to update
            **kwargs: Fields to update
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: UUID) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: Memory to delete
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def consolidate(self) -> int:
        """
        Consolidate and compress memories.
        
        Returns:
            Number of memories consolidated
        """
        pass
    
    async def get_by_id(self, memory_id: UUID) -> Optional[MemoryEntry]:
        """Get memory by ID."""
        return self.entries.get(memory_id)
    
    async def get_all(self) -> List[MemoryEntry]:
        """Get all memories."""
        return list(self.entries.values())
    
    async def clear(self) -> int:
        """Clear all memories."""
        count = len(self.entries)
        self.entries.clear()
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "memory_type": self.memory_type,
            "total_entries": len(self.entries),
            "total_size": sum(len(e.content) for e in self.entries.values()),
            "average_importance": sum(e.importance for e in self.entries.values()) / max(len(self.entries), 1)
        }
