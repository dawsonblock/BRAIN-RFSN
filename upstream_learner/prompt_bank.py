# upstream_learner/prompt_bank.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PromptBank:
    # arm_id -> short label; real systems store full prompt templates
    arms: Dict[str, str]


def default_prompt_bank() -> PromptBank:
    return PromptBank(
        arms={
            "default": "Deterministic stub (no LLM).",
        }
    )
