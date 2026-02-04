# rfsn_kernel/replay.py
from __future__ import annotations

import json
import os

from .types import StateSnapshot, Proposal, canonical_json, sha256_hex
from .gate import gate


def verify_ledger_chain(ledger_path: str) -> None:
    if not os.path.exists(ledger_path):
        raise RuntimeError(f"ledger missing: {ledger_path}")

    prev = "0" * 64
    with open(ledger_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            if rec["idx"] != i:
                raise RuntimeError(f"bad idx at line {i}: {rec['idx']}")
            if rec["prev_hash"] != prev:
                raise RuntimeError(f"bad prev_hash at idx {i}")
            body = {"idx": rec["idx"], "prev_hash": rec["prev_hash"], "payload": rec["payload"]}
            expect = sha256_hex(canonical_json(body))
            if rec["entry_hash"] != expect:
                raise RuntimeError(f"bad hash at idx {i}")
            prev = rec["entry_hash"]


def verify_gate_determinism(state: StateSnapshot, proposal: Proposal, trials: int = 10) -> None:
    d0 = gate(state, proposal)
    for _ in range(trials - 1):
        d = gate(state, proposal)
        if d != d0:
            raise RuntimeError("gate is non-deterministic for same inputs")
