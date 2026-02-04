# upstream_learner/bandit.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict
import random


@dataclass
class BetaArm:
    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    def update(self, reward_01: float) -> None:
        r = max(0.0, min(1.0, float(reward_01)))
        self.alpha += r
        self.beta += (1.0 - r)


@dataclass
class ThompsonBandit:
    seed: int = 1337
    arms: Dict[str, BetaArm] = field(default_factory=dict)

    def ensure(self, arm_id: str) -> None:
        if arm_id not in self.arms:
            self.arms[arm_id] = BetaArm()

    def choose(self) -> str:
        if not self.arms:
            # default single arm
            self.ensure("default")
        rng = random.Random(self.seed)
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
        self.arms[arm_id].update(reward_01)

    def bump_seed(self) -> None:
        self.seed += 1
