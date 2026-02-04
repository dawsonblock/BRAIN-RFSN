# rfsn_companion/proposers/brain_wrap.py
from __future__ import annotations

import uuid
from typing import List

from rfsn_kernel.types import StateSnapshot, Proposal, Action


def propose_brain(state: StateSnapshot) -> Proposal:
    """
    Safe wrapper:
    - proposal-only
    - no execution
    - no invented targets
    - read-before-write inside the same proposal
    """
    actions: List[Action] = []
    rationale_parts: List[str] = []

    read_path = state.notes.get("read_path")
    patch_path = state.notes.get("patch_path")
    patch_content = state.notes.get("patch_content")

    # If caller supplies a read target, read it.
    if isinstance(read_path, str) and read_path:
        actions.append(Action(name="READ_FILE", args={"path": read_path}))
        rationale_parts.append(f"read:{read_path}")

    # If caller supplies a patch, enforce read-before-write by adding READ_FILE first (if not already).
    if isinstance(patch_path, str) and patch_path and isinstance(patch_content, str) and patch_content:
        if not (isinstance(read_path, str) and read_path and read_path == patch_path):
            actions.append(Action(name="READ_FILE", args={"path": patch_path}))
            rationale_parts.append(f"read_before_patch:{patch_path}")

        actions.append(Action(name="APPLY_PATCH", args={"path": patch_path, "content": patch_content}))
        rationale_parts.append(f"patch:{patch_path}")

    # Always end with tests for any meaningful action set.
    actions.append(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}))
    rationale_parts.append("run_tests")

    # If nothing but tests was possible, still valid.
    rationale = "; ".join(rationale_parts) if rationale_parts else "run_tests"

    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=tuple(actions),
        rationale=rationale,
        metadata={"variant": "v3_brain"},
    )
