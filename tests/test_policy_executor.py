# tests/test_policy_executor.py
"""Tests for upstream_learner/policy_executor.py."""
import pytest

from upstream_learner.policy_arms import (
    PolicyArm,
    ContextPolicy,
    PatchPolicy,
    ModelPolicy,
    DEFAULT_ARMS,
    get_arm_by_id,
)
from upstream_learner.policy_executor import (
    arm_to_context_config,
    arm_to_model_config,
    create_execution_plan,
    PolicyExecutor,
    integrate_with_state_notes,
    ContextConfig,
    ModelConfig,
)
from upstream_learner.bandit import ThompsonBandit


class TestContextConfig:
    """Tests for arm_to_context_config."""

    def test_traceback_only(self):
        """TRACEBACK_ONLY should disable grep and imports."""
        arm = get_arm_by_id("traceback_minimal")
        assert arm is not None
        config = arm_to_context_config(arm)
        assert config.include_traceback_files is True
        assert config.include_grep_expansion is False
        assert config.include_imports is False
        assert config.deep_grep is False

    def test_traceback_grep(self):
        """TRACEBACK_GREP should enable grep expansion."""
        arm = get_arm_by_id("traceback_grep_standard")
        assert arm is not None
        config = arm_to_context_config(arm)
        assert config.include_traceback_files is True
        assert config.include_grep_expansion is True
        assert config.include_imports is False

    def test_traceback_imports(self):
        """TRACEBACK_IMPORTS should enable imports but not grep."""
        arm = get_arm_by_id("imports_minimal")
        assert arm is not None
        config = arm_to_context_config(arm)
        assert config.include_traceback_files is True
        assert config.include_imports is True
        assert config.include_grep_expansion is False

    def test_deep_grep(self):
        """DEEP_GREP should enable everything."""
        arm = get_arm_by_id("deep_grep_minimal")
        assert arm is not None
        config = arm_to_context_config(arm)
        assert config.include_traceback_files is True
        assert config.include_imports is True
        assert config.include_grep_expansion is True
        assert config.deep_grep is True

    def test_minimal(self):
        """MINIMAL should disable all context gathering."""
        arm = get_arm_by_id("minimal_fast")
        assert arm is not None
        config = arm_to_context_config(arm)
        assert config.minimal_mode is True
        assert config.include_traceback_files is False
        assert config.max_files == 0


class TestModelConfig:
    """Tests for arm_to_model_config."""

    def test_fast_model(self):
        """FAST should have fast tier."""
        arm = get_arm_by_id("traceback_minimal")
        assert arm is not None
        config = arm_to_model_config(arm)
        assert config.model_tier == "fast"
        assert config.temperature == 0.0

    def test_standard_model(self):
        """STANDARD should have standard tier."""
        arm = get_arm_by_id("traceback_grep_standard")
        assert arm is not None
        config = arm_to_model_config(arm)
        assert config.model_tier == "standard"

    def test_creative_model(self):
        """CREATIVE should have higher temperature."""
        arm = get_arm_by_id("deep_grep_edge_case")
        assert arm is not None
        config = arm_to_model_config(arm)
        assert config.model_tier == "creative"
        assert config.temperature >= 0.5


class TestExecutionPlan:
    """Tests for create_execution_plan."""

    def test_creates_complete_plan(self):
        """Should create a complete execution plan."""
        arm = get_arm_by_id("traceback_grep_standard")
        assert arm is not None
        plan = create_execution_plan(arm)
        assert plan.arm == arm
        assert isinstance(plan.context_config, ContextConfig)
        assert isinstance(plan.model_config, ModelConfig)
        assert len(plan.prompt_suffix) > 0

    def test_all_default_arms_have_plans(self):
        """Every default arm should produce a valid plan."""
        for arm in DEFAULT_ARMS:
            plan = create_execution_plan(arm)
            assert plan is not None
            assert plan.arm.arm_id == arm.arm_id


class TestPolicyExecutor:
    """Tests for PolicyExecutor class."""

    def test_init_registers_all_arms(self):
        """Should register all default arms in the bandit."""
        executor = PolicyExecutor()
        for arm in DEFAULT_ARMS:
            assert arm.arm_id in executor.bandit.arms

    def test_select_arm_returns_valid_id(self):
        """Should return a valid arm ID."""
        executor = PolicyExecutor()
        arm_id = executor.select_arm()
        assert arm_id in [a.arm_id for a in DEFAULT_ARMS]

    def test_get_arm(self):
        """Should return PolicyArm by ID."""
        executor = PolicyExecutor()
        arm = executor.get_arm("traceback_minimal")
        assert arm is not None
        assert arm.arm_id == "traceback_minimal"

    def test_get_arm_invalid(self):
        """Should return None for invalid arm ID."""
        executor = PolicyExecutor()
        arm = executor.get_arm("nonexistent")
        assert arm is None

    def test_get_execution_plan(self):
        """Should return execution plan."""
        executor = PolicyExecutor()
        plan = executor.get_execution_plan("traceback_grep_standard")
        assert plan is not None
        assert plan.arm.arm_id == "traceback_grep_standard"

    def test_record_outcome_updates_bandit(self):
        """Should update bandit with reward."""
        executor = PolicyExecutor()
        arm_id = "traceback_minimal"
        executor.record_outcome(arm_id, 1.0)
        assert executor.bandit.arms[arm_id].pulls > 0
        assert executor.bandit.arms[arm_id].total_reward > 0

    def test_get_stats_enriched(self):
        """Should return enriched statistics."""
        executor = PolicyExecutor()
        executor.record_outcome("traceback_minimal", 1.0)
        stats = executor.get_stats()
        assert len(stats) > 0
        # Check for enrichment
        stat = next(s for s in stats if s["arm_id"] == "traceback_minimal")
        assert "description" in stat
        assert "context_policy" in stat
        assert "patch_policy" in stat

    def test_custom_selection_method(self):
        """Should use custom selection method."""
        executor = PolicyExecutor(selection_method="greedy")
        assert executor.selection_method == "greedy"


class TestIntegrateWithStateNotes:
    """Tests for integrate_with_state_notes."""

    def test_injects_policy_config(self):
        """Should inject policy arm config into notes."""
        notes = {"existing": "value"}
        updated = integrate_with_state_notes("traceback_grep_standard", notes)
        assert updated["existing"] == "value"  # Original preserved
        assert updated["policy_arm_id"] == "traceback_grep_standard"
        assert updated["policy_context"] == "traceback_grep"
        assert updated["policy_patch"] == "minimal_fix"
        assert updated["policy_model"] == "standard"

    def test_invalid_arm_returns_unchanged(self):
        """Should return unchanged notes for invalid arm."""
        notes = {"key": "value"}
        updated = integrate_with_state_notes("nonexistent", notes)
        assert updated == notes
        assert "policy_arm_id" not in updated

    def test_includes_prompt_suffix(self):
        """Should include prompt suffix."""
        notes = {}
        updated = integrate_with_state_notes("traceback_grep_defensive", notes)
        assert "policy_prompt_suffix" in updated
        assert len(updated["policy_prompt_suffix"]) > 0
