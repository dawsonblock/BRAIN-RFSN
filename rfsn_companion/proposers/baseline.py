# rfsn_companion/proposers/baseline.py
from __future__ import annotations

import uuid
from rfsn_kernel.types import StateSnapshot, Proposal, Action


def propose_baseline(state: StateSnapshot) -> Proposal:
    actions = (
        Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
    )
    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=actions,
        rationale="Baseline: run tests for failing signal.",
        metadata={"variant": "v0_minimal"},
    )
