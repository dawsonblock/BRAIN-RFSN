# tests/test_policy_arms.py
"""Tests for policy arms configuration."""
from __future__ import annotations

from upstream_learner.policy_arms import (
    PolicyArm,
    ContextPolicy,
    PatchPolicy,
    ModelPolicy,
    DEFAULT_ARMS,
    get_arm_by_id,
    get_all_arm_ids,
    get_prompt_suffix,
    arms_to_prompt_bank_dict,
)


class TestPolicyArms:
    def test_default_arms_exist(self):
        assert len(DEFAULT_ARMS) == 8
    
    def test_arm_ids_unique(self):
        ids = get_all_arm_ids()
        assert len(ids) == len(set(ids))
    
    def test_get_arm_by_id_found(self):
        arm = get_arm_by_id("traceback_grep_standard")
        assert arm is not None
        assert arm.context == ContextPolicy.TRACEBACK_GREP
        assert arm.patch == PatchPolicy.MINIMAL_FIX
    
    def test_get_arm_by_id_not_found(self):
        assert get_arm_by_id("nonexistent") is None
    
    def test_prompt_suffix_exists_for_all_policies(self):
        for policy in PatchPolicy:
            arm = PolicyArm(
                arm_id="test",
                context=ContextPolicy.MINIMAL,
                patch=policy,
                model=ModelPolicy.FAST,
                description="test",
            )
            suffix = get_prompt_suffix(arm)
            assert isinstance(suffix, str)
    
    def test_arms_to_prompt_bank_dict(self):
        bank = arms_to_prompt_bank_dict()
        assert len(bank) == 8
        assert "traceback_grep_standard" in bank
        assert isinstance(bank["traceback_grep_standard"], str)
    
    def test_arm_parameters_valid(self):
        for arm in DEFAULT_ARMS:
            assert arm.max_files >= 0
            assert arm.max_total_bytes >= 0
            assert 0.0 <= arm.temperature <= 1.0
            assert arm.max_tokens > 0


class TestContextPolicy:
    def test_context_policies(self):
        assert len(ContextPolicy) == 5
        assert ContextPolicy.TRACEBACK_GREP.value == "traceback_grep"


class TestPatchPolicy:
    def test_patch_policies(self):
        assert len(PatchPolicy) == 5
        assert PatchPolicy.MINIMAL_FIX.value == "minimal_fix"


class TestModelPolicy:
    def test_model_policies(self):
        assert len(ModelPolicy) == 4
        assert ModelPolicy.FAST.value == "fast"
