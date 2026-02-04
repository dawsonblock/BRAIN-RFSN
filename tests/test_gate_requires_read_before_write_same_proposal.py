# tests/test_gate_requires_read_before_write_same_proposal.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


def test_gate_denies_write_without_read_same_proposal(tmp_path):
    ws = str(tmp_path)
    target = f"{ws}/a.txt"

    state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

    proposal = Proposal(
        proposal_id="p",
        actions=(
            Action(name="WRITE_FILE", args={"path": target, "content": "x"}),
            Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
        ),
    )

    d = gate(state, proposal)
    assert d.status == "DENY"
    assert "order:write_without_read_same_proposal" in d.reasons
