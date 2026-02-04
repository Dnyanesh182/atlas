"""
Short-term memory implementation.
Maintains recent context for ongoing conversations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.base_memory import BaseMemory
from atlas.core.schemas import MemoryEntry


class ShortTermMemory(BaseMemory):
    """
    Short-term memory for immediate context.
    
    Features:
    - Time-based expiration (default: 1 hour)
    - Limited capacity (LRU eviction)
    - Fast access
    - No persistence
    """
    
    def __init__(
        self,
        max_entries: int = 100,
        ttl_seconds: int = 3600,  # 1 hour
        **kwargs
    ):
        super().__init__(memory_type="short_term", **kwargs)
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """Store a short-term memory."""
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            memory_type=self.memory_type,
            importance=importance
        )
        
        # Evict old entries if at capacity
        if len(self.entries) >= self.max_entries:
            await self._evict_oldest()
        
        self.entries[entry.id] = entry
        return entry.id
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Retrieve recent memories."""
        # Clean expired entries
        await self._clean_expired()
        
        # Simple text matching (no vector search for short-term)
        results = []
        for entry in self.entries.values():
            if query.lower() in entry.content.lower():
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                results.append(entry)
                if len(results) >= top_k:
                    break
        
        return results
    
    async def update(self, memory_id: UUID, **kwargs) -> bool:
        """Update a memory entry."""
        if memory_id not in self.entries:
            return False
        
        entry = self.entries[memory_id]
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        return True
    
    async def delete(self, memory_id: UUID) -> bool:
        """Delete a memory entry."""
        if memory_id in self.entries:
            del self.entries[memory_id]
            return True
        return False
    
    async def consolidate(self) -> int:
        """Consolidate memories - promote important ones."""
        await self._clean_expired()
        
        # Find high-importance entries for promotion
        promotion_candidates = [
            entry for entry in self.entries.values()
            if entry.importance > 0.7 or entry.access_count > 5
        ]
        
        return len(promotion_candidates)
    
    async def _clean_expired(self):
        """Remove expired entries."""
        now = datetime.utcnow()
        expired = []
        
        for entry_id, entry in self.entries.items():
            age = (now - entry.created_at).total_seconds()
            if age > self.ttl_seconds:
                expired.append(entry_id)
        
        for entry_id in expired:
            del self.entries[entry_id]
    
    async def _evict_oldest(self):
        """Evict oldest entry."""
        if not self.entries:
            return
        
        oldest = min(
            self.entries.values(),
            key=lambda e: e.last_accessed
        )
        del self.entries[oldest.id]
    
    async def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get most recent memories."""
        await self._clean_expired()
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.created_at,
            reverse=True
        )
        return sorted_entries[:limit]
