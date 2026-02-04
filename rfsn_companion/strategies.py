# rfsn_companion/strategies.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from rfsn_kernel.types import Action, Proposal, StateSnapshot


def _get_notes_str_list(state: StateSnapshot, key: str, limit: int = 12) -> List[str]:
    v = state.notes.get(key)
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return [x for x in v if x.strip()][:limit]
    return []


def _get_notes_str(state: StateSnapshot, key: str, max_len: int = 200_000) -> Optional[str]:
    v = state.notes.get(key)
    if isinstance(v, str) and v.strip():
        return v[:max_len]
    return None


def _safe_default_reads() -> List[str]:
    # "good first reads" across python repos; harmless if missing (READ_FILE may fail at execute-time)
    return [
        "README.md",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "requirements.txt",
        "pytest.ini",
    ]


@dataclass(frozen=True)
class PlannerStrategy:
    """
    A strategy is just: state -> Proposal(actions).
    It is NOT allowed to execute anything; only propose.
    """
    arm_id: str
    label: str

    def propose(self, state: StateSnapshot) -> Proposal:
        raise NotImplementedError


class RunTestsOnly(PlannerStrategy):
    def propose(self, state: StateSnapshot) -> Proposal:
        actions = (
            Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
        )
        return Proposal(actions=actions, meta={"strategy": self.arm_id})


class ReadThenTests(PlannerStrategy):
    def propose(self, state: StateSnapshot) -> Proposal:
        paths = _safe_default_reads()
        actions = tuple(Action("READ_FILE", {"path": p}) for p in paths) + (
            Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
        )
        return Proposal(actions=actions, meta={"strategy": self.arm_id, "read_paths": paths})


class FocusedReadsThenTests(PlannerStrategy):
    """
    Reads a small set of "likely hot" paths provided by upstream in state.notes["focus_paths"].
    Then runs tests.
    """
    def propose(self, state: StateSnapshot) -> Proposal:
        focus = _get_notes_str_list(state, "focus_paths", limit=20)
        if not focus:
            focus = _safe_default_reads()

        actions: Tuple[Action, ...] = tuple(Action("READ_FILE", {"path": p}) for p in focus) + (
            Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
        )
        return Proposal(actions=actions, meta={"strategy": self.arm_id, "focus_paths": focus})


class PatchIfProvidedThenTests(PlannerStrategy):
    """
    If upstream provides a unified diff in state.notes["patch_text"], propose applying it.
    Always runs tests after.
    """
    def propose(self, state: StateSnapshot) -> Proposal:
        patch = _get_notes_str(state, "patch_text")
        actions: List[Action] = []

        if patch:
            actions.append(Action("APPLY_PATCH", {"patch": patch}))

        actions.append(Action("RUN_TESTS", {"argv": ["pytest", "-q"]}))
        return Proposal(actions=tuple(actions), meta={"strategy": self.arm_id, "has_patch": bool(patch)})


class ReadPatchTest(PlannerStrategy):
    """
    Read a few files (defaults + optional focus_paths), apply patch if provided, then tests.
    """
    def propose(self, state: StateSnapshot) -> Proposal:
        focus = _get_notes_str_list(state, "focus_paths", limit=12) or _safe_default_reads()
        patch = _get_notes_str(state, "patch_text")

        actions: List[Action] = [Action("READ_FILE", {"path": p}) for p in focus]
        if patch:
            actions.append(Action("APPLY_PATCH", {"patch": patch}))
        actions.append(Action("RUN_TESTS", {"argv": ["pytest", "-q"]}))

        return Proposal(
            actions=tuple(actions),
            meta={"strategy": self.arm_id, "focus_paths": focus, "has_patch": bool(patch)},
        )


class WriteNoteThenTests(PlannerStrategy):
    """
    Writes a small marker file (inside workspace) then runs tests.
    Useful as a sanity check that WRITE_FILE confinement works end-to-end.
    """
    def propose(self, state: StateSnapshot) -> Proposal:
        text = _get_notes_str(state, "note_text", max_len=10_000) or "rfsn marker\n"
        actions = (
            Action("WRITE_FILE", {"path": "run_logs/marker.txt", "text": text}),
            Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
        )
        return Proposal(actions=actions, meta={"strategy": self.arm_id})


def build_strategy_registry() -> Dict[str, PlannerStrategy]:
    """
    Add / remove arms here. Upstream bandit chooses among these ids.
    """
    strategies: List[PlannerStrategy] = [
        RunTestsOnly(arm_id="run_tests_only", label="Run tests only"),
        ReadThenTests(arm_id="read_then_tests", label="Read common config/docs then run tests"),
        FocusedReadsThenTests(arm_id="focused_reads_then_tests", label="Read focus_paths then run tests"),
        PatchIfProvidedThenTests(arm_id="patch_if_provided_then_tests", label="Apply provided patch then run tests"),
        ReadPatchTest(arm_id="read_patch_test", label="Read focus, apply patch, then run tests"),
        WriteNoteThenTests(arm_id="write_note_then_tests", label="Write marker then run tests"),
    ]
    return {s.arm_id: s for s in strategies}
