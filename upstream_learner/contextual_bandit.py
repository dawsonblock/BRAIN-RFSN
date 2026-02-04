# upstream_learner/contextual_bandit.py
"""
Contextual Thompson Bandit for strategy selection.
Separate bandit per task context bucket for proper learning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import hashlib
import random
import json
import os


from memory.vector_store import get_vector_memory

def _bucketize_features(features: Dict[str, object], use_semantic: bool = False) -> str:
    """
    Turn a small dict of stable task features into a deterministic bucket key.
    If use_semantic is True, uses vector memory to find a neighbor.
    """
    if use_semantic:
        task_info = str(features.get("task_description", ""))
        repo_info = str(features.get("repo", ""))
        query = f"Task: {task_info} in Repo: {repo_info}"
        
        vector_memory = get_vector_memory()
        neighbors = vector_memory.retrieve(query, k=1)
        
        if neighbors and neighbors[0].relevance > 0.8:
            # Return the bucket ID of the closest match if stored in metadata
            match_bucket = neighbors[0].metadata.get("bucket_id")
            if match_bucket:
                return match_bucket

    # Fallback to coarse features
    keys = [
        ("repo", str(features.get("repo", ""))[:64]),
        ("lang", str(features.get("lang", "py"))[:8]),
        ("has_trace", "1" if features.get("has_trace") else "0"),
        ("test_kind", str(features.get("test_kind", "pytest"))[:16]),
        ("err_sig", str(features.get("err_sig", ""))[:64]),
    ]
    raw = "|".join([f"{k}={v}" for k, v in keys])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class BetaArm:
    """Thompson sampling arm with Beta distribution."""
    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    def update(self, reward01: float) -> None:
        r = max(0.0, min(1.0, reward01))
        self.alpha += r
        self.beta += (1.0 - r)

    def to_dict(self) -> Dict[str, float]:
        return {"alpha": self.alpha, "beta": self.beta}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "BetaArm":
        return cls(alpha=d.get("alpha", 1.0), beta=d.get("beta", 1.0))


@dataclass
class ContextualThompsonBandit:
    """
    Contextual = separate Thompson bandit per bucket.
    Deterministic given seed + same history.
    """
    seed: int = 1337
    buckets: Dict[str, Dict[str, BetaArm]] = field(default_factory=dict)

    def _rng(self) -> random.Random:
        return random.Random(self.seed)

    def _advance_seed(self) -> None:
        self.seed = (self.seed * 1103515245 + 12345) & 0x7FFFFFFF

    def ensure_arm(self, bucket: str, arm_id: str) -> None:
        if bucket not in self.buckets:
            self.buckets[bucket] = {}
        if arm_id not in self.buckets[bucket]:
            self.buckets[bucket][arm_id] = BetaArm()

    def choose(self, arm_ids: List[str], features: Dict[str, object], use_semantic: bool = True) -> Tuple[str, str]:
        """Choose best arm for given features. Returns (arm_id, bucket)."""
        bucket = _bucketize_features(features, use_semantic=use_semantic)
        rng = self._rng()

        # Cross-Context Weight Sharing:
        # If bucket is brand new, check if we can borrow from nearest neighbor
        if bucket not in self.buckets and use_semantic:
            vector_memory = get_vector_memory()
            task_query = str(features.get("task_description", ""))
            neighbors = vector_memory.retrieve(task_query, k=1)
            
            if neighbors and neighbors[0].relevance > 0.7:
                neighbor_bucket = neighbors[0].metadata.get("bucket_id")
                if neighbor_bucket and neighbor_bucket in self.buckets:
                    # Clone neighbor's experience to jumpstart learning
                    self.buckets[bucket] = {
                        aid: BetaArm(alpha=arm.alpha, beta=arm.beta) 
                        for aid, arm in self.buckets[neighbor_bucket].items()
                    }
        
        best_id = arm_ids[0]
        best_val = -1.0
        for arm_id in arm_ids:
            self.ensure_arm(bucket, arm_id)
            v = self.buckets[bucket][arm_id].sample(rng)
            if v > best_val:
                best_val = v
                best_id = arm_id

        self._advance_seed()

        # Persist this mapping in vector store for future semantic lookup
        if use_semantic:
            vector_memory = get_vector_memory()
            vector_memory.store(
                text=str(features.get("task_description", "")),
                metadata={"bucket_id": bucket, "repo": str(features.get("repo", ""))}
            )

        return best_id, bucket

    def update(self, bucket: str, arm_id: str, reward01: float, multiplier: float = 1.0) -> None:
        """Update arm with observed reward, optionally scaled by meta-cognitive importance."""
        self.ensure_arm(bucket, arm_id)
        # Apply multiplier to the weight of the update
        # High multiplier = higher learning rate for this specific result
        r = max(0.0, min(1.0, reward01))
        self.buckets[bucket][arm_id].alpha += (r * multiplier)
        self.buckets[bucket][arm_id].beta += ((1.0 - r) * multiplier)

    def save(self, path: str) -> None:
        """Save bandit state to file."""
        data = {
            "seed": self.seed,
            "buckets": {
                bucket: {arm_id: arm.to_dict() for arm_id, arm in arms.items()}
                for bucket, arms in self.buckets.items()
            },
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "ContextualThompsonBandit":
        """Load bandit state from file."""
        if not os.path.exists(path):
            return cls()

        with open(path, "r") as f:
            data = json.load(f)

        bandit = cls(seed=data.get("seed", 1337))
        for bucket, arms in data.get("buckets", {}).items():
            bandit.buckets[bucket] = {
                arm_id: BetaArm.from_dict(arm_data) for arm_id, arm_data in arms.items()
            }
        return bandit


# Strategy arms for SWE-bench
STRATEGY_ARMS = [
    "trace_then_patch",
    "read_tests_first",
    "patch_then_test",
    "multi_candidate_search",
    "llm_direct_fix",
]
