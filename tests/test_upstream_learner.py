# tests/test_upstream_learner.py
"""Tests for the upstream learner (bandit, features, episode runner)."""
from __future__ import annotations

import os

from upstream_learner.bandit import ThompsonBandit, BetaArm
from upstream_learner.features import reward_from_episode
from upstream_learner.prompt_bank import default_prompt_bank, PromptVariant
from upstream_learner.policy_store import save_bandit, load_bandit
from upstream_learner.episode_runner import run_episode, EpisodeOutcome
from rfsn_kernel.types import StateSnapshot, Proposal, Action


class TestThompsonBandit:
    """Test Thompson sampling bandit."""

    def test_bandit_initialization(self):
        """Bandit should initialize with empty arms."""
        bandit = ThompsonBandit(seed=42)
        assert bandit.seed == 42
        assert len(bandit.arms) == 0

    def test_bandit_choose_creates_arm(self):
        """Choosing from new arms should create them."""
        bandit = ThompsonBandit(seed=42)
        choice = bandit.choose(["a", "b", "c"])
        assert choice in ["a", "b", "c"]
        assert "a" in bandit.arms
        assert "b" in bandit.arms
        assert "c" in bandit.arms

    def test_bandit_update_modifies_arm(self):
        """Updating should modify arm parameters."""
        bandit = ThompsonBandit(seed=42)
        bandit.ensure_arm("a")

        initial_alpha = bandit.arms["a"].alpha
        initial_beta = bandit.arms["a"].beta

        bandit.update("a", 1.0)  # Full success

        assert bandit.arms["a"].alpha > initial_alpha
        assert bandit.arms["a"].beta == initial_beta  # Beta unchanged on full success

    def test_bandit_deterministic_with_seed(self):
        """Same seed should produce same choices."""
        choices1 = []
        bandit1 = ThompsonBandit(seed=123)
        for _ in range(5):
            choices1.append(bandit1.choose(["x", "y", "z"]))

        choices2 = []
        bandit2 = ThompsonBandit(seed=123)
        for _ in range(5):
            choices2.append(bandit2.choose(["x", "y", "z"]))

        assert choices1 == choices2

    def test_beta_arm_sample_in_range(self):
        """Beta arm samples should be in [0, 1]."""
        import random
        arm = BetaArm(alpha=2.0, beta=5.0)
        rng = random.Random(42)

        for _ in range(100):
            sample = arm.sample(rng)
            assert 0.0 <= sample <= 1.0


class TestRewardComputation:
    """Test reward computation from episode outcomes."""

    def test_reward_deny_is_zero(self):
        """Denied decision should yield zero reward."""
        r = reward_from_episode("DENY", tests_passed=True, wall_ms=1000)
        assert r == 0.0

    def test_reward_allow_tests_fail(self):
        """Allowed but tests failed should yield low reward."""
        r = reward_from_episode("ALLOW", tests_passed=False, wall_ms=1000)
        assert 0.0 < r < 0.5

    def test_reward_allow_tests_pass(self):
        """Allowed with passing tests should yield high reward."""
        r = reward_from_episode("ALLOW", tests_passed=True, wall_ms=1000)
        assert r > 0.5

    def test_reward_time_penalty(self):
        """Long running time should reduce reward."""
        fast = reward_from_episode("ALLOW", tests_passed=True, wall_ms=1000)
        slow = reward_from_episode("ALLOW", tests_passed=True, wall_ms=300000)
        assert fast > slow


class TestPromptBank:
    """Test prompt bank functionality."""

    def test_prompt_bank_has_variants(self):
        """Prompt bank should have all expected variants."""
        bank = default_prompt_bank()
        variant_ids = {v.variant_id for v in bank}

        assert "v0_minimal" in variant_ids
        assert "v1_patch_then_test" in variant_ids
        assert "v2_read_then_plan" in variant_ids
        assert "v3_brain" in variant_ids

    def test_prompt_variant_structure(self):
        """Each variant should have required fields."""
        bank = default_prompt_bank()

        for variant in bank:
            assert isinstance(variant, PromptVariant)
            assert variant.variant_id
            assert variant.system
            assert variant.instructions


class TestPolicyStore:
    """Test bandit persistence."""

    def test_save_and_load_bandit(self, tmp_path):
        """Bandit state should persist correctly."""
        path = str(tmp_path / "bandit.json")

        # Create and train bandit
        original = ThompsonBandit(seed=999)
        original.ensure_arm("arm1")
        original.update("arm1", 0.8)
        original.ensure_arm("arm2")
        original.update("arm2", 0.2)

        save_bandit(path, original)

        # Load and compare
        loaded = load_bandit(path)
        assert loaded.seed == original.seed
        assert "arm1" in loaded.arms
        assert "arm2" in loaded.arms
        assert abs(loaded.arms["arm1"].alpha - original.arms["arm1"].alpha) < 0.001

    def test_load_missing_file_returns_default(self, tmp_path):
        """Loading missing file should return default bandit."""
        path = str(tmp_path / "nonexistent.json")
        bandit = load_bandit(path, default_seed=42)

        assert bandit.seed == 42
        assert len(bandit.arms) == 0


class TestEpisodeRunner:
    """Test episode runner integration."""

    def test_episode_runner_produces_outcome(self, tmp_path):
        """Episode runner should produce valid outcome."""
        ledger_path = str(tmp_path / "ledger.jsonl")
        ws = str(tmp_path)

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="test_proposal",
            actions=(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),),
        )

        outcome = run_episode(ledger_path=ledger_path, state=state, proposal=proposal)

        assert isinstance(outcome, EpisodeOutcome)
        assert outcome.decision_status in ("ALLOW", "DENY")
        assert isinstance(outcome.reward, float)
        assert 0.0 <= outcome.reward <= 1.0
        assert outcome.wall_ms >= 0

    def test_episode_runner_logs_to_ledger(self, tmp_path):
        """Episode should be logged to ledger."""
        ledger_path = str(tmp_path / "ledger.jsonl")
        ws = str(tmp_path)

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="logged_proposal",
            actions=(Action(name="RUN_TESTS", args={"argv": ["pytest"]}),),
        )

        run_episode(ledger_path=ledger_path, state=state, proposal=proposal)

        assert os.path.exists(ledger_path)
        with open(ledger_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
