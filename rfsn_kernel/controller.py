# rfsn_kernel/controller.py
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
    ws = os.path.abspath(state.workspace_root)

    # === File Operations ===
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

    # === Web Operations ===
    if action.name == "WEB_SEARCH":
        from .tools.web import web_search
        query = str(action.args.get("query", ""))
        num_results = int(action.args.get("num_results", 5))
        result = web_search(query, num_results)
        if result.error:
            return ExecResult(action=action, ok=False, stderr=result.error, exit_code=1)
        output = "\n".join([f"[{r.title}]({r.url})" for r in result.results])
        return ExecResult(action=action, ok=True, stdout=output)

    if action.name == "BROWSE_URL":
        from .tools.web import browse_url
        url = str(action.args.get("url", ""))
        max_chars = int(action.args.get("max_chars", 50_000))
        result = browse_url(url, max_chars)
        if result.error:
            return ExecResult(action=action, ok=False, stderr=result.error, exit_code=1)
        return ExecResult(action=action, ok=True, stdout=result.content)

    # === Shell Operations ===
    if action.name == "SHELL_EXEC":
        from .tools.shell import shell_exec
        command = str(action.args.get("command", ""))
        cwd = action.args.get("cwd", ws)
        timeout_sec = timeout_ms // 1000
        result = shell_exec(command, cwd=cwd, timeout_seconds=timeout_sec)
        if result.error:
            return ExecResult(action=action, ok=False, stderr=result.error, exit_code=-1)
        return ExecResult(
            action=action,
            ok=(result.exit_code == 0),
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

    # === Memory Operations ===
    if action.name == "REMEMBER":
        from .tools.memory import remember
        content = str(action.args.get("content", ""))
        metadata = action.args.get("metadata", {})
        store_path = os.path.join(ws, ".rfsn", "memory")
        result = remember(content, metadata, store_path)
        if not result.success:
            return ExecResult(action=action, ok=False, stderr=result.error or "Unknown error", exit_code=1)
        return ExecResult(action=action, ok=True, stdout=f"STORED:{result.chunk_id}")

    if action.name == "RECALL":
        from .tools.memory import recall
        query = str(action.args.get("query", ""))
        k = int(action.args.get("k", 5))
        store_path = os.path.join(ws, ".rfsn", "memory")
        result = recall(query, k, store_path)
        if result.error:
            return ExecResult(action=action, ok=False, stderr=result.error, exit_code=1)
        chunks = [f"[{c.chunk_id}] {c.content[:200]}..." for c in result.chunks]
        return ExecResult(action=action, ok=True, stdout="\n---\n".join(chunks) if chunks else "NO_MATCHES")

    # === Delegate (placeholder) ===
    if action.name == "DELEGATE":
        # Sub-agent delegation - requires full agent loop
        # For now, return a placeholder
        task = str(action.args.get("task", ""))
        return ExecResult(
            action=action,
            ok=False,
            stderr=f"DELEGATE not yet implemented. Task: {task[:100]}",
            exit_code=2,
        )

    return ExecResult(action=action, ok=False, stderr=f"unimplemented_action:{action.name}", exit_code=2)
