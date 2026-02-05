# rfsn_kernel/controller.py
"""
Execute approved actions from the gate.

Security hardening:
- Realpath confinement checks (defense in depth)
- Write byte caps
- git apply --check before apply (no .rej pollution)
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Tuple

from .types import StateSnapshot, Decision, ExecResult
from .gate import is_allowed_tests_argv
from .patch_safety import patch_paths_are_confined


_MAX_READ_BYTES = 512_000
_MAX_WRITE_BYTES = 512_000
_MAX_TEST_OUTPUT_CHARS = 120_000


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
    """Check that path is relative and has no traversal."""
    p = p.strip().replace("\\", "/")
    if not p:
        return False
    if p.startswith("/") or p.startswith("~"):
        return False
    if ":" in p.split("/")[0]:
        return False
    segs = [s for s in p.split("/") if s not in ("", ".")]
    if any(s == ".." for s in segs):
        return False
    return True


def _tail(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[-n:]


def _read_file(path: str, cap_bytes: int = _MAX_READ_BYTES) -> str:
    with open(path, "rb") as f:
        data = f.read(cap_bytes + 1)
    if len(data) > cap_bytes:
        raise RuntimeError(f"read cap exceeded: {cap_bytes} bytes")
    return data.decode("utf-8", errors="replace")


def _write_file(path: str, text: str, cap_bytes: int = _MAX_WRITE_BYTES) -> int:
    nbytes = len(text.encode("utf-8", errors="replace"))
    if nbytes > cap_bytes:
        raise RuntimeError(f"write cap exceeded: {nbytes} > {cap_bytes}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return nbytes


def _apply_patch_minimal(workspace: str, patch: str) -> Dict[str, Any]:
    """
    Minimal safe patching:
    - Only supports unified diff against files inside workspace
    - Uses git apply --check first to avoid .rej pollution
    - Calls git apply only if check passes
    """
    ws = os.path.realpath(workspace)
    if not os.path.isdir(os.path.join(ws, ".git")):
        return {"applied": False, "reason": "workspace is not a git repo (.git missing)"}

    # Defense-in-depth: parse diff headers and enforce confinement
    ok, reason, files = patch_paths_are_confined(ws, patch)
    if not ok:
        return {"applied": False, "reason": f"patch rejected: {reason}"}

    # First: verify patch applies cleanly (no .rej files)
    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", "-"],
        input=patch.encode("utf-8", errors="replace"),
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check.returncode != 0:
        return {
            "applied": False,
            "reason": "patch failed git apply --check",
            "returncode": check.returncode,
            "stdout": _tail(check.stdout.decode("utf-8", errors="replace"), 4000),
            "stderr": _tail(check.stderr.decode("utf-8", errors="replace"), 4000),
            "touched_files": [{"old": f.old_path, "new": f.new_path} for f in files],
        }

    # Apply cleanly (no --reject)
    proc = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        input=patch.encode("utf-8", errors="replace"),
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "applied": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": _tail(proc.stdout.decode("utf-8", errors="replace"), 4000),
        "stderr": _tail(proc.stderr.decode("utf-8", errors="replace"), 4000),
        "touched_files": [{"old": f.old_path, "new": f.new_path} for f in files],
    }


def _run_tests(workspace: str, argv: List[str], timeout_s: int = 600) -> Dict[str, Any]:
    if not is_allowed_tests_argv(argv, workspace=workspace):
        raise RuntimeError("RUN_TESTS argv failed allowlist re-check")
    ws = os.path.realpath(workspace)
    proc = subprocess.run(
        argv,
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
    )
    return {
        "returncode": proc.returncode,
        "stdout": _tail(proc.stdout.decode("utf-8", errors="replace"), _MAX_TEST_OUTPUT_CHARS),
        "stderr": _tail(proc.stderr.decode("utf-8", errors="replace"), _MAX_TEST_OUTPUT_CHARS),
        "ok": proc.returncode == 0,
    }


def execute_decision(state: StateSnapshot, decision: Decision) -> Tuple[ExecResult, ...]:
    if not decision.allowed:
        raise RuntimeError(f"decision denied: {decision.reason}")

    ws = os.path.realpath(state.workspace)
    results: List[ExecResult] = []

    for a in decision.approved_actions:
        if a.type == "READ_FILE":
            rel = a.payload["path"]
            if not _is_confined_relative(rel):
                raise RuntimeError(f"READ_FILE path not confined: {rel}")
            if not _realpath_in_workspace(ws, rel):
                raise RuntimeError(f"READ_FILE escapes via symlink: {rel}")
            ap = os.path.join(ws, rel)
            text = _read_file(ap)
            results.append(ExecResult(True, a, {"path": rel, "text": text}))

        elif a.type == "WRITE_FILE":
            rel = a.payload["path"]
            text = a.payload["text"]
            if not _is_confined_relative(rel):
                raise RuntimeError(f"WRITE_FILE path not confined: {rel}")
            if not _realpath_in_workspace(ws, rel):
                raise RuntimeError(f"WRITE_FILE escapes via symlink: {rel}")
            ap = os.path.join(ws, rel)
            nbytes = _write_file(ap, text)
            results.append(ExecResult(True, a, {"path": rel, "bytes": nbytes}))

        elif a.type == "APPLY_PATCH":
            out = _apply_patch_minimal(ws, a.payload["patch"])
            results.append(ExecResult(bool(out.get("applied")), a, out))

        elif a.type == "RUN_TESTS":
            out = _run_tests(ws, a.payload["argv"])
            results.append(ExecResult(bool(out.get("ok")), a, out))

        else:
            results.append(ExecResult(False, a, {"error": "unknown action type"}))

    return tuple(results)
