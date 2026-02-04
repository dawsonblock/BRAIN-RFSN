# tests/test_order_rule_requires_tests_after_write.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


def test_missing_tests_after_write_is_denied(tmp_path):
    ws = str(tmp_path)
    state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

    proposal = Proposal(
        proposal_id="p",
        actions=(
            Action(name="WRITE_FILE", args={"path": f"{ws}/a.txt", "content": "x"}),
        ),
    )

    d = gate(state, proposal)
    assert d.status == "DENY"
    assert "order:missing_run_tests_after_write" in d.reasons
