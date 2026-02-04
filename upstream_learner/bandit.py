# upstream_learner/bandit.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import random


@dataclass
class BetaArm:
    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng: random.Random) -> float:
        # rng.betavariate is deterministic given seed
        return rng.betavariate(self.alpha, self.beta)

    def update(self, reward: float) -> None:
        # reward in [0,1]
        r = max(0.0, min(1.0, reward))
        self.alpha += r
        self.beta += (1.0 - r)


@dataclass
class ThompsonBandit:
    seed: int = 1337
    arms: Dict[str, BetaArm] = field(default_factory=dict)

    def ensure_arm(self, arm_id: str) -> None:
        if arm_id not in self.arms:
            self.arms[arm_id] = BetaArm()

    def choose(self, arm_ids: List[str], dopamine: float = 0.5) -> str:
        rng = random.Random(self.seed)
        best_id = arm_ids[0]
        best_val = -1.0
        
        # Adaptive Entropy: High dopamine increases exploration variance
        exploration_noise = max(0.0, dopamine - 0.5) * 0.2 # up to 0.1 jitter
        
        for arm_id in arm_ids:
            self.ensure_arm(arm_id)
            v = self.arms[arm_id].sample(rng)
            
            # Apply dopamine-scaled noise
            if exploration_noise > 0:
                v += rng.uniform(-exploration_noise, exploration_noise)
                v = max(0.0, min(1.0, v))

            if v > best_val:
                best_val = v
                best_id = arm_id
        # advance seed deterministically to avoid choosing same forever
        self.seed = (self.seed * 1103515245 + 12345) & 0x7FFFFFFF
        return best_id

    def update(self, arm_id: str, reward: float) -> None:
        self.ensure_arm(arm_id)
        self.arms[arm_id].update(reward)
