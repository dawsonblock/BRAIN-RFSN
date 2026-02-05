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
from typing import Any, Dict, List, Optional, Tuple

from .types import StateSnapshot, Decision, ExecResult, verify_decision_sig
from .gate import is_allowed_tests_argv
from .patch_safety import patch_paths_are_confined


_MAX_READ_BYTES = 512_000
_MAX_WRITE_BYTES = 512_000
_MAX_TEST_OUTPUT_CHARS = 120_000
_MAX_GREP_RESULTS = 100
_MAX_GREP_OUTPUT_BYTES = 512_000
_MAX_LIST_DIR_ENTRIES = 500
_MAX_GIT_DIFF_BYTES = 512_000

# Test execution mode:
# - "host": run pytest on host (default)
# - "docker": run pytest inside docker sandbox (if available)
#
# Set globally via env:
#   RFSN_TEST_MODE=host|docker
#
# Or per action with:
#   Action("RUN_TESTS", {"argv":[...], "mode":"docker"})
_DEFAULT_TEST_MODE = (os.environ.get("RFSN_TEST_MODE") or "host").strip().lower()


def _get_test_mode(payload: Dict[str, Any]) -> str:
    """Get test execution mode from action payload or default."""
    m = payload.get("mode")
    if isinstance(m, str) and m.strip():
        return m.strip().lower()
    return _DEFAULT_TEST_MODE


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


def _run_tests(
    workspace: str,
    argv: List[str],
    timeout_s: int = 600,
    mode: str = "host",
) -> Dict[str, Any]:
    """
    Execute tests with configurable execution mode.

    Args:
        workspace: Path to workspace
        argv: Test command, e.g. ["pytest", "-q"]
        timeout_s: Timeout in seconds
        mode: "host" (default) or "docker" for sandboxed execution

    Returns:
        Dict with ok, returncode, stdout, stderr, mode
    """
    if not is_allowed_tests_argv(argv, workspace=workspace):
        raise RuntimeError("RUN_TESTS argv failed allowlist re-check")

    ws = os.path.realpath(workspace)

    if mode == "docker":
        # Lazy import to avoid breaking host-only deployments
        try:
            from docker_runner import run_tests_sandboxed
        except ImportError as e:
            return {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Docker mode unavailable: {e}",
                "mode": "docker",
            }

        result = run_tests_sandboxed(
            workspace=ws,
            argv=argv,
            timeout_s=timeout_s,
        )
        # Ensure caps on output
        result["stdout"] = _tail(result.get("stdout", ""), _MAX_TEST_OUTPUT_CHARS)
        result["stderr"] = _tail(result.get("stderr", ""), _MAX_TEST_OUTPUT_CHARS)
        result["mode"] = "docker"
        return result
    else:
        # Host mode (default)
        proc = subprocess.run(
            argv,
            cwd=ws,
            capture_output=True,
            timeout=timeout_s,
        )
        return {
            "returncode": proc.returncode,
            "stdout": _tail(proc.stdout.decode("utf-8", errors="replace"), _MAX_TEST_OUTPUT_CHARS),
            "stderr": _tail(proc.stderr.decode("utf-8", errors="replace"), _MAX_TEST_OUTPUT_CHARS),
            "ok": proc.returncode == 0,
            "mode": "host",
        }


def _grep(
    workspace: str,
    pattern: str,
    path: str = ".",
    fixed_string: bool = False,
) -> Dict[str, Any]:
    """
    Safe grep with caps and directory exclusions.

    Args:
        workspace: Workspace path
        pattern: Search pattern
        path: Relative path to search in (default ".")
        fixed_string: If True, use fixed-string matching (-F) instead of regex (-E)

    Returns:
        Dict with ok, pattern, path, matches, count, truncated
    """
    ws = os.path.realpath(workspace)
    target = os.path.join(ws, path) if path != "." else ws

    # Build command
    cmd = ["grep", "-rn"]

    # Fixed-string vs regex mode
    if fixed_string:
        cmd.append("-F")
    else:
        cmd.append("-E")

    # File type includes (code + config + docs)
    includes = [
        "*.py", "*.txt", "*.md", "*.rst",
        "*.json", "*.yaml", "*.yml", "*.toml",
        "*.js", "*.ts", "*.jsx", "*.tsx",
        "*.java", "*.go", "*.rs", "*.c", "*.h", "*.cpp",
        "*.html", "*.css", "*.sh",
    ]
    for inc in includes:
        cmd.append(f"--include={inc}")

    # Directory excluses (noise + security)
    excludes = [
        ".git", "__pycache__", "node_modules",
        ".venv", "venv", ".env",
        "dist", "build", ".next", ".cache",
        "coverage", "htmlcov", ".pytest_cache",
        ".mypy_cache", ".ruff_cache",
    ]
    for exc in excludes:
        cmd.append(f"--exclude-dir={exc}")

    cmd.append(pattern)
    cmd.append(target)

    try:
        proc = subprocess.run(
            cmd,
            cwd=ws,
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "grep timeout", "matches": []}

    raw = proc.stdout.decode("utf-8", errors="replace")
    # Cap output
    if len(raw) > _MAX_GREP_OUTPUT_BYTES:
        raw = raw[:_MAX_GREP_OUTPUT_BYTES] + "\n[truncated]"

    # Parse lines and cap results
    lines = raw.strip().split("\n") if raw.strip() else []
    lines = lines[:_MAX_GREP_RESULTS]

    return {
        "ok": True,
        "pattern": pattern,
        "path": path,
        "fixed_string": fixed_string,
        "matches": lines,
        "count": len(lines),
        "truncated": len(lines) >= _MAX_GREP_RESULTS,
    }


