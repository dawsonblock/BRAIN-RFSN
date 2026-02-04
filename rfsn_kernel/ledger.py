# rfsn_kernel/ledger.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple
import os
import json

from .types import (
    StateSnapshot,
    Proposal,
    Decision,
    ExecResult,
    canonical_json,
    sha256_hex,
    dataclass_to_dict,
)


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
        "results": [dataclass_to_dict(r) for r in results],
        "meta": meta or {},
    }


def append_ledger(
    ledger_path: str,
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
        last = None
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = json.loads(line)
        if last is not None:
            prev_hash = last["entry_hash"]
            idx = int(last["idx"]) + 1

    payload = _entry_payload(state, proposal, decision, results, meta=meta)
    blob = canonical_json({"idx": idx, "prev_hash": prev_hash, "payload": payload})
    entry_hash = sha256_hex(blob)

    entry = {
        "idx": idx,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "payload": payload,
    }

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return LedgerEntry(idx=idx, prev_hash=prev_hash, entry_hash=entry_hash, payload=payload)


def iter_ledger_entries(ledger_path: str) -> Iterable[LedgerEntry]:
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            yield LedgerEntry(
                idx=int(obj["idx"]),
                prev_hash=str(obj["prev_hash"]),
                entry_hash=str(obj["entry_hash"]),
                payload=obj["payload"],
            )


def compute_entry_hash(idx: int, prev_hash: str, payload: Dict[str, Any]) -> str:
    blob = canonical_json({"idx": idx, "prev_hash": prev_hash, "payload": payload})
    return sha256_hex(blob)
