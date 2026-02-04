# tests/test_ledger_chain.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.replay import verify_ledger_chain


def test_ledger_hash_chain_verifies(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "a.txt").write_text("a", encoding="utf-8")

    state = StateSnapshot(workspace=str(ws), notes={})
    proposal = Proposal(actions=(Action("READ_FILE", {"path": "a.txt"}),), meta={})
    decision = gate(state, proposal)

    append_ledger(str(ledger), state=state, proposal=proposal, decision=decision, results=(), meta={"k": 1})
    append_ledger(str(ledger), state=state, proposal=proposal, decision=decision, results=(), meta={"k": 2})

    verify_ledger_chain(str(ledger))
