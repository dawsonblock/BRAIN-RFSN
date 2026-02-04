# rfsn_companion/proposer.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal
from .proposer_variants import select_proposer


def propose(state: StateSnapshot) -> Proposal:
    variant = str(state.notes.get("prompt_variant", "v0_minimal"))
    fn = select_proposer(variant)
    return fn(state)
