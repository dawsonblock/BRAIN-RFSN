# rfsn_companion/proposer.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal
from .proposers.deterministic_stub import propose_deterministic


def propose(state: StateSnapshot) -> Proposal:
    """
    Companion layer chooses *how* to propose.
    This minimal build is deterministic, so kernel/replay tests are stable.
    Swap propose_deterministic() with an LLM-backed proposer later.
    """
    return propose_deterministic(state)
