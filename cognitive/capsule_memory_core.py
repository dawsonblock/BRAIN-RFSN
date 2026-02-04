"""
Capsule Memory Core.
The episodic memory store. Handles storage and retrieval of time-stamped experience capsules.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class MemoryCapsule:
    id: int
    content: str
    type: str # 'task', 'thought', 'dream', 'identity'
    context: Dict[str, Any]
    emotion_profile: Dict[str, float]
    tags: List[str]
    self_relevance: float
    timestamp: float

class CapsuleMemoryCore:
    def __init__(self, db_path="memory_core.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capsules (
                    id INTEGER PRIMARY KEY,
                    content TEXT,
                    type TEXT,
                    context_json TEXT,
                    emotion_json TEXT,
                    tags_json TEXT,
                    self_relevance REAL,
                    timestamp REAL
                )
            """)

    def create_capsule(self, content: str, context: Dict, emotion_profile: Dict, tags: List[str], self_relevance: float) -> MemoryCapsule:
        """Encodes an experience into a permanent memory capsule."""
        timestamp = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO capsules (content, type, context_json, emotion_json, tags_json, self_relevance, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (content, 'episodic', json.dumps(context), json.dumps(emotion_profile), json.dumps(tags), self_relevance, timestamp))
            
            return MemoryCapsule(
                id=cursor.lastrowid,
                content=content,
                type='episodic',
                context=context,
                emotion_profile=emotion_profile,
                tags=tags,
                self_relevance=self_relevance,
                timestamp=timestamp
            )

    def retrieve_capsules(self, min_self_relevance: float = 0.5, limit: int = 10) -> List[MemoryCapsule]:
        """Retrieves memories relevant to the self."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, content, type, context_json, emotion_json, tags_json, self_relevance, timestamp
                FROM capsules WHERE self_relevance >= ? ORDER BY timestamp DESC LIMIT ?
            """, (min_self_relevance, limit))
            
            return [
                MemoryCapsule(
                    id=row[0], content=row[1], type=row[2],
                    context=json.loads(row[3]), emotion_profile=json.loads(row[4]),
                    tags=json.loads(row[5]), self_relevance=row[6], timestamp=row[7]
                ) for row in cursor.fetchall()
            ]

    def get_statistics(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM capsules").fetchone()[0]
        return {"total_capsules": count, "storage_type": "sqlite"}

# Singleton
_memory_core: Optional[CapsuleMemoryCore] = None
def get_memory_core():
    global _memory_core
    if _memory_core is None:
        _memory_core = CapsuleMemoryCore()
    return _memory_core

