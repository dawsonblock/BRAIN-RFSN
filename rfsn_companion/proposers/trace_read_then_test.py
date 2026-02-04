# rfsn_companion/proposers/trace_read_then_test.py
from __future__ import annotations

import os
import uuid
from typing import List

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_companion.selectors.traceback_selector import select_candidate_paths


def propose_trace_read_then_test(state: StateSnapshot) -> Proposal:
    ws = os.path.abspath(state.workspace_root)
    last_tests_path = os.path.join(ws, ".rfsn", "last_tests.txt")

    actions: List[Action] = []

    # 1) Read the last test output if it exists (safe: under workspace)
    actions.append(Action(name="READ_FILE", args={"path": last_tests_path}))

    # 2) Optionally read candidate files (deterministic selection from that output)
    # NOTE: We do not have the content at proposal time, so this step is "planned".
    # The kernel will execute READ_FILE for last_tests.txt first; a later improvement is to do two-step episodes.
    #
    # For now, we support a "manual mode": if state.notes includes "last_tests_text",
    # we can pick candidates deterministically right now.
    last_tests_text = state.notes.get("last_tests_text", "")
    if isinstance(last_tests_text, str) and last_tests_text:
        cands = select_candidate_paths(last_tests_text, ws, k=int(state.notes.get("trace_k", 3)))
        for p in cands:
            actions.append(Action(name="READ_FILE", args={"path": p}))

        # Optional patch only if explicitly provided AND is among candidates
        patch_path = state.notes.get("patch_path")
        patch_content = state.notes.get("patch_content")
        if isinstance(patch_path, str) and patch_path and isinstance(patch_content, str) and patch_content:
            ap = os.path.abspath(patch_path)
            if ap in set(cands):
                # enforce read-before-write (same proposal) already satisfied if ap in cands
                actions.append(Action(name="APPLY_PATCH", args={"path": ap, "content": patch_content}))

    # 3) Always run tests last
    actions.append(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}))

    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=tuple(actions),
        rationale="trace_read_then_test: read last test output; read top candidate files; run tests",
        metadata={"variant": "v4_trace_read"},
    )
