# tests/test_envelope_blocks_out_of_bounds_path.py
from __future__ import annotations

import os
from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


def test_gate_denies_out_of_bounds_paths(tmp_path):
    ws = str(tmp_path)

    # attempt to write outside workspace
    outside = os.path.abspath(os.path.join(ws, "..", "pwned.txt"))

    state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
    proposal = Proposal(
        proposal_id="p",
        actions=(
            Action(name="WRITE_FILE", args={"path": outside, "content": "nope"}),
            Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
        ),
    )

    d = gate(state, proposal)
    assert d.status == "DENY"
    assert any("path_out_of_bounds" in r for r in d.reasons)
