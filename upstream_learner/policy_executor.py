# upstream_learner/policy_executor.py
"""
Policy Executor - Connects PolicyArm configuration to actual execution.

This module bridges the gap between:
- PolicyArm (configuration: context policy, patch policy, model policy)
- Actual execution (context building, prompt generation, LLM calls)

The executor:
1. Selects a PolicyArm via the bandit
2. Configures context building based on arm.context
3. Generates prompts with arm-specific suffixes
4. Configures model parameters from arm.model
5. Returns structured results for bandit learning
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .policy_arms import (
    PolicyArm,
    ContextPolicy,
    PatchPolicy,
    ModelPolicy,
    DEFAULT_ARMS,
    get_arm_by_id,
    get_prompt_suffix,
)
from .bandit import ThompsonBandit


@dataclass
class ContextConfig:
    """Configuration for context building derived from PolicyArm."""
    max_files: int = 12
    max_total_bytes: int = 240_000
    max_grep_patterns: int = 10
    include_traceback_files: bool = True
    include_imports: bool = False
    include_grep_expansion: bool = True
    deep_grep: bool = False
    minimal_mode: bool = False


@dataclass
class ModelConfig:
    """Configuration for LLM calls derived from PolicyArm."""
    temperature: float = 0.2
    max_tokens: int = 4096
    model_tier: str = "standard"  # fast, standard, creative


@dataclass
class ExecutionPlan:
    """Complete execution plan from a PolicyArm."""
    arm: PolicyArm
    context_config: ContextConfig
    model_config: ModelConfig
    prompt_suffix: str


def arm_to_context_config(arm: PolicyArm) -> ContextConfig:
    """Convert PolicyArm to ContextConfig based on context policy."""
    config = ContextConfig(
        max_files=arm.max_files,
        max_total_bytes=arm.max_total_bytes,
        max_grep_patterns=arm.max_grep_patterns,
    )

    if arm.context == ContextPolicy.TRACEBACK_ONLY:
        config.include_traceback_files = True
        config.include_imports = False
        config.include_grep_expansion = False
        config.deep_grep = False

    elif arm.context == ContextPolicy.TRACEBACK_GREP:
        config.include_traceback_files = True
        config.include_imports = False
        config.include_grep_expansion = True
        config.deep_grep = False

    elif arm.context == ContextPolicy.TRACEBACK_IMPORTS:
        config.include_traceback_files = True
        config.include_imports = True
        config.include_grep_expansion = False
        config.deep_grep = False

    elif arm.context == ContextPolicy.DEEP_GREP:
        config.include_traceback_files = True
        config.include_imports = True
        config.include_grep_expansion = True
        config.deep_grep = True

    elif arm.context == ContextPolicy.MINIMAL:
        config.include_traceback_files = False
        config.include_imports = False
        config.include_grep_expansion = False
        config.minimal_mode = True
        config.max_files = 0

    return config


def arm_to_model_config(arm: PolicyArm) -> ModelConfig:
    """Convert PolicyArm to ModelConfig based on model policy."""
    config = ModelConfig(
        temperature=arm.temperature,
        max_tokens=arm.max_tokens,
    )

    if arm.model == ModelPolicy.FAST:
        config.model_tier = "fast"
        config.temperature = max(0.0, arm.temperature)
    elif arm.model == ModelPolicy.STANDARD:
        config.model_tier = "standard"
    elif arm.model == ModelPolicy.CREATIVE:
        config.model_tier = "creative"
        config.temperature = max(0.5, arm.temperature)
    elif arm.model == ModelPolicy.RERANK:
        config.model_tier = "standard"
        # Rerank generates multiple and picks best

    return config


def create_execution_plan(arm: PolicyArm) -> ExecutionPlan:
    """Create complete execution plan from a PolicyArm."""
    return ExecutionPlan(
        arm=arm,
        context_config=arm_to_context_config(arm),
        model_config=arm_to_model_config(arm),
        prompt_suffix=get_prompt_suffix(arm),
    )


class PolicyExecutor:
    """
    Executes policies selected by the bandit.

    Usage:
        executor = PolicyExecutor()
        arm_id = executor.select_arm()
        plan = executor.get_execution_plan(arm_id)
        # ... execute with plan.context_config, plan.model_config, plan.prompt_suffix
        executor.record_outcome(arm_id, reward=1.0)  # test passed
    """

    def __init__(
        self,
        bandit: ThompsonBandit | None = None,
        selection_method: str = "thompson",
    ):
        self.bandit = bandit or ThompsonBandit()
        self.selection_method = selection_method
        self._ensure_arms_registered()

    def _ensure_arms_registered(self) -> None:
        """Ensure all default arms are registered in the bandit."""
        for arm in DEFAULT_ARMS:
            self.bandit.ensure(arm.arm_id)

    def select_arm(self) -> str:
        """Select an arm using the configured selection method."""
        arm_id = self.bandit.choose(method=self.selection_method)
        self.bandit.bump_seed()  # Ensure different selection next time
        return arm_id

    def get_arm(self, arm_id: str) -> PolicyArm | None:
        """Get PolicyArm by ID."""
        return get_arm_by_id(arm_id)

    def get_execution_plan(self, arm_id: str) -> ExecutionPlan | None:
        """Get execution plan for an arm."""
        arm = get_arm_by_id(arm_id)
        if arm is None:
            return None
        return create_execution_plan(arm)

    def record_outcome(self, arm_id: str, reward: float) -> None:
        """Record outcome for learning."""
        self.bandit.update(arm_id, reward)

    def get_stats(self) -> List[Dict[str, Any]]:
        """Get arm statistics for monitoring."""
        stats = self.bandit.arm_stats()
        # Enrich with arm descriptions
        for stat in stats:
            arm = get_arm_by_id(stat["arm_id"])
            if arm:
                stat["description"] = arm.description
                stat["context_policy"] = arm.context.value
                stat["patch_policy"] = arm.patch.value
                stat["model_policy"] = arm.model.value
        return stats

    def best_arm_id(self) -> str | None:
        """Get ID of best-performing arm."""
        return self.bandit.best_arm()


def integrate_with_state_notes(arm_id: str, notes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inject policy arm configuration into state.notes for companion strategies.

    This allows the companion planner to use policy arm configuration
    when building proposals.
    """
    arm = get_arm_by_id(arm_id)
    if arm is None:
        return notes

    updated = dict(notes)
    updated["policy_arm_id"] = arm_id
    updated["policy_context"] = arm.context.value
    updated["policy_patch"] = arm.patch.value
    updated["policy_model"] = arm.model.value
    updated["policy_max_files"] = arm.max_files
    updated["policy_max_bytes"] = arm.max_total_bytes
    updated["policy_prompt_suffix"] = get_prompt_suffix(arm)
    return updated
