"""
Knowledge Base.
Long-term storage for learned heuristics, survival rules, and solution patterns.
"""
from typing import List, Dict, Any
import time

class KnowledgeBase:
    def __init__(self):
        self.entries = []
        self.success_history = [] # 1 for success, 0 for fail

    def add_knowledge(self, category: str, title: str, content: str, tags: List[str], confidence: float):
        entry = {
            "id": len(self.entries) + 1,
            "category": category,
            "title": title,
            "content": content,
            "tags": tags,
            "confidence": confidence,
            "timestamp": time.time()
        }
        self.entries.append(entry)

    def retrieve_knowledge(self, category: str, min_confidence: float = 0.5, limit: int = 5) -> List[Any]:
        # Simple filter
        matches = [
            e for e in self.entries 
            if e['category'] == category and e['confidence'] >= min_confidence
        ]
        return sorted(matches, key=lambda x: x['confidence'], reverse=True)[:limit]

    def record_outcome(self, success: bool):
        self.success_history.append(1 if success else 0)
        if len(self.success_history) > 100:
            self.success_history.pop(0)

    def get_recent_success_rate(self) -> float:
        if not self.success_history:
            return 1.0 # Optimistic default
        return sum(self.success_history) / len(self.success_history)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self.entries),
            "survival_rules": len([e for e in self.entries if e['category'] == 'survival_rule']),
            "recent_success_rate": self.get_recent_success_rate()
        }

_kb = None
def get_knowledge_base():
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


