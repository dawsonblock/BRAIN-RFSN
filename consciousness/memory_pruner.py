"""
Synaptic Pruner.
Handles memory consolidation and database hygiene during the REM cycle.
"""
import sqlite3
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PruningStats:
    deleted_episodes: int
    consolidated_summaries: int
    space_reclaimed_mb: float

class MemoryPruner:
    def __init__(self, db_path: str = "memory_core.db"):
        self.db_path = db_path
        
    def execute_rem_cycle(self) -> PruningStats:
        """
        The main cleanup routine. Runs inside the Dream Cycle.
        """
        logger.info("🧹 STARTING SYNAPTIC PRUNING...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Ensure tables exist (for safety if run standalone)
            cursor.execute("CREATE TABLE IF NOT EXISTS memory_capsules (id INTEGER PRIMARY KEY, content TEXT, type TEXT, importance REAL, timestamp REAL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS context_blobs (id INTEGER PRIMARY KEY, capsule_id INTEGER)")

            # 1. CONSOLIDATION: Summarize the day's high-volume events
            # Find all 'task_processing' events from the last 24h that weren't errors
            cursor.execute("""
                SELECT content FROM memory_capsules 
                WHERE type='task_processing' 
                AND timestamp > ? 
                AND importance < 0.8
            """, (time.time() - 86400,))
            
            raw_logs = cursor.fetchall()
            if raw_logs:
                # Create a single "Day Summary" capsule
                summary_content = f"Processed {len(raw_logs)} routine tasks. Systems nominal."
                self._create_summary_node(cursor, summary_content)
            
            # 2. PRUNING: Delete the raw data we just summarized
            # Delete episodic logs older than 24h that are low importance
            cursor.execute("""
                DELETE FROM memory_capsules 
                WHERE timestamp < ? 
                AND importance < 0.5 
                AND type != 'core_identity'
            """, (time.time() - 86400,))
            deleted_count = cursor.rowcount
            
            # 3. GARBAGE COLLECTION: Remove orphaned context blobs
            cursor.execute("DELETE FROM context_blobs WHERE capsule_id NOT IN (SELECT id FROM memory_capsules)")
            
            # 4. OPTIMIZATION: Rebuild database file structure
            conn.commit()
            try:
                cursor.execute("VACUUM") # Physically reclaim disk space
            except Exception:
                pass 
            
            # Initialize kb_pruned for the return statement
            kb_pruned = 0

            # 5. KNOWLEDGE BASE PRUNING (Synaptic Pruning)
            from learning.knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            if kb:
                original_size = len(kb.entries)
                # Keep survival rules and high-confidence heuristics
                kb.entries = [
                    e for e in kb.entries 
                    if e['category'] == 'survival_rule' 
                    or e['confidence'] > 0.3 
                    or (time.time() - e['timestamp'] < 3600) # Keep very recent anyway
                ]
                kb_pruned = original_size - len(kb.entries)
                logger.info(f"🧠 KNOWLEDGE BASE: Pruned {kb_pruned} weak heuristics.")

            return PruningStats(
                deleted_episodes=deleted_count + kb_pruned,
                consolidated_summaries=1 if raw_logs else 0,
                space_reclaimed_mb=0.0 
            )
            
        finally:
            conn.close()

    def _create_summary_node(self, cursor, content: str):
        """Writes a compressed 'Long Term Memory' node."""
        cursor.execute("""
            INSERT INTO memory_capsules (content, type, importance, timestamp)
            VALUES (?, 'daily_summary', 1.0, ?)
        """, (content, time.time()))


