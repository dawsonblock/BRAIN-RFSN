# tests/test_candidate_loop.py
"""Tests for deterministic candidate-patch search loop."""
from __future__ import annotations

import pytest

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposers.candidate_loop import (
    candidate_loop_propose,
    check_exhausted,
    next_candidate_state,
    _hash_patch,
)
from rfsn_companion.strategies import build_strategy_registry


def test_candidate_loop_propose_first_candidate():
    """Should propose first candidate when index is 0."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["patch1", "patch2", "patch3"],
            "candidate_index": 0,
        },
    )
    proposal = candidate_loop_propose(state)

    assert len(proposal.actions) == 2
    assert proposal.actions[0].type == "APPLY_PATCH"
    assert proposal.actions[0].payload["patch"] == "patch1"
    assert proposal.actions[1].type == "RUN_TESTS"
    assert proposal.meta["candidate_index"] == 0
    assert proposal.meta["total_candidates"] == 3
    assert proposal.meta["has_patch"] is True
    assert "candidate_hash" in proposal.meta


def test_candidate_loop_propose_second_candidate():
    """Should propose second candidate when index is 1."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["patch1", "patch2", "patch3"],
            "candidate_index": 1,
        },
    )
    proposal = candidate_loop_propose(state)

    assert proposal.actions[0].payload["patch"] == "patch2"
    assert proposal.meta["candidate_index"] == 1


def test_candidate_loop_propose_no_candidates():
    """Should propose only tests when no candidates."""
    state = StateSnapshot(workspace="/tmp/ws", notes={})
    proposal = candidate_loop_propose(state)

    assert len(proposal.actions) == 1
    assert proposal.actions[0].type == "RUN_TESTS"
    assert proposal.meta["has_patch"] is False
    assert proposal.meta["exhausted"] is True


def test_candidate_loop_propose_exhausted():
    """Should propose only tests when index exceeds candidates."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["patch1", "patch2"],
            "candidate_index": 5,
        },
    )
    proposal = candidate_loop_propose(state)

    assert len(proposal.actions) == 1
    assert proposal.meta["exhausted"] is True


def test_check_exhausted():
    """check_exhausted should return True when all candidates tried."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["a", "b"],
            "candidate_index": 2,
        },
    )
    assert check_exhausted(state) is True

    state2 = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["a", "b"],
            "candidate_index": 1,
        },
    )
    assert check_exhausted(state2) is False


def test_next_candidate_state():
    """next_candidate_state should increment candidate_index."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["a", "b", "c"],
            "candidate_index": 1,
        },
    )
    new_state = next_candidate_state(state)

    assert new_state.notes["candidate_index"] == 2
    assert new_state.notes["patch_candidates"] == ["a", "b", "c"]
    assert new_state.workspace == "/tmp/ws"


def test_hash_patch_deterministic():
    """Patch hash should be deterministic."""
    patch = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
    h1 = _hash_patch(patch)
    h2 = _hash_patch(patch)
    assert h1 == h2
    assert len(h1) == 12  # short hash


def test_strategy_registry_includes_candidate_loop():
    """CandidatePatchLoop should be in strategy registry."""
    registry = build_strategy_registry()
    assert "candidate_patch_loop" in registry

    strat = registry["candidate_patch_loop"]
    assert strat.label == "Deterministic candidate-patch search loop"


def test_candidate_loop_via_strategy():
    """CandidatePatchLoop strategy should work end-to-end."""
    registry = build_strategy_registry()
    strat = registry["candidate_patch_loop"]

    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["fix1", "fix2"],
            "candidate_index": 0,
        },
    )
    proposal = strat.propose(state)

    assert proposal.actions[0].type == "APPLY_PATCH"
    assert proposal.meta["strategy"] == "candidate_patch_loop"


def test_custom_test_argv():
    """Should use custom test_argv from state.notes."""
    state = StateSnapshot(
        workspace="/tmp/ws",
        notes={
            "patch_candidates": ["patch1"],
            "candidate_index": 0,
            "test_argv": ["pytest", "-xvs", "tests/specific.py"],
        },
    )
    proposal = candidate_loop_propose(state)

    assert proposal.actions[1].payload["argv"] == ["pytest", "-xvs", "tests/specific.py"]
