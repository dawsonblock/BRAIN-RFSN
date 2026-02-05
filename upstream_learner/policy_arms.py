# upstream_learner/policy_arms.py
"""
Real policy arms that change solving behavior.

Categories:
1. CONTEXT policy: How to gather context for LLM
2. PATCH policy: What kind of fix to request
3. MODEL policy: Which model/temperature to use

Each arm is a distinct strategy that the bandit can learn over.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ContextPolicy(str, Enum):
    """How to build context for the LLM."""
    TRACEBACK_ONLY = "traceback_only"            # Only traceback files
    TRACEBACK_GREP = "traceback_grep"            # Traceback + grep expansion (default)
    TRACEBACK_IMPORTS = "traceback_imports"      # Traceback + import neighbors
    DEEP_GREP = "deep_grep"                      # Aggressive grep for all symbols
    MINIMAL = "minimal"                          # Just pytest output, no files


class PatchPolicy(str, Enum):
    """What kind of fix to request."""
    MINIMAL_FIX = "minimal_fix"                  # Smallest change to pass tests
    ASSERTION_HARDENING = "assertion_hardening"  # Add guards/assertions
    TYPE_EDGE_CASE = "type_edge_case"            # Handle edge cases/types
    REFACTOR_FIX = "refactor_fix"                # Refactor + fix
    DEFENSIVE = "defensive"                      # Add error handling


class ModelPolicy(str, Enum):
    """Which model/temperature configuration."""
    FAST = "fast"                                # Fast model, low temp (0.0)
    STANDARD = "standard"                        # Standard model, low temp (0.2)
    CREATIVE = "creative"                        # Standard model, higher temp (0.7)
    RERANK = "rerank"                            # Generate multiple, pick best


@dataclass(frozen=True)
class PolicyArm:
    """Complete policy configuration for one bandit arm."""
    arm_id: str
    context: ContextPolicy
    patch: PatchPolicy
    model: ModelPolicy
    description: str
    
    # Context builder parameters
    max_files: int = 12
    max_total_bytes: int = 240_000
    max_grep_patterns: int = 10
    
    # Model parameters
    temperature: float = 0.2
    max_tokens: int = 4096


# Default arms that cover the policy space
DEFAULT_ARMS: Tuple[PolicyArm, ...] = (
    # Traceback-focused arms
    PolicyArm(
        arm_id="traceback_minimal",
        context=ContextPolicy.TRACEBACK_ONLY,
        patch=PatchPolicy.MINIMAL_FIX,
        model=ModelPolicy.FAST,
        description="Traceback files only, minimal fix, fast model",
        max_files=6,
        max_total_bytes=120_000,
        temperature=0.0,
    ),
    PolicyArm(
        arm_id="traceback_grep_standard",
        context=ContextPolicy.TRACEBACK_GREP,
        patch=PatchPolicy.MINIMAL_FIX,
        model=ModelPolicy.STANDARD,
        description="Traceback + grep, minimal fix, standard model",
        max_files=12,
        max_total_bytes=240_000,
        temperature=0.2,
    ),
    PolicyArm(
        arm_id="traceback_grep_defensive",
        context=ContextPolicy.TRACEBACK_GREP,
        patch=PatchPolicy.DEFENSIVE,
        model=ModelPolicy.STANDARD,
        description="Traceback + grep, defensive fix (add error handling)",
        max_files=12,
        max_total_bytes=240_000,
        temperature=0.3,
    ),
    # Deep context arms
    PolicyArm(
        arm_id="deep_grep_minimal",
        context=ContextPolicy.DEEP_GREP,
        patch=PatchPolicy.MINIMAL_FIX,
        model=ModelPolicy.STANDARD,
        description="Deep grep for all symbols, minimal fix",
        max_files=16,
        max_total_bytes=320_000,
        max_grep_patterns=20,
        temperature=0.2,
    ),
    PolicyArm(
        arm_id="deep_grep_edge_case",
        context=ContextPolicy.DEEP_GREP,
        patch=PatchPolicy.TYPE_EDGE_CASE,
        model=ModelPolicy.CREATIVE,
        description="Deep grep, fix edge cases/types, creative",
        max_files=16,
        max_total_bytes=320_000,
        max_grep_patterns=20,
        temperature=0.7,
    ),
    # Import-aware arms
    PolicyArm(
        arm_id="imports_minimal",
        context=ContextPolicy.TRACEBACK_IMPORTS,
        patch=PatchPolicy.MINIMAL_FIX,
        model=ModelPolicy.STANDARD,
        description="Traceback + import neighbors, minimal fix",
        max_files=14,
        max_total_bytes=280_000,
        temperature=0.2,
    ),
    # Minimal context arms (for simple bugs)
    PolicyArm(
        arm_id="minimal_fast",
        context=ContextPolicy.MINIMAL,
        patch=PatchPolicy.MINIMAL_FIX,
        model=ModelPolicy.FAST,
        description="Just pytest output, minimal fix, fast model",
        max_files=0,
        max_total_bytes=0,
        temperature=0.0,
    ),
    # Assertion-focused arm
    PolicyArm(
        arm_id="grep_assertion",
        context=ContextPolicy.TRACEBACK_GREP,
        patch=PatchPolicy.ASSERTION_HARDENING,
        model=ModelPolicy.STANDARD,
        description="Traceback + grep, add assertions/guards",
        max_files=12,
        max_total_bytes=240_000,
        temperature=0.3,
    ),
)


def get_arm_by_id(arm_id: str) -> Optional[PolicyArm]:
    """Look up arm by ID."""
    for arm in DEFAULT_ARMS:
        if arm.arm_id == arm_id:
            return arm
    return None


def get_all_arm_ids() -> List[str]:
    """Get all arm IDs."""
    return [arm.arm_id for arm in DEFAULT_ARMS]


def get_prompt_suffix(arm: PolicyArm) -> str:
    """
    Generate prompt suffix based on patch policy.
    This modifies how the LLM approaches the fix.
    """
    suffixes = {
        PatchPolicy.MINIMAL_FIX: (
            "Make the SMALLEST possible change to fix the failing test. "
            "Do not refactor or add unnecessary code."
        ),
        PatchPolicy.ASSERTION_HARDENING: (
            "Fix the failing test and ADD appropriate assertions or guards "
            "to prevent similar issues. Be defensive."
        ),
        PatchPolicy.TYPE_EDGE_CASE: (
            "Fix the failing test, paying special attention to type handling "
            "and edge cases. Handle None, empty strings, boundary values."
        ),
        PatchPolicy.REFACTOR_FIX: (
            "Fix the failing test. If the code structure contributes to the bug, "
            "you may refactor slightly to prevent similar issues."
        ),
        PatchPolicy.DEFENSIVE: (
            "Fix the failing test and add proper error handling. "
            "Wrap risky operations in try/except, validate inputs, handle edge cases."
        ),
    }
    return suffixes.get(arm.patch, "")


def arms_to_prompt_bank_dict() -> Dict[str, str]:
    """Convert arms to prompt bank format for compatibility."""
    return {arm.arm_id: arm.description for arm in DEFAULT_ARMS}
