"""
Vector store implementation for ATLAS memory systems.
Uses FAISS for efficient similarity search.
"""

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from atlas.core.schemas import MemoryEntry


class VectorStore:
    """
    Vector store for semantic memory retrieval.
    
    Features:
    - Efficient similarity search with FAISS
    - Metadata filtering
    - Persistence to disk
    - Incremental updates
    """
    
    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        persist_path: Optional[Path] = None
    ):
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.persist_path = persist_path
        self.vectorstore: Optional[FAISS] = None
        self.id_to_entry: Dict[str, MemoryEntry] = {}
        
        # Load existing store if available
        if persist_path and persist_path.exists():
            self.load()
    
    async def add_entries(
        self,
        entries: List[MemoryEntry]
    ) -> List[str]:
        """
        Add memory entries to vector store.
        
        Args:
            entries: Memory entries to add
            
        Returns:
            List of entry IDs
        """
        if not entries:
            return []
        
        # Extract texts and metadata
        texts = [entry.content for entry in entries]
        metadatas = [
            {
                "entry_id": str(entry.id),
                "memory_type": entry.memory_type,
                "importance": entry.importance,
                **entry.metadata
            }
            for entry in entries
        ]
        
        # Generate embeddings and add to store
        if self.vectorstore is None:
            self.vectorstore = await FAISS.afrom_texts(
                texts=texts,
                embedding=self.embedding_model,
                metadatas=metadatas
            )
        else:
            await self.vectorstore.aadd_texts(
                texts=texts,
                metadatas=metadatas
            )
        
        # Store entry mapping
        for entry in entries:
            self.id_to_entry[str(entry.id)] = entry
        
        return [str(entry.id) for entry in entries]
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[tuple[MemoryEntry, float]]:
        """
        Search for similar entries.
        
        Args:
            query: Search query
            top_k: Number of results
            filter_dict: Metadata filters
            score_threshold: Minimum similarity score
            
        Returns:
            List of (entry, score) tuples
        """
        if self.vectorstore is None:
            return []
        
        # Perform similarity search
        results = await self.vectorstore.asimilarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict
        )
        
        # Convert to MemoryEntry objects
        entries_with_scores = []
        for doc, score in results:
            if score >= score_threshold:
                entry_id = doc.metadata.get("entry_id")
                if entry_id in self.id_to_entry:
                    entry = self.id_to_entry[entry_id]
                    entries_with_scores.append((entry, score))
        
        return entries_with_scores
    
    async def delete_entry(self, entry_id: UUID) -> bool:
        """
        Delete an entry from the vector store.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            Success status
        """
        entry_id_str = str(entry_id)
        if entry_id_str in self.id_to_entry:
            del self.id_to_entry[entry_id_str]
            # Note: FAISS doesn't support direct deletion
            # In production, implement periodic rebuilding
            return True
        return False
    
    def save(self):
        """Persist vector store to disk."""
        if self.persist_path and self.vectorstore:
            self.persist_path.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss_path = self.persist_path / "faiss_index"
            self.vectorstore.save_local(str(faiss_path))
            
            # Save entry mapping
            mapping_path = self.persist_path / "entry_mapping.pkl"
            with open(mapping_path, "wb") as f:
                pickle.dump(self.id_to_entry, f)
    
    def load(self):
        """Load vector store from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            # Load FAISS index
            faiss_path = self.persist_path / "faiss_index"
            if faiss_path.exists():
                self.vectorstore = FAISS.load_local(
                    str(faiss_path),
                    self.embedding_model,
                    allow_dangerous_deserialization=True
                )
            
            # Load entry mapping
            mapping_path = self.persist_path / "entry_mapping.pkl"
            if mapping_path.exists():
                with open(mapping_path, "rb") as f:
                    self.id_to_entry = pickle.load(f)
        except Exception as e:
            print(f"Error loading vector store: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_entries": len(self.id_to_entry),
            "has_vectorstore": self.vectorstore is not None,
            "persist_path": str(self.persist_path) if self.persist_path else None
        }
