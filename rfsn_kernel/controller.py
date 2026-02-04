# rfsn_kernel/controller.py
"""
Kernel Controller - Executes ONLY approved kernel actions.

IMPORTANT: This controller handles file and test operations ONLY.
Web, memory, shell, and delegate actions belong to upstream (rfsn_companion).

SECURITY: Implements belt-and-suspenders validation:
- realpath containment (symlink-safe)
- read capping (memory exhaustion protection)
- tests allowlist re-check (defense in depth)
"""
from __future__ import annotations

from typing import Tuple
import os

from .types import StateSnapshot, Decision, Action, ExecResult
from .envelopes import default_envelopes
from .sandbox.sandbox_adapter import run_cmd
from .gate import is_allowed_tests_argv


# ----------------------------
# Path Security Helpers
# ----------------------------
def _resolve_under_workspace(workspace_root: str, p: str) -> str:
    """
    Normalize any path to be under workspace_root.
    Relative paths resolve against workspace_root (not CWD).
    """
    ws = os.path.abspath(workspace_root)
    if not isinstance(p, str) or not p:
        return ws
    if os.path.isabs(p):
        return os.path.abspath(p)
    return os.path.abspath(os.path.join(ws, p))


def _realpath_is_under(workspace_root: str, candidate_path: str) -> bool:
    """
    Symlink-safe containment check.
    Resolves symlinks and ensures path stays under workspace_root.
    """
    ws = os.path.realpath(os.path.abspath(workspace_root))
    cp = os.path.realpath(os.path.abspath(candidate_path))
    return cp == ws or cp.startswith(ws + os.sep)


def execute_decision(state: StateSnapshot, decision: Decision) -> Tuple[ExecResult, ...]:
    envs = default_envelopes(state.workspace_root)
    results = []

    for a in decision.approved_actions:
        spec = envs.get(a.name)
        timeout_ms = spec.max_wall_ms if spec else 30_000
        max_bytes = spec.max_bytes if spec else 1_000_000
        results.append(_execute_action(state, a, timeout_ms, max_bytes))

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


def _execute_action(state: StateSnapshot, action: Action, timeout_ms: int, max_bytes: int) -> ExecResult:
    """
    Execute a kernel-approved action with defense-in-depth security checks.
    
    Supported actions (kernel-only):
    - READ_FILE: Read file contents (capped to max_bytes)
    - WRITE_FILE: Write/create file
    - APPLY_PATCH: Apply patch (currently as file replace)
    - RUN_TESTS: Execute test suite (allowlisted argv only)
    """
    ws = os.path.abspath(state.workspace_root)

    # === READ_FILE ===
    if action.name == "READ_FILE":
        raw_path = action.args.get("path", "")
        abspath = _resolve_under_workspace(ws, raw_path)
        
        # SECURITY: realpath containment check
        if not _realpath_is_under(ws, abspath):
            return ExecResult(action=action, ok=False, stderr="path_escape", exit_code=1)
        
        try:
            # SECURITY: cap reads by envelope max_bytes
            with open(abspath, "r", encoding="utf-8") as f:
                data = f.read(max_bytes)
            return ExecResult(action=action, ok=True, stdout=data)
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    # === WRITE_FILE ===
    if action.name == "WRITE_FILE":
        raw_path = action.args.get("path", "")
        abspath = _resolve_under_workspace(ws, raw_path)
        
        # SECURITY: realpath containment check (on parent for new files)
        parent = os.path.dirname(abspath)
        if os.path.exists(abspath):
            check_path = abspath
        else:
            # For new files, check parent exists and is under workspace
            check_path = parent if os.path.exists(parent) else ws
        if not _realpath_is_under(ws, check_path):
            return ExecResult(action=action, ok=False, stderr="path_escape", exit_code=1)
        
        content = str(action.args.get("content", ""))
        try:
            os.makedirs(parent, exist_ok=True)
            with open(abspath, "w", encoding="utf-8") as f:
                f.write(content)
            return ExecResult(action=action, ok=True, stdout="WROTE_FILE")
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    # === APPLY_PATCH ===
    if action.name == "APPLY_PATCH":
        raw_path = action.args.get("path", "")
        abspath = _resolve_under_workspace(ws, raw_path)
        
        # SECURITY: realpath containment check
        parent = os.path.dirname(abspath)
        if os.path.exists(abspath):
            check_path = abspath
        else:
            check_path = parent if os.path.exists(parent) else ws
        if not _realpath_is_under(ws, check_path):
            return ExecResult(action=action, ok=False, stderr="path_escape", exit_code=1)
        
        content = str(action.args.get("content", ""))
        try:
            os.makedirs(parent, exist_ok=True)
            with open(abspath, "w", encoding="utf-8") as f:
                f.write(content)
            return ExecResult(action=action, ok=True, stdout="APPLIED_PATCH_AS_REPLACE")
        except Exception as e:
            return ExecResult(action=action, ok=False, stderr=str(e), exit_code=1)

    # === RUN_TESTS ===
    if action.name == "RUN_TESTS":
        argv = action.args.get("argv", ["python", "-m", "pytest", "-q"])
        
        # SECURITY: re-check allowlist at execution time (belt + suspenders)
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            return ExecResult(action=action, ok=False, stderr="bad_tests_argv", exit_code=1)
        if not is_allowed_tests_argv(argv):
            return ExecResult(action=action, ok=False, stderr="tests_argv_not_allowlisted", exit_code=1)
        
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

