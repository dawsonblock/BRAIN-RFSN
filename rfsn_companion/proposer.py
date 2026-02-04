# rfsn_companion/proposer.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal
from .strategies import build_strategy_registry


_REGISTRY = build_strategy_registry()


def propose(state: StateSnapshot) -> Proposal:
    """
    Select a proposal strategy based on state.notes["arm_id"].
    Falls back deterministically to run_tests_only.
    """
    arm_id = state.notes.get("arm_id")
    if not isinstance(arm_id, str) or arm_id not in _REGISTRY:
        arm_id = "run_tests_only"
    return _REGISTRY[arm_id].propose(state)
