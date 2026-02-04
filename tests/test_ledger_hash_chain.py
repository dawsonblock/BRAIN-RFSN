# tests/test_ledger_hash_chain.py
from __future__ import annotations

import os
from rfsn_kernel.types import StateSnapshot, Proposal, Action, Decision, ExecResult
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.replay import verify_ledger_chain


def test_ledger_hash_chain_ok(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ws = os.path.abspath(os.getcwd())

    state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
    proposal = Proposal(proposal_id="p", actions=(Action(name="RUN_TESTS", args={"argv": ["echo", "ok"]}),))
    decision = Decision(status="ALLOW", approved_actions=proposal.actions)

    results = (ExecResult(action=proposal.actions[0], ok=True, stdout="ok\n", stderr="", exit_code=0, duration_ms=1),)

    append_ledger(str(ledger), state, proposal, decision, results, meta={"k": "v"})
    append_ledger(str(ledger), state, proposal, decision, results, meta={"k": "v2"})

    ok, errs = verify_ledger_chain(str(ledger))
    assert ok, errs
