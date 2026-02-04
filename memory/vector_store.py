"""
Vector Memory Store using ChromaDB.
Provides semantic memory capabilities for RAG-enhanced cognition.
"""
from __future__ import annotations

import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MemoryFragment:
    """A retrieved memory fragment with relevance score."""
    text: str
    metadata: Dict[str, Any]
    distance: float  # Lower is more similar
    
    @property
    def relevance(self) -> float:
        """Convert distance to a 0-1 relevance score."""
        return max(0.0, 1.0 - self.distance)


class VectorMemory:
    """
    Semantic memory store using ChromaDB for vector similarity search.
    Enables RAG (Retrieval-Augmented Generation) for the agent.
    """
    
    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = "rfsn_memory"):
        """
        Initialize the vector memory store.
        
        Args:
            persist_directory: Path for persistent storage. None for in-memory only.
            collection_name: Name of the ChromaDB collection.
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        if not CHROMADB_AVAILABLE:
            logger.warning("⚠️ ChromaDB not available. Falling back to Lite Semantic Store (Fuzzy Match).")
            self.client = "LITE_MODE"
            self.collection = [] # List of dicts for fuzzy search
            return
        
        try:
            if persist_directory:
                self.client = chromadb.PersistentClient(path=persist_directory)
            else:
                self.client = chromadb.Client()
            
            # Get or create collection with default embedding function
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            
            logger.info(f"🧠 VectorMemory initialized. Collection: {collection_name}, Items: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorMemory: {e}")
            self.client = None
            self.collection = None
    
    def _generate_id(self, text: str) -> str:
        """Generate a deterministic ID from text content."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def store(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a memory in the vector database or lite store."""
        if self.client == "LITE_MODE":
            self.collection.append({
                "id": self._generate_id(text),
                "text": text,
                "metadata": metadata or {"_stored": "true"}
            })
            return True

        if not self.collection:
            return False
        
        try:
            doc_id = self._generate_id(text)
            meta = metadata if metadata else {"_stored": "true"}
            self.collection.upsert(
                documents=[text],
                metadatas=[meta],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    def retrieve(self, query: str, k: int = 5, where: Optional[Dict] = None) -> List[MemoryFragment]:
        """Retrieve semantically (or fuzzy) similar memories."""
        if self.client == "LITE_MODE":
            # Simple fuzzy match based on word overlap
            query_words = set(query.lower().split())
            results = []
            for item in self.collection:
                item_words = set(item["text"].lower().split())
                overlap = len(query_words.intersection(item_words))
                if overlap > 0:
                    score = overlap / max(len(query_words), len(item_words))
                    results.append(MemoryFragment(
                        text=item["text"],
                        metadata=item["metadata"],
                        distance=1.0 - score
                    ))
            return sorted(results, key=lambda x: x.distance)[:k]

        if not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count()) if self.collection.count() > 0 else k,
                where=where
            )
            
            fragments = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    fragment = MemoryFragment(
                        text=doc,
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {},
                        distance=results['distances'][0][i] if results['distances'] else 0.0
                    )
                    fragments.append(fragment)
            
            logger.debug(f"🔍 Retrieved {len(fragments)} memories for query: {query[:30]}...")
            return fragments
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def clear(self) -> bool:
        """Clear all memories from the collection."""
        if not self.client:
            return False
        
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("🧹 VectorMemory cleared.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False
    
    def count(self) -> int:
        """Return the number of stored memories."""
        if not self.collection:
            return 0
        return self.collection.count()


# Singleton instance
_vector_memory: Optional[VectorMemory] = None


DEFAULT_MEMORY_DIR = "rfsn_memory_store"

def get_vector_memory(persist_directory: Optional[str] = None) -> VectorMemory:
    """Get the singleton VectorMemory instance."""
    global _vector_memory
    if _vector_memory is None:
        # Default to persistent storage if not specified
        directory = persist_directory or DEFAULT_MEMORY_DIR
        _vector_memory = VectorMemory(persist_directory=directory)
    return _vector_memory
