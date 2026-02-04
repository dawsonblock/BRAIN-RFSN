# tests/test_replay_detects_tamper.py
from __future__ import annotations

import json
from rfsn_kernel.types import StateSnapshot, Proposal, Action, Decision, ExecResult
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.replay import verify_ledger_chain


def test_replay_detects_tamper(tmp_path):
    ledger = tmp_path / "ledger.jsonl"

    state = StateSnapshot(task_id="t", workspace_root=str(tmp_path), step=0)
    proposal = Proposal(proposal_id="p", actions=(Action(name="RUN_TESTS", args={"argv": ["echo", "ok"]}),))
    decision = Decision(status="ALLOW", approved_actions=proposal.actions)
    results = (ExecResult(action=proposal.actions[0], ok=True, stdout="ok\n", stderr="", exit_code=0, duration_ms=1),)

    append_ledger(str(ledger), state, proposal, decision, results)

    # tamper with first line payload
    lines = ledger.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[0])
    obj["payload"]["meta"] = {"tampered": True}
    lines[0] = json.dumps(obj)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, errs = verify_ledger_chain(str(ledger))
    assert not ok
    assert errs
