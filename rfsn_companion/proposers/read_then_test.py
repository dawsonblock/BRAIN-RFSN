# rfsn_companion/proposers/read_then_test.py
from __future__ import annotations

import uuid
from rfsn_kernel.types import StateSnapshot, Proposal, Action


def propose_read_then_test(state: StateSnapshot) -> Proposal:
    target = state.notes.get("read_path", None)
    if not target:
        # default: you can set this from the episode runner later
        target = f"{state.workspace_root}/README.md"

    actions = (
        Action(name="READ_FILE", args={"path": target}),
        Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
    )
    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=actions,
        rationale="Read a target file for context, then run tests.",
        metadata={"variant": "v2_read_then_plan", "read_path": target},
    )
