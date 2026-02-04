# rfsn_kernel/replay.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
from .ledger import iter_ledger_entries, compute_entry_hash
from .types import StateSnapshot, Proposal, Action
from .gate import gate


def verify_ledger_chain(ledger_path: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    prev_hash = "0" * 64
    expected_idx = 0

    for e in iter_ledger_entries(ledger_path):
        if e.idx != expected_idx:
            errors.append(f"bad_idx:got={e.idx}:expected={expected_idx}")
            break
        if e.prev_hash != prev_hash:
            errors.append(f"bad_prev_hash:idx={e.idx}")
            break
        h = compute_entry_hash(e.idx, e.prev_hash, e.payload)
        if h != e.entry_hash:
            errors.append(f"bad_entry_hash:idx={e.idx}")
            break
        prev_hash = e.entry_hash
        expected_idx += 1

    return (len(errors) == 0), errors


def verify_gate_determinism(ledger_path: str) -> Tuple[bool, List[str]]:
    """
    Re-run gate() from recorded state+proposal and compare to recorded decision.
    """
    errors: List[str] = []
    for e in iter_ledger_entries(ledger_path):
        payload = e.payload
        state = StateSnapshot(**payload["state"])
        proposal_obj = payload["proposal"]
        actions = tuple(Action(**a) for a in proposal_obj["actions"])
        proposal = Proposal(
            proposal_id=proposal_obj["proposal_id"],
            actions=actions,
            rationale=proposal_obj.get("rationale", ""),
            metadata=proposal_obj.get("metadata", {}),
        )
        recorded = payload["decision"]

        d = gate(state, proposal)

        # Compare minimal stable fields
        if d.status != recorded["status"]:
            errors.append(f"gate_mismatch_status:idx={e.idx}")
            continue
        if tuple(d.reasons) != tuple(recorded.get("reasons", [])):
            errors.append(f"gate_mismatch_reasons:idx={e.idx}")
            continue

        # approved_actions comparison (by name+args canonical)
        def key(a: Dict[str, Any]) -> str:
            return f'{a["name"]}|{sorted(a.get("args", {}).items())}'

        rec_approved = tuple(recorded.get("approved_actions", []))
        got_approved = tuple({"name": a.name, "args": a.args} for a in d.approved_actions)
        if tuple(map(key, rec_approved)) != tuple(map(key, got_approved)):
            errors.append(f"gate_mismatch_approved:idx={e.idx}")

    return (len(errors) == 0), errors
