# rfsn_kernel/gate.py
"""
Deterministic gate for RFSN kernel.

Security hardening:
- Realpath confinement (symlink escape prevention)
- Write byte caps (per-file and per-proposal)
- Nodeid file path validation (traversal rejection)
"""
from __future__ import annotations

import os
import re
from typing import List

from .types import StateSnapshot, Proposal, Action, Decision
from .patch_safety import patch_paths_are_confined


# HARD BOUNDARY: allowlist test argv (deterministic, non-interactive)
_ALLOWED_TEST_PREFIXES: List[List[str]] = [
    ["python", "-m", "pytest", "-q"],
    ["pytest", "-q"],
]

# Safe pytest nodeid pattern: path/to/file.py::ClassName::test_name
_PYTEST_NODEID_SAFE = re.compile(r"^[A-Za-z0-9_./:-]+(::[A-Za-z0-9_./:-]+)*$")

# Hard caps to prevent resource abuse
_MAX_WRITE_BYTES = 512_000          # 512 KB per WRITE_FILE
_MAX_TOTAL_WRITE_BYTES = 2_000_000  # 2 MB per proposal


def _realpath_in_workspace(workspace: str, user_path: str) -> bool:
    """
    Realpath-based confinement check.
    Prevents escaping via symlinks inside workspace.
    """
    ws = os.path.realpath(workspace)
    target = os.path.realpath(os.path.join(ws, user_path))
    try:
        return os.path.commonpath([ws, target]) == ws
    except ValueError:
        return False


def _is_confined_relative(p: str) -> bool:
    """
    Check that path is relative and has no traversal.
    """
    p = p.strip().replace("\\", "/")
    if not p:
        return False
    if p.startswith("/") or p.startswith("~"):
        return False
    if ":" in p.split("/")[0]:  # windows drive
        return False
    # Reject traversal
    segs = [s for s in p.split("/") if s not in ("", ".")]
    if any(s == ".." for s in segs):
        return False
    return True


def _validate_nodeid_path(workspace: str, nodeid: str) -> bool:
    """
    Validate pytest nodeid:
    - Must match safe pattern
    - File segment (before ::) must be confined relative path
    - File segment must resolve inside workspace (realpath)
    """
    if not _PYTEST_NODEID_SAFE.match(nodeid):
        return False
    
    # Extract file path segment (before first ::)
    file_part = nodeid.split("::", 1)[0].replace("\\", "/").strip()
    
    if not _is_confined_relative(file_part):
        return False
    
    # Realpath check
    return _realpath_in_workspace(workspace, file_part)


def is_allowed_tests_argv(argv: List[str], *, workspace: str) -> bool:
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
            # Check suffix: only safe nodeids allowed (no flags)
            suffix = norm[len(prefix):]
            # Reject anything starting with - (flags)
            if any(s.startswith("-") for s in suffix):
                return False
            # All suffix items must be validated nodeids
            if all(_validate_nodeid_path(workspace, s) for s in suffix):
                return True
    return False


def gate(state: StateSnapshot, proposal: Proposal) -> Decision:
    ws = os.path.realpath(state.workspace)

    if not os.path.isdir(ws):
        return Decision(False, f"workspace does not exist: {ws}", ())

    approved: List[Action] = []
    total_write_bytes = 0

    for a in proposal.actions:
        if a.type == "READ_FILE":
            rel = a.payload.get("path")
            if not isinstance(rel, str) or not rel:
                return Decision(False, "READ_FILE missing path", ())
            if not _is_confined_relative(rel):
                return Decision(False, f"READ_FILE path not confined: {rel}", ())
            if not _realpath_in_workspace(ws, rel):
                return Decision(False, f"READ_FILE escapes via symlink: {rel}", ())
            approved.append(a)

        elif a.type == "WRITE_FILE":
            rel = a.payload.get("path")
            text = a.payload.get("text")
            if not isinstance(rel, str) or not rel:
                return Decision(False, "WRITE_FILE missing path", ())
            if not isinstance(text, str):
                return Decision(False, "WRITE_FILE missing text", ())
            if not _is_confined_relative(rel):
                return Decision(False, f"WRITE_FILE path not confined: {rel}", ())
            if not _realpath_in_workspace(ws, rel):
                return Decision(False, f"WRITE_FILE escapes via symlink: {rel}", ())
            
            # Enforce write caps
            nbytes = len(text.encode("utf-8", errors="replace"))
            if nbytes > _MAX_WRITE_BYTES:
                return Decision(False, f"WRITE_FILE exceeds per-file cap: {nbytes} > {_MAX_WRITE_BYTES}", ())
            total_write_bytes += nbytes
            if total_write_bytes > _MAX_TOTAL_WRITE_BYTES:
                return Decision(False, f"WRITE_FILE exceeds proposal cap: {total_write_bytes} > {_MAX_TOTAL_WRITE_BYTES}", ())
            
            approved.append(a)

        elif a.type == "APPLY_PATCH":
            patch = a.payload.get("patch")
            if not isinstance(patch, str) or not patch.strip():
                return Decision(False, "APPLY_PATCH missing patch", ())
            # Hard requirement: patch paths must be parseable and confined
            ok, reason, _files = patch_paths_are_confined(ws, patch)
            if not ok:
                return Decision(False, f"APPLY_PATCH rejected: {reason}", ())
            approved.append(a)

        elif a.type == "RUN_TESTS":
            argv = a.payload.get("argv")
            if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
                return Decision(False, "RUN_TESTS argv must be list[str]", ())
            if not is_allowed_tests_argv(argv, workspace=ws):
                return Decision(False, f"RUN_TESTS argv not allowlisted: {argv}", ())
            approved.append(a)

        else:
            return Decision(False, f"unknown action type: {a.type}", ())

    return Decision(True, "OK", tuple(approved))
