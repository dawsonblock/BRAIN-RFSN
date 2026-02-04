# rfsn_kernel/tools/memory.py
"""Memory tools: remember and recall."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os
import json
import hashlib
from datetime import datetime


@dataclass
class MemoryChunk:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str


@dataclass
class RememberResult:
    chunk_id: str
    success: bool
    error: Optional[str] = None


@dataclass
class RecallResult:
    query: str
    chunks: List[MemoryChunk]
    error: Optional[str] = None


class SimpleMemoryStore:
    """
    Simple file-based memory store.
    For production, integrate with vector DB (already have VectorMemory).
    """

    def __init__(self, store_path: str):
        self.store_path = store_path
        os.makedirs(store_path, exist_ok=True)
        self.index_path = os.path.join(store_path, "index.json")
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
            with open(self.index_path, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {"chunks": []}

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store content and return chunk ID."""
        chunk_id = hashlib.sha256(
            f"{content}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        chunk = {
            "chunk_id": chunk_id,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Save chunk file
        chunk_path = os.path.join(self.store_path, f"{chunk_id}.json")
        with open(chunk_path, "w") as f:
            json.dump(chunk, f)

        # Update index
        self.index["chunks"].append({
            "chunk_id": chunk_id,
            "preview": content[:100],
            "metadata": metadata or {},
            "timestamp": chunk["timestamp"],
        })
        self._save_index()

        return chunk_id

    def query(self, query: str, k: int = 5) -> List[MemoryChunk]:
        """
        Simple keyword-based recall.
        For semantic search, use VectorMemory integration.
        """
        query_lower = query.lower()
        results = []

        for entry in self.index["chunks"]:
            chunk_id = entry["chunk_id"]
            chunk_path = os.path.join(self.store_path, f"{chunk_id}.json")

            if not os.path.exists(chunk_path):
                continue

            with open(chunk_path, "r") as f:
                chunk_data = json.load(f)

            content = chunk_data.get("content", "")
            if query_lower in content.lower():
                results.append(MemoryChunk(
                    chunk_id=chunk_data["chunk_id"],
                    content=content,
                    metadata=chunk_data.get("metadata", {}),
                    timestamp=chunk_data.get("timestamp", ""),
                ))

        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:k]


# Global store instance (can be overridden)
_memory_store: Optional[SimpleMemoryStore] = None


def get_memory_store(store_path: Optional[str] = None) -> SimpleMemoryStore:
    global _memory_store
    if _memory_store is None or store_path:
        path = store_path or os.path.join(os.getcwd(), ".rfsn", "memory")
        _memory_store = SimpleMemoryStore(path)
    return _memory_store


def remember(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    store_path: Optional[str] = None,
) -> RememberResult:
    """Store content in memory."""
    try:
        store = get_memory_store(store_path)
        chunk_id = store.store(content, metadata)
        return RememberResult(chunk_id=chunk_id, success=True)
    except Exception as e:
        return RememberResult(chunk_id="", success=False, error=str(e))


def recall(
    query: str,
    k: int = 5,
    store_path: Optional[str] = None,
) -> RecallResult:
    """Query memory for relevant chunks."""
    try:
        store = get_memory_store(store_path)
        chunks = store.query(query, k=k)
        return RecallResult(query=query, chunks=chunks)
    except Exception as e:
        return RecallResult(query=query, chunks=[], error=str(e))
