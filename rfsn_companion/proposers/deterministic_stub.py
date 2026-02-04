# rfsn_companion/proposers/deterministic_stub.py
from __future__ import annotations

from rfsn_kernel.types import Proposal, Action, StateSnapshot


def propose_deterministic(state: StateSnapshot) -> Proposal:
    """
    Deterministic placeholder:
    - run allowlisted tests
    This makes the whole pipeline runnable without any external model.
    """
    actions = (
        Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
    )
    return Proposal(actions=actions, meta={"proposer": "deterministic_stub"})
