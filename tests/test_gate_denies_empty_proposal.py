# tests/test_gate_denies_empty_proposal.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal
from rfsn_kernel.gate import gate


def test_gate_denies_empty_proposal(tmp_path):
    state = StateSnapshot(task_id="t", workspace_root=str(tmp_path), step=0)
    proposal = Proposal(proposal_id="p", actions=())
    d = gate(state, proposal)
    assert d.status == "DENY"
    assert "empty_proposal" in d.reasons
