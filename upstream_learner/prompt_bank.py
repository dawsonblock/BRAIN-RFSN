# upstream_learner/prompt_bank.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PromptBank:
    # arm_id -> label (for now). In a real system, store prompt templates + planner configs.
    arms: Dict[str, str]


def default_prompt_bank() -> PromptBank:
    return PromptBank(
        arms={
            "run_tests_only": "Run allowlisted tests only",
            "read_then_tests": "Read common repo files, then tests",
            "focused_reads_then_tests": "Read focus_paths from notes, then tests",
            "patch_if_provided_then_tests": "Apply patch_text from notes if present, then tests",
            "read_patch_test": "Read focus, apply patch_text if present, then tests",
            "write_note_then_tests": "Write run_logs/marker.txt (confined), then tests",
        }
    )
