# rfsn_companion/proposers/read_patch_test.py
from __future__ import annotations

import uuid
from rfsn_kernel.types import StateSnapshot, Proposal, Action


def propose_read_patch_test(state: StateSnapshot) -> Proposal:
    target = state.notes.get("patch_path", f"{state.workspace_root}/example.txt")
    content = state.notes.get("patch_content", "example\n")

    actions = (
        Action(name="READ_FILE", args={"path": target}),
        Action(name="APPLY_PATCH", args={"path": target, "content": content}),
        Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
    )
    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=actions,
        rationale="Read then apply a minimal patch, then run tests.",
        metadata={"variant": "v1_patch_then_test", "patch_path": target},
    )
