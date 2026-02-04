# upstream_learner/bandit.py
"""
Thompson Sampling Bandit with:
- Persistence (save/load to JSON)
- Exponential decay (older observations count less)
- Arm statistics (pulls, mean reward, UCB)
- Warm-start from outcomes DB
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import json
import math
import os
import random


@dataclass
class BetaArm:
    alpha: float = 1.0
    beta: float = 1.0
    pulls: int = 0
    total_reward: float = 0.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    def update(self, reward_01: float, decay: float = 1.0) -> None:
        """Update arm with reward. decay < 1 shrinks prior before adding new observation."""
        r = max(0.0, min(1.0, float(reward_01)))
        # Apply decay to existing counts
        self.alpha = 1.0 + (self.alpha - 1.0) * decay
        self.beta = 1.0 + (self.beta - 1.0) * decay
        # Add new observation
        self.alpha += r
        self.beta += (1.0 - r)
        self.pulls += 1
        self.total_reward += r

    @property
    def mean(self) -> float:
        """Expected value of the Beta distribution."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Variance of the Beta distribution."""
        total = self.alpha + self.beta
        return (self.alpha * self.beta) / (total * total * (total + 1))

    def ucb(self, total_pulls: int, c: float = 2.0) -> float:
        """Upper confidence bound for exploration bonus."""
        if self.pulls == 0 or total_pulls == 0:
            return float('inf')
        return self.mean + c * math.sqrt(math.log(total_pulls) / self.pulls)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BetaArm":
        return cls(
            alpha=float(d.get("alpha", 1.0)),
            beta=float(d.get("beta", 1.0)),
            pulls=int(d.get("pulls", 0)),
            total_reward=float(d.get("total_reward", 0.0)),
        )


@dataclass
class ThompsonBandit:
    seed: int = 1337
    decay: float = 1.0  # 1.0 = no decay, 0.99 = slight decay
    arms: Dict[str, BetaArm] = field(default_factory=dict)

    def ensure(self, arm_id: str) -> None:
        if arm_id not in self.arms:
            self.arms[arm_id] = BetaArm()

    @property
    def total_pulls(self) -> int:
        return sum(a.pulls for a in self.arms.values())

    def choose(self, method: str = "thompson") -> str:
        """
        Choose an arm using specified method:
        - 'thompson': Thompson sampling (default)
        - 'ucb': Upper Confidence Bound
        - 'greedy': Pure exploitation (highest mean)
        - 'random': Uniform random
        """
        if not self.arms:
            self.ensure("default")

        rng = random.Random(self.seed)

        if method == "random":
            return rng.choice(list(self.arms.keys()))

        if method == "greedy":
            return max(self.arms.keys(), key=lambda k: self.arms[k].mean)

        if method == "ucb":
            total = self.total_pulls
            return max(self.arms.keys(), key=lambda k: self.arms[k].ucb(total))

        # Default: Thompson sampling
        best_id = None
        best_val = -1.0
        for arm_id, arm in self.arms.items():
            v = arm.sample(rng)
            if v > best_val:
                best_val = v
                best_id = arm_id
        return str(best_id)

    def update(self, arm_id: str, reward_01: float) -> None:
        self.ensure(arm_id)
        self.arms[arm_id].update(reward_01, decay=self.decay)

    def bump_seed(self) -> None:
        self.seed += 1

    # === Statistics ===

    def arm_stats(self) -> List[Dict[str, Any]]:
        """Return sorted list of arm statistics (best first by mean)."""
        stats = []
        for arm_id, arm in self.arms.items():
            stats.append({
                "arm_id": arm_id,
                "pulls": arm.pulls,
                "mean": round(arm.mean, 4),
                "total_reward": round(arm.total_reward, 2),
                "alpha": round(arm.alpha, 2),
                "beta": round(arm.beta, 2),
                "ucb": round(arm.ucb(self.total_pulls), 4) if arm.pulls > 0 else None,
            })
        return sorted(stats, key=lambda x: x["mean"], reverse=True)

    def best_arm(self) -> Optional[str]:
        """Return arm_id with highest mean reward."""
        if not self.arms:
            return None
        return max(self.arms.keys(), key=lambda k: self.arms[k].mean)

    # === Persistence ===

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "decay": self.decay,
            "arms": {k: v.to_dict() for k, v in self.arms.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ThompsonBandit":
        bandit = cls(
            seed=int(d.get("seed", 1337)),
            decay=float(d.get("decay", 1.0)),
        )
        for arm_id, arm_data in d.get("arms", {}).items():
            bandit.arms[arm_id] = BetaArm.from_dict(arm_data)
        return bandit

    def save(self, path: str) -> None:
        """Save bandit state to JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "ThompsonBandit":
        """Load bandit state from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def load_or_create(cls, path: str, seed: int = 1337, decay: float = 1.0) -> "ThompsonBandit":
        """Load if exists, otherwise create new."""
        if os.path.exists(path):
            return cls.load(path)
        return cls(seed=seed, decay=decay)


def warm_start_from_outcomes(
    bandit: ThompsonBandit,
    db_path: str,
    max_rows: int = 1000,
) -> int:
    """
    Initialize bandit arms from historical outcomes.
    Returns number of rows processed.
    """
    import sqlite3

    if not os.path.exists(db_path):
        return 0

    count = 0
    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT arm_id, reward FROM outcomes ORDER BY ts DESC LIMIT ?",
            (max_rows,),
        ).fetchall()

        # Process in chronological order (oldest first)
        for row in reversed(rows):
            arm_id = row["arm_id"]
            reward = float(row["reward"])
            bandit.ensure(arm_id)
            bandit.arms[arm_id].update(reward, decay=bandit.decay)
            count += 1

    return count
