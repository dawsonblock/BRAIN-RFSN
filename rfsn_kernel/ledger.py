# rfsn_kernel/ledger.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import os
import json

from .types import StateSnapshot, Proposal, Decision, ExecResult, canonical_json, sha256_hex, dataclass_to_dict


@dataclass(frozen=True)
class LedgerEntry:
    idx: int
    prev_hash: str
    entry_hash: str
    payload: Dict[str, Any]


def _entry_payload(
    state: StateSnapshot,
    proposal: Proposal,
    decision: Decision,
    results: Tuple[ExecResult, ...],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "state": dataclass_to_dict(state),
        "proposal": dataclass_to_dict(proposal),
        "decision": dataclass_to_dict(decision),
        "results": dataclass_to_dict(results),
        "meta": meta or {},
    }


def append_ledger(
    ledger_path: str,
    *,
    state: StateSnapshot,
    proposal: Proposal,
    decision: Decision,
    results: Tuple[ExecResult, ...],
    meta: Optional[Dict[str, Any]] = None,
) -> LedgerEntry:
    os.makedirs(os.path.dirname(os.path.abspath(ledger_path)), exist_ok=True)

    prev_hash = "0" * 64
    idx = 0

    if os.path.exists(ledger_path):
        with open(ledger_path, "rb") as f:
            lines = f.read().splitlines()
        if lines:
            last = json.loads(lines[-1].decode("utf-8"))
            prev_hash = str(last["entry_hash"])
            idx = int(last["idx"]) + 1

    payload = _entry_payload(state, proposal, decision, results, meta)
    body = {"idx": idx, "prev_hash": prev_hash, "payload": payload}
    entry_hash = sha256_hex(canonical_json(body))
    rec = {"idx": idx, "prev_hash": prev_hash, "entry_hash": entry_hash, "payload": payload}

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return LedgerEntry(idx=idx, prev_hash=prev_hash, entry_hash=entry_hash, payload=payload)
