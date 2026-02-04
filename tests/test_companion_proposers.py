# tests/test_companion_proposers.py
"""Tests for companion proposer variants."""
from __future__ import annotations


from rfsn_kernel.types import StateSnapshot, Proposal
from rfsn_companion.proposer import propose
from rfsn_companion.proposer_variants import PROPOSER_BY_VARIANT, select_proposer
from rfsn_companion.proposers.baseline import propose_baseline
from rfsn_companion.proposers.read_then_test import propose_read_then_test
from rfsn_companion.proposers.read_patch_test import propose_read_patch_test
from rfsn_companion.proposers.brain_wrap import propose_brain


class TestProposerRegistry:
    """Test proposer variant registry."""

    def test_all_variants_registered(self):
        """All expected variants should be in registry."""
        assert "v0_minimal" in PROPOSER_BY_VARIANT
        assert "v1_patch_then_test" in PROPOSER_BY_VARIANT
        assert "v2_read_then_plan" in PROPOSER_BY_VARIANT
        assert "v3_brain" in PROPOSER_BY_VARIANT

    def test_select_proposer_returns_function(self):
        """select_proposer should return callable."""
        for variant_id in PROPOSER_BY_VARIANT:
            fn = select_proposer(variant_id)
            assert callable(fn)

    def test_select_proposer_unknown_returns_baseline(self):
        """Unknown variant should fall back to baseline."""
        fn = select_proposer("nonexistent_variant")
        assert fn is propose_baseline


class TestBaselineProposer:
    """Test baseline proposer."""

    def test_baseline_returns_run_tests(self, tmp_path):
        """Baseline should return RUN_TESTS action."""
        state = StateSnapshot(task_id="t", workspace_root=str(tmp_path), step=0)
        proposal = propose_baseline(state)

        assert isinstance(proposal, Proposal)
        assert len(proposal.actions) == 1
        assert proposal.actions[0].name == "RUN_TESTS"


class TestReadThenTestProposer:
    """Test read_then_test proposer."""

    def test_read_then_test_with_path(self, tmp_path):
        """Should read specified path then run tests."""
        read_path = str(tmp_path / "target.py")
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={"read_path": read_path},
        )
        proposal = propose_read_then_test(state)

        assert len(proposal.actions) == 2
        assert proposal.actions[0].name == "READ_FILE"
        assert proposal.actions[0].args["path"] == read_path
        assert proposal.actions[1].name == "RUN_TESTS"


class TestReadPatchTestProposer:
    """Test read_patch_test proposer."""

    def test_read_patch_test_with_content(self, tmp_path):
        """Should read, patch, then test."""
        patch_path = str(tmp_path / "fix.py")
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={"patch_path": patch_path, "patch_content": "# fixed\n"},
        )
        proposal = propose_read_patch_test(state)

        assert len(proposal.actions) == 3
        assert proposal.actions[0].name == "READ_FILE"
        assert proposal.actions[1].name == "APPLY_PATCH"
        assert proposal.actions[1].args["content"] == "# fixed\n"
        assert proposal.actions[2].name == "RUN_TESTS"


class TestBrainProposer:
    """Test brain proposer (hardened version)."""

    def test_brain_no_targets_just_tests(self, tmp_path):
        """Without targets, should only run tests."""
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={"prompt_variant": "v3_brain"},
        )
        proposal = propose_brain(state)

        assert len(proposal.actions) == 1
        assert proposal.actions[0].name == "RUN_TESTS"

    def test_brain_with_read_path(self, tmp_path):
        """With read_path, should read then test."""
        read_path = str(tmp_path / "analysis.py")
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={"prompt_variant": "v3_brain", "read_path": read_path},
        )
        proposal = propose_brain(state)

        assert len(proposal.actions) == 2
        assert proposal.actions[0].name == "READ_FILE"
        assert proposal.actions[0].args["path"] == read_path
        assert proposal.actions[1].name == "RUN_TESTS"

    def test_brain_with_patch_adds_read_first(self, tmp_path):
        """With patch but no read, should add READ_FILE before patch."""
        patch_path = str(tmp_path / "target.py")
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={
                "prompt_variant": "v3_brain",
                "patch_path": patch_path,
                "patch_content": "# new content\n",
            },
        )
        proposal = propose_brain(state)

        # Should be: READ_FILE, APPLY_PATCH, RUN_TESTS
        assert len(proposal.actions) == 3
        assert proposal.actions[0].name == "READ_FILE"
        assert proposal.actions[0].args["path"] == patch_path
        assert proposal.actions[1].name == "APPLY_PATCH"
        assert proposal.actions[2].name == "RUN_TESTS"

    def test_brain_with_same_read_and_patch(self, tmp_path):
        """With same read and patch path, should not duplicate read."""
        target = str(tmp_path / "file.py")
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={
                "prompt_variant": "v3_brain",
                "read_path": target,
                "patch_path": target,
                "patch_content": "# updated\n",
            },
        )
        proposal = propose_brain(state)

        # Should be: READ_FILE, APPLY_PATCH, RUN_TESTS (no duplicate read)
        assert len(proposal.actions) == 3
        read_count = sum(1 for a in proposal.actions if a.name == "READ_FILE")
        assert read_count == 1

    def test_brain_never_emits_run_cmd(self, tmp_path):
        """Brain proposer should never emit RUN_CMD."""
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={
                "prompt_variant": "v3_brain",
                "read_path": str(tmp_path / "x.py"),
                "patch_path": str(tmp_path / "y.py"),
                "patch_content": "z\n",
            },
        )
        proposal = propose_brain(state)

        for action in proposal.actions:
            assert action.name != "RUN_CMD"


class TestMainProposer:
    """Test main propose() function routing."""

    def test_propose_routes_by_variant(self, tmp_path):
        """propose() should route to correct variant."""
        for variant_id in PROPOSER_BY_VARIANT:
            state = StateSnapshot(
                task_id="t",
                workspace_root=str(tmp_path),
                step=0,
                notes={"prompt_variant": variant_id},
            )
            proposal = propose(state)
            assert isinstance(proposal, Proposal)
            assert len(proposal.actions) >= 1

    def test_propose_default_variant(self, tmp_path):
        """Missing variant should use baseline."""
        state = StateSnapshot(
            task_id="t",
            workspace_root=str(tmp_path),
            step=0,
            notes={},  # No variant specified
        )
        proposal = propose(state)
        assert isinstance(proposal, Proposal)
