from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import os


@dataclass
class Episode:
    """A single episode of agent experience."""
    episode_id: str
    timestamp: str
    goal: str
    actions: List[Dict[str, Any]]
    outcome: str
    reward: float
    lessons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    emotion_profile: Dict[str, float] = field(default_factory=dict)


@dataclass
class EpisodeQuery:
    """Query for finding similar episodes."""
    goal: Optional[str] = None
    outcome: Optional[str] = None
    action_type: Optional[str] = None
    min_reward: float = 0.0


class EpisodicMemory:
    """
    Stores and retrieves task execution episodes.
    Enables learning from past experiences.
    """

    def __init__(self, store_path: str):
        self.store_path = store_path
        os.makedirs(store_path, exist_ok=True)
        self.index_path = os.path.join(store_path, "episodes_index.json")
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
            with open(self.index_path, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {"episodes": [], "stats": {"total": 0, "successes": 0, "failures": 0}}

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def store(self, episode: Episode) -> str:
        """Store an episode and return its ID."""
        # Ensure directory exists (in case it was deleted externally)
        os.makedirs(self.store_path, exist_ok=True)
        # Save episode file
        episode_path = os.path.join(self.store_path, f"{episode.episode_id}.json")
        with open(episode_path, "w") as f:
            json.dump({
                "episode_id": episode.episode_id,
                "timestamp": episode.timestamp,
                "goal": episode.goal,
                "actions": episode.actions,
                "outcome": episode.outcome,
                "reward": episode.reward,
                "lessons": episode.lessons,
                "metadata": episode.metadata,
                "emotion_profile": episode.emotion_profile,
            }, f, indent=2)

        # Update index
        self.index["episodes"].append({
            "episode_id": episode.episode_id,
            "goal_preview": episode.goal[:100],
            "outcome": episode.outcome,
            "reward": episode.reward,
            "timestamp": episode.timestamp,
            "action_count": len(episode.actions),
        })
        self.index["stats"]["total"] += 1
        if episode.outcome == "success":
            self.index["stats"]["successes"] += 1
        elif episode.outcome == "failure":
            self.index["stats"]["failures"] += 1
        self._save_index()

        return episode.episode_id

    def retrieve(self, query: EpisodeQuery, k: int = 5) -> List[Episode]:
        """Retrieve episodes matching the query."""
        matches = []

        for entry in self.index["episodes"]:
            # Filter by outcome
            if query.outcome and entry.get("outcome") != query.outcome:
                continue
            # Filter by min reward
            if entry.get("reward", 0) < query.min_reward:
                continue

            matches.append(entry)

        # Sort by reward (highest first) and recency
        matches.sort(key=lambda x: (x.get("reward", 0), x.get("timestamp", "")), reverse=True)

        # Load full episodes
        episodes = []
        for entry in matches[:k]:
            episode = self._load_episode(entry["episode_id"])
            if episode:
                episodes.append(episode)

        return episodes

    def _load_episode(self, episode_id: str) -> Optional[Episode]:
        episode_path = os.path.join(self.store_path, f"{episode_id}.json")
        if not os.path.exists(episode_path):
            return None

        with open(episode_path, "r") as f:
            data = json.load(f)

        return Episode(
            episode_id=data["episode_id"],
            timestamp=data["timestamp"],
            goal=data["goal"],
            actions=data["actions"],
            outcome=data["outcome"],
            reward=data["reward"],
            lessons=data.get("lessons", []),
            metadata=data.get("metadata", {}),
            emotion_profile=data.get("emotion_profile", {})
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.index.get("stats", {})

    def get_lessons_for_goal(self, goal: str, k: int = 3) -> List[str]:
        """Get lessons learned from similar past goals."""
        all_lessons = []

        for entry in self.index["episodes"]:
            # Simple keyword matching for now
            goal_lower = goal.lower()
            preview_lower = entry.get("goal_preview", "").lower()

            # Check for word overlap
            goal_words = set(goal_lower.split())
            preview_words = set(preview_lower.split())
            overlap = goal_words & preview_words

            if len(overlap) >= 2 or entry.get("outcome") == "success":
                episode = self._load_episode(entry["episode_id"])
                if episode and episode.lessons:
                    all_lessons.extend(episode.lessons)

        return all_lessons[:k]


# Singleton instance
_episodic_memory: Optional[EpisodicMemory] = None

def get_episodic_memory(store_path: str = "rfsn_memory_store/episodes") -> EpisodicMemory:
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory(store_path)
    return _episodic_memory
