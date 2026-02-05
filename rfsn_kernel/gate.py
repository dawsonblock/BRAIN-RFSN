# rfsn_kernel/gate.py
from __future__ import annotations

import os
import re
from typing import List

from .types import StateSnapshot, Proposal, Action, Decision
from .patch_safety import patch_paths_are_confined


# HARD BOUNDARY: allowlist test argv (deterministic, non-interactive)
_ALLOWED_TEST_PREFIXES: list[list[str]] = [
    ["python", "-m", "pytest", "-q"],
    ["pytest", "-q"],
]


def _abspath(workspace: str, p: str) -> str:
    # strict: resolve against workspace
    return os.path.abspath(os.path.join(workspace, p))


def _is_in_workspace(workspace: str, abs_path: str) -> bool:
    ws = os.path.abspath(workspace)
    ap = os.path.abspath(abs_path)
    try:
        common = os.path.commonpath([ws, ap])
    except ValueError:
        return False
    return common == ws



# Safe pytest nodeid pattern: path/to/file.py::ClassName::test_name
_PYTEST_NODEID_SAFE = re.compile(r"^[A-Za-z0-9_./:-]+(::[A-Za-z0-9_./:-]+)*$")


def is_allowed_tests_argv(argv: List[str]) -> bool:
    """
    Check if test argv matches allowlist.
    
    Allowed forms:
    - ["pytest", "-q"]
    - ["python", "-m", "pytest", "-q"]
    - ["pytest", "-q", "tests/foo.py::TestClass::test_bar"]  # safe nodeids
    """
    norm = [str(x).strip() for x in argv if str(x).strip() != ""]
    for prefix in _ALLOWED_TEST_PREFIXES:
        if norm[: len(prefix)] == prefix:
            # Exact match (no suffix)
            if len(norm) == len(prefix):
                return True
            # Check suffix: only safe nodeids allowed (no flags like --cov, -s, etc.)
            suffix = norm[len(prefix):]
            # Reject anything starting with - (flags)
            if any(s.startswith("-") for s in suffix):
                return False
            # All suffix items must be safe nodeids
            if all(_PYTEST_NODEID_SAFE.match(s) for s in suffix):
                return True
    return False


def gate(state: StateSnapshot, proposal: Proposal) -> Decision:
    ws = os.path.abspath(state.workspace)

    if not os.path.isdir(ws):
        return Decision(False, f"workspace does not exist: {ws}", ())

    approved: list[Action] = []
    for a in proposal.actions:
        if a.type == "READ_FILE":
            rel = a.payload.get("path")
            if not isinstance(rel, str) or not rel:
                return Decision(False, "READ_FILE missing path", ())
            ap = _abspath(ws, rel)
            if not _is_in_workspace(ws, ap):
                return Decision(False, f"READ_FILE escapes workspace: {rel}", ())
            approved.append(a)

        elif a.type == "WRITE_FILE":
            rel = a.payload.get("path")
            text = a.payload.get("text")
            if not isinstance(rel, str) or not rel:
                return Decision(False, "WRITE_FILE missing path", ())
            if not isinstance(text, str):
                return Decision(False, "WRITE_FILE missing text", ())
            ap = _abspath(ws, rel)
            if not _is_in_workspace(ws, ap):
                return Decision(False, f"WRITE_FILE escapes workspace: {rel}", ())
            approved.append(a)

        elif a.type == "APPLY_PATCH":
            patch = a.payload.get("patch")
            if not isinstance(patch, str) or not patch.strip():
                return Decision(False, "APPLY_PATCH missing patch", ())
            # hard requirement: patch paths must be parseable and confined
            ok, reason, _files = patch_paths_are_confined(ws, patch)
            if not ok:
                return Decision(False, f"APPLY_PATCH rejected: {reason}", ())
            approved.append(a)

        elif a.type == "RUN_TESTS":
            argv = a.payload.get("argv")
            if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
                return Decision(False, "RUN_TESTS argv must be list[str]", ())
            if not is_allowed_tests_argv(argv):
                return Decision(False, f"RUN_TESTS argv not allowlisted: {argv}", ())
            approved.append(a)

        else:
            return Decision(False, f"unknown action type: {a.type}", ())

    return Decision(True, "OK", tuple(approved))
