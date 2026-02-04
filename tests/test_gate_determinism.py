# tests/test_gate_determinism.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


def test_gate_is_deterministic_for_same_inputs(tmp_path):
    ws = tmp_path
    (ws / "x.txt").write_text("hi", encoding="utf-8")

    state = StateSnapshot(workspace=str(ws), notes={})
    proposal = Proposal(
        actions=(
            Action("READ_FILE", {"path": "x.txt"}),
            Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
        ),
        meta={},
    )

    d0 = gate(state, proposal)
    for _ in range(20):
        assert gate(state, proposal) == d0
