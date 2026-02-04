# tests/test_gate_determinism.py
from __future__ import annotations

import os
from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


def test_gate_is_deterministic():
    ws = os.path.abspath(os.getcwd())

    state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
        ),
    )

    d1 = gate(state, proposal)
    d2 = gate(state, proposal)

    assert d1 == d2
