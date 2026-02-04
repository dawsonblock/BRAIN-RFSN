# upstream_learner/features.py
from __future__ import annotations


def reward_from_episode(decision_status: str, tests_passed: bool, wall_ms: int) -> float:
    """
    Simple bounded reward:
    - deny => 0
    - allow + tests fail => 0.2
    - allow + tests pass => 1.0
    - time penalty mild
    """
    if decision_status != "ALLOW":
        return 0.0
    base = 1.0 if tests_passed else 0.2
    penalty = min(0.5, wall_ms / 600_000.0)  # up to -0.5 at 10 min
    return max(0.0, min(1.0, base - penalty))
