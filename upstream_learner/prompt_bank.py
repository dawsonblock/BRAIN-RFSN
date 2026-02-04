# upstream_learner/prompt_bank.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PromptVariant:
    variant_id: str
    system: str
    instructions: str


def default_prompt_bank() -> List[PromptVariant]:
    return [
        PromptVariant(
            variant_id="v0_minimal",
            system="You are a proposer. Output actions only.",
            instructions="Run tests first. Do not edit files unless you can justify changes.",
        ),
        PromptVariant(
            variant_id="v1_patch_then_test",
            system="You are a proposer. Output actions only.",
            instructions="If a fix is obvious, propose a small patch then run tests.",
        ),
        PromptVariant(
            variant_id="v2_read_then_plan",
            system="You are a proposer. Output actions only.",
            instructions="Read a relevant file (READ_FILE), then run tests, then patch if needed.",
        ),
        PromptVariant(
            variant_id="v3_brain",
            system="You are a proposer. Output actions only.",
            instructions=(
                "Use internal cognition to decide read/patch/test, but never execute. "
                "Never invent patch targets. Only patch paths explicitly provided by state.notes."
            ),
        ),
        PromptVariant(
            variant_id="v4_trace_read",
            system="You are a proposer. Output actions only.",
            instructions=(
                "Use last test output to deterministically pick candidate files from stack traces. "
                "Only read files under workspace. Never invent patch targets."
            ),
        ),
        PromptVariant(
            variant_id="v5_llm_patch",
            system="You are a proposer. Output actions only.",
            instructions=(
                "Use DeepSeek LLM to generate patches from error traces. "
                "Select top candidate from trace, call LLM, apply generated patch, run tests."
            ),
        ),
    ]
