# upstream_learner/policy_store.py
from __future__ import annotations

import json
import os

from .bandit import ThompsonBandit, BetaArm


def save_bandit(path: str, bandit: ThompsonBandit) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    obj = {
        "seed": bandit.seed,
        "arms": {k: {"alpha": v.alpha, "beta": v.beta} for k, v in bandit.arms.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_bandit(path: str, default_seed: int = 1337) -> ThompsonBandit:
    if not os.path.exists(path):
        return ThompsonBandit(seed=default_seed)

    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    b = ThompsonBandit(seed=int(obj.get("seed", default_seed)))
    arms = obj.get("arms", {})
    for k, v in arms.items():
        b.arms[str(k)] = BetaArm(alpha=float(v["alpha"]), beta=float(v["beta"]))
    return b
