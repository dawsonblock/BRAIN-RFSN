# tests/test_kernel_determinism.py
from __future__ import annotations

import os
import json
import tempfile

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.replay import verify_ledger_chain


def test_gate_determinism():
    """Same input => same decision."""
    state = StateSnapshot(task_id="t", workspace_root="/tmp/ws", step=0)
    proposal = Proposal(
        proposal_id="p1",
        actions=(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest"]}),),
    )
    
    d1 = gate(state, proposal)
    d2 = gate(state, proposal)
    
    assert d1.status == d2.status
    assert d1.reasons == d2.reasons
    assert d1.approved_actions == d2.approved_actions


def test_ledger_chain_integrity():
    """One tamper breaks chain verification."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    
    try:
        state = StateSnapshot(task_id="t", workspace_root="/tmp/ws", step=0)
        proposal = Proposal(
            proposal_id="p1",
            actions=(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest"]}),),
        )
        decision = gate(state, proposal)
        
        # Append two entries
        append_ledger(ledger_path, state, proposal, decision, results=())
        append_ledger(ledger_path, state, proposal, decision, results=())
        
        # Verify intact chain
        ok, errs = verify_ledger_chain(ledger_path)
        assert ok, f"Chain should be valid: {errs}"
        
        # Tamper with the file
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Modify second entry's hash
        obj = json.loads(lines[1])
        obj["entry_hash"] = "aaaa" + obj["entry_hash"][4:]
        lines[1] = json.dumps(obj) + "\n"
        
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        # Verify tampered chain fails
        ok, errs = verify_ledger_chain(ledger_path)
        assert not ok, "Tampered chain should fail verification"
        assert "bad_entry_hash" in errs[0]
        
    finally:
        os.unlink(ledger_path)


def test_envelope_enforcement():
    """Forbidden path edits denied."""
    state = StateSnapshot(task_id="t", workspace_root="/tmp/ws", step=0)
    
    # Path outside workspace
    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="WRITE_FILE", args={"path": "/etc/passwd", "content": "hacked"}),
            Action(name="RUN_TESTS", args={"argv": ["pytest"]}),
        ),
    )
    
    d = gate(state, proposal)
    assert d.status == "DENY"
    assert any("path_out_of_bounds" in r for r in d.reasons)
