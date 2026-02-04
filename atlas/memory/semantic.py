"""
Semantic memory for factual knowledge and concepts.
Stores learned facts, rules, and domain knowledge.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from atlas.core.base_memory import BaseMemory
from atlas.core.schemas import MemoryEntry
from atlas.memory.vector_store import VectorStore


class SemanticMemory(BaseMemory):
    """
    Semantic memory for factual knowledge.
    
    Features:
    - Fact storage and retrieval
    - Concept relationships
    - Domain knowledge
    - Vector-based semantic search
    """
    
    def __init__(
        self,
        persist_path: Optional[Path] = None,
        **kwargs
    ):
        super().__init__(memory_type="semantic", **kwargs)
        self.vector_store = VectorStore(persist_path=persist_path)
        self.knowledge_graph: Dict[str, List[str]] = {}  # Concept relationships
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> UUID:
        """Store a semantic memory (fact/concept)."""
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            memory_type=self.memory_type,
            importance=importance
        )
        
        self.entries[entry.id] = entry
        await self.vector_store.add_entries([entry])
        
        return entry.id
    
    async def store_fact(
        self,
        fact: str,
        category: str,
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> UUID:
        """
        Store a factual knowledge entry.
        
        Args:
            fact: The factual statement
            category: Knowledge category
            source: Source of the fact
            confidence: Confidence score (0-1)
            
        Returns:
            Memory entry ID
        """
        metadata = {
            "category": category,
            "source": source,
            "confidence": confidence,
            "type": "fact"
        }
        
        return await self.store(
            content=fact,
            metadata=metadata,
            importance=confidence
        )
    
    async def store_concept(
        self,
        concept: str,
        definition: str,
        related_concepts: Optional[List[str]] = None
    ) -> UUID:
        """
        Store a concept definition.
        
        Args:
            concept: Concept name
            definition: Concept definition
            related_concepts: Related concepts
            
        Returns:
            Memory entry ID
        """
        content = f"Concept: {concept}\n\nDefinition: {definition}"
        
        metadata = {
            "concept": concept,
            "type": "concept",
            "related_concepts": related_concepts or []
        }
        
        entry_id = await self.store(
            content=content,
            metadata=metadata,
            importance=0.7
        )
        
        # Update knowledge graph
        if related_concepts:
            self.knowledge_graph[concept] = related_concepts
        
        return entry_id
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Retrieve relevant semantic memories."""
        results = await self.vector_store.search(
            query=query,
            top_k=top_k,
            filter_dict=filters
        )
        
        return [entry for entry, score in results]
    
    async def retrieve_by_category(
        self,
        category: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Retrieve facts by category."""
        return await self.retrieve(
            query=category,
            top_k=limit,
            filters={"category": category}
        )
    
    async def update(self, memory_id: UUID, **kwargs) -> bool:
        """Update a semantic memory."""
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
        """Delete a semantic memory."""
        if memory_id in self.entries:
            del self.entries[memory_id]
            await self.vector_store.delete_entry(memory_id)
            return True
        return False
    
    async def consolidate(self) -> int:
        """Consolidate knowledge - merge duplicates."""
        # In production, use LLM to detect and merge duplicate facts
        consolidated = 0
        
        # Remove low-confidence facts
        to_remove = []
        for entry_id, entry in self.entries.items():
            confidence = entry.metadata.get("confidence", 1.0)
            if confidence < 0.3:
                to_remove.append(entry_id)
        
        for entry_id in to_remove:
            await self.delete(entry_id)
            consolidated += 1
        
        # Save to disk
        self.vector_store.save()
        
        return consolidated
    
    async def get_related_concepts(self, concept: str) -> List[str]:
        """Get concepts related to the given concept."""
        return self.knowledge_graph.get(concept, [])
    
    async def learn_from_text(
        self,
        text: str,
        category: str,
        source: Optional[str] = None
    ) -> List[UUID]:
        """
        Extract and store facts from text.
        
        Args:
            text: Text to learn from
            category: Knowledge category
            source: Source of the text
            
        Returns:
            List of created memory IDs
        """
        # In production, use LLM to extract facts
        # For now, simple sentence splitting
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        memory_ids = []
        for sentence in sentences[:10]:  # Limit to avoid spam
            if len(sentence) > 20:  # Skip very short sentences
                entry_id = await self.store_fact(
                    fact=sentence,
                    category=category,
                    source=source,
                    confidence=0.7
                )
                memory_ids.append(entry_id)
        
        return memory_ids
