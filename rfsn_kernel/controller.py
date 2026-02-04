# rfsn_kernel/controller.py
"""
Kernel Controller - Executes ONLY approved kernel actions.

IMPORTANT: This controller handles file and test operations ONLY.
Web, memory, shell, and delegate actions belong to upstream (rfsn_companion).
"""
from __future__ import annotations

from typing import Tuple
import os

from .types import StateSnapshot, Decision, Action, ExecResult
from .envelopes import default_envelopes
from .sandbox.sandbox_adapter import run_cmd


def execute_decision(state: StateSnapshot, decision: Decision) -> Tuple[ExecResult, ...]:
    envs = default_envelopes(state.workspace_root)
    results = []

    for a in decision.approved_actions:
        spec = envs.get(a.name)
        timeout_ms = spec.max_wall_ms if spec else 30_000
        results.append(_execute_action(state, a, timeout_ms))

    return tuple(results)


def _write_last_tests_artifact(workspace_root: str, stdout: str, stderr: str) -> None:
    ws = os.path.abspath(workspace_root)
    out_dir = os.path.join(ws, ".rfsn")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "last_tests.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(stdout or "")
        f.write("\n\n=== STDERR ===\n")
        f.write(stderr or "")
        f.write("\n")


def _execute_action(state: StateSnapshot, action: Action, timeout_ms: int) -> ExecResult:
    """
    Execute a kernel-approved action.
    
    Supported actions (kernel-only):
    - READ_FILE: Read file contents
    - WRITE_FILE: Write/create file
    - APPLY_PATCH: Apply patch (currently as file replace)
    - RUN_TESTS: Execute test suite
    """
    ws = os.path.abspath(state.workspace_root)

    # === File Operations (Kernel-Only) ===
    if action.name == "READ_FILE":
        path = os.path.abspath(action.args["path"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ExecResult(action=action, ok=True, stdout=f.read())
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    if action.name == "WRITE_FILE":
        path = os.path.abspath(action.args["path"])
        content = str(action.args.get("content", ""))
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ExecResult(action=action, ok=True, stdout="WROTE_FILE")
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    if action.name == "APPLY_PATCH":
        path = os.path.abspath(action.args["path"])
        content = str(action.args.get("content", ""))
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ExecResult(action=action, ok=True, stdout="APPLIED_PATCH_AS_REPLACE")
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    if action.name == "RUN_TESTS":
        argv = action.args.get("argv", ["python", "-m", "pytest", "-q"])
        out = run_cmd(argv=argv, cwd=ws, timeout_ms=timeout_ms)
        _write_last_tests_artifact(ws, out.get("stdout", ""), out.get("stderr", ""))
        return ExecResult(
            action=action,
            ok=bool(out.get("ok", False)),
            stdout=str(out.get("stdout", "")),
            stderr=str(out.get("stderr", "")),
            exit_code=int(out.get("exit_code", 0)),
            duration_ms=int(out.get("duration_ms", 0)),
            artifacts=dict(out.get("artifacts", {})),
        )

    # NOTE: WEB_SEARCH, BROWSE_URL, SHELL_EXEC, REMEMBER, RECALL, DELEGATE
    # are NOT kernel actions. They have been moved to upstream (rfsn_companion).
    # If we reach here, the gate should have already denied the action.

    return ExecResult(action=action, ok=False, stderr=f"unimplemented_action:{action.name}", exit_code=2)
