# cognitive/memory_consolidation.py
"""
Memory Consolidation: Transforms episodic memories into semantic knowledge.
Like biological sleep-based memory consolidation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

from .episodic_memory import EpisodicMemory, Episode, EpisodeQuery


@dataclass
class SemanticKnowledge:
    """Extracted knowledge from multiple episodes."""
    knowledge_id: str
    topic: str
    insight: str
    confidence: float  # 0.0 to 1.0
    source_episodes: List[str]
    timestamp: str


class MemoryConsolidator:
    """
    Consolidates episodic memories into semantic knowledge.
    
    Process:
    1. Batch episodes by goal type
    2. Extract patterns (what works, what fails)
    3. Generate semantic insights
    4. Store as reusable knowledge
    """

    def __init__(
        self,
        episodic_store: EpisodicMemory,
        semantic_store_path: str,
        api_key: Optional[str] = None,
    ):
        self.episodic = episodic_store
        self.semantic_path = semantic_store_path
        os.makedirs(semantic_store_path, exist_ok=True)
        self.api_key = api_key
        self.index_path = os.path.join(semantic_store_path, "knowledge_index.json")
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
            with open(self.index_path, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {"knowledge": [], "last_consolidation": None}

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def consolidate(self, min_episodes: int = 3) -> List[SemanticKnowledge]:
        """
        Run consolidation on recent episodes.
        Returns new knowledge generated.
        """
        # Get successful episodes
        successes = self.episodic.retrieve(
            EpisodeQuery(outcome="success", min_reward=0.5),
            k=20
        )

        # Get failed episodes
        failures = self.episodic.retrieve(
            EpisodeQuery(outcome="failure"),
            k=10
        )

        if len(successes) < min_episodes:
            return []  # Not enough data

        new_knowledge = []

        # Extract patterns from successes
        success_patterns = self._extract_patterns(successes)
        for pattern in success_patterns:
            knowledge = SemanticKnowledge(
                knowledge_id=f"k_{len(self.index['knowledge'])+1}",
                topic=pattern["topic"],
                insight=pattern["insight"],
                confidence=pattern["confidence"],
                source_episodes=pattern["sources"],
                timestamp=datetime.utcnow().isoformat(),
            )
            self._store_knowledge(knowledge)
            new_knowledge.append(knowledge)

        # Extract anti-patterns from failures
        failure_patterns = self._extract_anti_patterns(failures)
        for pattern in failure_patterns:
            knowledge = SemanticKnowledge(
                knowledge_id=f"k_{len(self.index['knowledge'])+1}",
                topic=f"avoid:{pattern['topic']}",
                insight=pattern["insight"],
                confidence=pattern["confidence"],
                source_episodes=pattern["sources"],
                timestamp=datetime.utcnow().isoformat(),
            )
            self._store_knowledge(knowledge)
            new_knowledge.append(knowledge)

        self.index["last_consolidation"] = datetime.utcnow().isoformat()
        self._save_index()

        return new_knowledge

    def _extract_patterns(self, episodes: List[Episode]) -> List[Dict[str, Any]]:
        """Extract success patterns from episodes."""
        patterns = []

        # Group by action sequences
        action_seqs = {}
        for ep in episodes:
            seq = tuple(a["action"] for a in ep.actions[:3])  # First 3 actions
            if seq not in action_seqs:
                action_seqs[seq] = []
            action_seqs[seq].append(ep)

        # Find common successful sequences
        for seq, eps in action_seqs.items():
            if len(eps) >= 2:  # At least 2 episodes with same pattern
                patterns.append({
                    "topic": f"successful_sequence:{'-'.join(seq)}",
                    "insight": f"Starting with {' → '.join(seq)} led to {len(eps)} successful outcomes",
                    "confidence": min(0.9, 0.3 + 0.2 * len(eps)),
                    "sources": [ep.episode_id for ep in eps],
                })

        # Collect lessons
        all_lessons = []
        for ep in episodes:
            for lesson in ep.lessons:
                all_lessons.append((lesson, ep.episode_id))

        # Aggregate similar lessons
        if all_lessons:
            patterns.append({
                "topic": "learned_lessons",
                "insight": "; ".join(set(lesson[0] for lesson in all_lessons[:5])),
                "confidence": 0.7,
                "sources": list(set(lesson[1] for lesson in all_lessons)),
            })

        return patterns

    def _extract_anti_patterns(self, episodes: List[Episode]) -> List[Dict[str, Any]]:
        """Extract failure patterns to avoid."""
        patterns = []

        # Find common failure actions
        failure_actions = {}
        for ep in episodes:
            for action in ep.actions:
                if not action.get("success", True):
                    name = action["action"]
                    if name not in failure_actions:
                        failure_actions[name] = []
                    failure_actions[name].append((ep.episode_id, action.get("error", "")))

        for action, failures in failure_actions.items():
            if len(failures) >= 2:
                errors = set(f[1][:50] for f in failures if f[1])
                patterns.append({
                    "topic": f"failure_prone:{action}",
                    "insight": f"{action} failed {len(failures)} times. Errors: {'; '.join(errors)}",
                    "confidence": min(0.8, 0.2 + 0.15 * len(failures)),
                    "sources": [f[0] for f in failures],
                })

        return patterns

    def _store_knowledge(self, knowledge: SemanticKnowledge):
        """Store knowledge item."""
        path = os.path.join(self.semantic_path, f"{knowledge.knowledge_id}.json")
        with open(path, "w") as f:
            json.dump({
                "knowledge_id": knowledge.knowledge_id,
                "topic": knowledge.topic,
                "insight": knowledge.insight,
                "confidence": knowledge.confidence,
                "source_episodes": knowledge.source_episodes,
                "timestamp": knowledge.timestamp,
            }, f, indent=2)

        self.index["knowledge"].append({
            "knowledge_id": knowledge.knowledge_id,
            "topic": knowledge.topic,
            "confidence": knowledge.confidence,
        })

    def query_knowledge(self, topic: str, k: int = 5) -> List[SemanticKnowledge]:
        """Query for relevant knowledge."""
        matches = []
        topic_lower = topic.lower()

        for entry in self.index["knowledge"]:
            entry_topic = entry.get("topic", "").lower()
            if topic_lower in entry_topic or any(w in entry_topic for w in topic_lower.split()):
                matches.append(entry)

        # Sort by confidence
        matches.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # Load full knowledge
        results = []
        for entry in matches[:k]:
            path = os.path.join(self.semantic_path, f"{entry['knowledge_id']}.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                results.append(SemanticKnowledge(**data))

        return results
