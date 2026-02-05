# rfsn_companion/proposers/candidate_loop.py
"""
Deterministic Candidate-Patch Search Loop

Enables reproducible patch generation by iterating through patch candidates
in a deterministic, seeded order. The loop:

1. Reads patch candidates from state.notes["patch_candidates"] (list of str)
2. Uses state.notes["candidate_index"] to track current position (default 0)
3. Proposes: apply candidate[index], run tests
4. Caller increments index and re-runs until success or exhaustion

Usage:
    state.notes = {
        "patch_candidates": [patch1, patch2, patch3],
        "candidate_index": 0,  # optional, defaults to 0
        "test_argv": ["pytest", "-q"],  # optional
    }
    proposal = candidate_loop_propose(state)

The proposal meta contains:
    - candidate_index: which candidate was selected
    - total_candidates: how many candidates exist
    - candidate_hash: hash of the selected patch for reproducibility
"""
from __future__ import annotations

import hashlib
from typing import List, Optional

from rfsn_kernel.types import Action, Proposal, StateSnapshot


def _hash_patch(patch: str) -> str:
    """Return short sha256 hash of patch for reproducibility tracking."""
    return hashlib.sha256(patch.encode("utf-8")).hexdigest()[:12]


def _get_patch_candidates(state: StateSnapshot) -> List[str]:
    """Extract patch candidates from state.notes."""
    candidates = state.notes.get("patch_candidates")
    if not isinstance(candidates, list):
        return []
    return [c for c in candidates if isinstance(c, str) and c.strip()]


def _get_candidate_index(state: StateSnapshot) -> int:
    """Extract current candidate index from state.notes (default 0)."""
    idx = state.notes.get("candidate_index", 0)
    if isinstance(idx, int) and idx >= 0:
        return idx
    return 0


def _get_test_argv(state: StateSnapshot) -> List[str]:
    """Extract test command from state.notes or use default."""
    argv = state.notes.get("test_argv")
    if isinstance(argv, list) and all(isinstance(x, str) for x in argv):
        return argv
    return ["pytest", "-q"]


def candidate_loop_propose(state: StateSnapshot) -> Proposal:
    """
    Propose applying the current candidate patch and running tests.

    If no candidates or index out of range, proposes only running tests
    (which will likely fail, signaling exhaustion to the caller).
    """
    candidates = _get_patch_candidates(state)
    index = _get_candidate_index(state)
    test_argv = _get_test_argv(state)

    actions: List[Action] = []
    meta = {
        "proposer": "candidate_loop",
        "candidate_index": index,
        "total_candidates": len(candidates),
    }

    if candidates and 0 <= index < len(candidates):
        patch = candidates[index]
        meta["candidate_hash"] = _hash_patch(patch)
        meta["has_patch"] = True
        actions.append(Action("APPLY_PATCH", {"patch": patch}))
    else:
        meta["has_patch"] = False
        meta["exhausted"] = index >= len(candidates) if candidates else True

    actions.append(Action("RUN_TESTS", {"argv": test_argv}))

    return Proposal(actions=tuple(actions), meta=meta)


def check_exhausted(state: StateSnapshot) -> bool:
    """Check if all candidates have been tried."""
    candidates = _get_patch_candidates(state)
    index = _get_candidate_index(state)
    return index >= len(candidates)


def next_candidate_state(state: StateSnapshot) -> StateSnapshot:
    """
    Return a new StateSnapshot with candidate_index incremented.

    This is a pure function for use in deterministic loops.
    """
    new_notes = dict(state.notes)
    current_index = _get_candidate_index(state)
    new_notes["candidate_index"] = current_index + 1
    return StateSnapshot(workspace=state.workspace, notes=new_notes)
