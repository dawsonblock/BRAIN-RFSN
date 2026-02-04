# rfsn_kernel/controller.py
from __future__ import annotations

from typing import Tuple, Dict, Any, List
import os
import subprocess

from .types import StateSnapshot, Decision, Action, ExecResult
from .gate import is_allowed_tests_argv


def _abspath(workspace: str, p: str) -> str:
    return os.path.abspath(os.path.join(workspace, p))


def _is_in_workspace(workspace: str, abs_path: str) -> bool:
    ws = os.path.abspath(workspace)
    ap = os.path.abspath(abs_path)
    try:
        common = os.path.commonpath([ws, ap])
    except ValueError:
        return False
    return common == ws


def _read_file(path: str, cap_bytes: int = 512_000) -> str:
    with open(path, "rb") as f:
        data = f.read(cap_bytes + 1)
    if len(data) > cap_bytes:
        raise RuntimeError(f"read cap exceeded: {cap_bytes} bytes")
    return data.decode("utf-8", errors="replace")


def _write_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _apply_patch_minimal(workspace: str, patch: str) -> Dict[str, Any]:
    """
    Minimal safe patching:
    - only supports unified diff against files inside workspace
    - calls `git apply` with strict flags if git exists
    """
    ws = os.path.abspath(workspace)
    if not os.path.isdir(os.path.join(ws, ".git")):
        return {"applied": False, "reason": "workspace is not a git repo (.git missing)"}

    # defense-in-depth: disallow patch that mentions absolute paths
    for bad in ("/", "\\"):
        if "\n--- " + bad in patch or "\n+++ " + bad in patch:
            return {"applied": False, "reason": "patch contains absolute paths"}

    proc = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "--reject", "--recount", "-"],
        input=patch.encode("utf-8", errors="replace"),
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "applied": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.decode("utf-8", errors="replace")[-4000:],
        "stderr": proc.stderr.decode("utf-8", errors="replace")[-4000:],
    }


def _run_tests(workspace: str, argv: List[str], timeout_s: int = 600) -> Dict[str, Any]:
    if not is_allowed_tests_argv(argv):
        raise RuntimeError("RUN_TESTS argv failed allowlist re-check")
    ws = os.path.abspath(workspace)
    proc = subprocess.run(
        argv,
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.decode("utf-8", errors="replace")[-8000:],
        "stderr": proc.stderr.decode("utf-8", errors="replace")[-8000:],
        "ok": proc.returncode == 0,
    }


def execute_decision(state: StateSnapshot, decision: Decision) -> Tuple[ExecResult, ...]:
    if not decision.allowed:
        raise RuntimeError(f"decision denied: {decision.reason}")

    ws = os.path.abspath(state.workspace)
    results: list[ExecResult] = []

    for a in decision.approved_actions:
        if a.type == "READ_FILE":
            rel = a.payload["path"]
            ap = _abspath(ws, rel)
            if not _is_in_workspace(ws, ap):
                raise RuntimeError(f"READ_FILE escapes workspace: {rel}")
            text = _read_file(ap)
            results.append(ExecResult(True, a, {"path": rel, "text": text}))

        elif a.type == "WRITE_FILE":
            rel = a.payload["path"]
            ap = _abspath(ws, rel)
            if not _is_in_workspace(ws, ap):
                raise RuntimeError(f"WRITE_FILE escapes workspace: {rel}")
            _write_file(ap, a.payload["text"])
            results.append(ExecResult(True, a, {"path": rel, "written": True}))

        elif a.type == "APPLY_PATCH":
            out = _apply_patch_minimal(ws, a.payload["patch"])
            results.append(ExecResult(bool(out.get("applied")), a, out))

        elif a.type == "RUN_TESTS":
            out = _run_tests(ws, a.payload["argv"])
            results.append(ExecResult(bool(out.get("ok")), a, out))

        else:
            results.append(ExecResult(False, a, {"error": "unknown action type"}))

    return tuple(results)
