# tests/test_strategies_generate_proposals.py
from __future__ import annotations

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.strategies import build_strategy_registry


def test_all_strategies_produce_nonempty_proposals(tmp_path):
    ws = tmp_path
    ws.mkdir(exist_ok=True)

    reg = build_strategy_registry()

    for arm_id, strat in reg.items():
        state = StateSnapshot(
            workspace=str(ws),
            notes={
                "arm_id": arm_id,
                "focus_paths": ["README.md", "pyproject.toml"],
                "patch_text": "diff --git a/x.txt b/x.txt\n--- a/x.txt\n+++ b/x.txt\n@@ -0,0 +1 @@\n+hi\n",
                "note_text": "marker\n",
            },
        )
        proposal = strat.propose(state)
        assert proposal.actions, f"{arm_id} produced empty actions"