def _list_dir(workspace: str, path: str = ".") -> Dict[str, Any]:
    """
    Safe directory listing with caps.
    No recursive, max entries capped.
    """
    ws = os.path.realpath(workspace)
    target = os.path.join(ws, path) if path != "." else ws
    
    if not os.path.isdir(target):
        return {"ok": False, "error": f"not a directory: {path}", "entries": []}
    
    try:
        entries = os.listdir(target)
    except OSError as e:
        return {"ok": False, "error": str(e), "entries": []}
    
    # Cap entries
    entries = sorted(entries)[:_MAX_LIST_DIR_ENTRIES]
    
    # Add type info
    result = []
    for name in entries:
        full = os.path.join(target, name)
        entry: Dict[str, Any] = {"name": name}
        try:
            if os.path.isdir(full):
                entry["type"] = "dir"
            elif os.path.isfile(full):
                entry["type"] = "file"
                entry["size"] = os.path.getsize(full)
            else:
                entry["type"] = "other"
        except OSError:
            entry["type"] = "unknown"
        result.append(entry)
    
    return {
        "ok": True,
        "path": path,
        "entries": result,
        "count": len(result),
        "truncated": len(entries) >= _MAX_LIST_DIR_ENTRIES,
    }


def _git_diff(
    workspace: str,
    paths: Optional[List[str]] = None,
    context_lines: int = 3,
) -> Dict[str, Any]:
    """
    Safe git diff with output cap and bounded context.
    
    Args:
        workspace: Path to git repo
        paths: Optional list of paths to restrict diff to
        context_lines: Number of context lines (0-10, default 3, use 1 for minimal)
    
    Returns current uncommitted changes.
    """
    ws = os.path.realpath(workspace)
    paths = paths or []
    
    if not os.path.isdir(os.path.join(ws, ".git")):
        return {"ok": False, "error": "not a git repo", "diff": ""}
    
    # Build git diff command with bounded context
    cmd = ["git", "diff", f"-U{context_lines}"]
    
    # Add paths if specified (already validated by gate)
    if paths:
        cmd.append("--")
        cmd.extend(paths)
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=ws,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git diff timeout", "diff": ""}
    
    diff = proc.stdout.decode("utf-8", errors="replace")
    
    # Truncate if too large
    truncated = False
    if len(diff) > _MAX_GIT_DIFF_BYTES:
        diff = diff[:_MAX_GIT_DIFF_BYTES] + "\n[truncated]"
        truncated = True
    
    return {
        "ok": True,
        "diff": diff,
        "returncode": proc.returncode,
        "paths": paths,
        "context_lines": context_lines,
        "truncated": truncated,
    }


def execute_decision(state: StateSnapshot, decision: Decision) -> Tuple[ExecResult, ...]:
    # CRITICAL: Verify decision was created by gate (prevents forged decisions)
    if not verify_decision_sig(decision):
        raise RuntimeError("SECURITY: Decision signature invalid - gate is FINAL AUTHORITY")
    
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
            mode = _get_test_mode(a.payload)
            out = _run_tests(ws, a.payload["argv"], mode=mode)
            results.append(ExecResult(bool(out.get("ok")), a, out))

        elif a.type == "GREP":
            pattern = a.payload["pattern"]
            path = a.payload.get("path", ".")
            fixed_string = bool(a.payload.get("fixed_string", False))
            # Defense in depth: validate path again
            if path != ".":
                if not _is_confined_relative(path):
                    raise RuntimeError(f"GREP path not confined: {path}")
                if not _realpath_in_workspace(ws, path):
                    raise RuntimeError(f"GREP path escapes via symlink: {path}")
            out = _grep(ws, pattern, path, fixed_string=fixed_string)
            results.append(ExecResult(bool(out.get("ok")), a, out))

        elif a.type == "LIST_DIR":
            path = a.payload.get("path", ".")
            if path != ".":
                if not _is_confined_relative(path):
                    raise RuntimeError(f"LIST_DIR path not confined: {path}")
                if not _realpath_in_workspace(ws, path):
                    raise RuntimeError(f"LIST_DIR path escapes via symlink: {path}")
            out = _list_dir(ws, path)
            results.append(ExecResult(bool(out.get("ok")), a, out))

        elif a.type == "GIT_DIFF":
            paths = a.payload.get("paths", [])
            context_lines = a.payload.get("context_lines", 3)
            out = _git_diff(ws, paths=paths, context_lines=context_lines)
            results.append(ExecResult(bool(out.get("ok")), a, out))

        else:
            results.append(ExecResult(False, a, {"error": "unknown action type"}))

    return tuple(results)
