"""
SWE-bench-ish harness skeleton that:
- Loads tasks from a SWE-bench JSON/JSONL file
- Checks out the target repo at base commit into a fresh workspace
- Runs your existing LLM repair loop (rfsn_swe_agent.py) against that workspace
- Captures artifacts (ledger, patch attempts, logs)
- Emits a machine-readable report JSON

This is NOT full SWE-bench parity (env/image/deps/scoring differ). It is the missing harness spine.
You can bolt on dockerized env parity later without changing the kernel boundary.

Assumptions:
- You have git installed
- The target repo is reachable (local path or clone URL)
- Your rfsn_swe_agent.py uses the kernel gate+controller and writes a ledger

Example:
  export LLM_API_KEY="..."
  export LLM_MODEL="gpt-4.1-mini"
  export LLM_BASE_URL="https://api.openai.com/v1/chat/completions"

  python swebench_runner.py \\
    --tasks ./swebench_tasks.jsonl \\
    --out ./swebench_runs \\
    --max-tasks 5 \\
    --attempts 8 \\
    --timeout-s 900 \\
    --verbose
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from swebench_tasks import load_tasks, normalize_task
from swebench_utils import (
    ensure_empty_dir,
    run_cmd,
    sha256_file,
    safe_write_text,
    utc_ts,
)


@dataclass
class TaskRunResult:
    task_id: str
    repo: str
    base_commit: str
    workspace_dir: str
    ok: bool
    returncode: int
    wall_s: float
    agent_stdout_tail: str
    agent_stderr_tail: str
    ledger_sha256: Optional[str]
    notes: Dict[str, Any]


def clone_or_copy_repo(repo: str, dest: Path, *, verbose: bool = False) -> None:
    """
    repo can be:
      - a local path to a git repo
      - a clone URL (https/ssh)
    """
    if Path(repo).exists():
        # Copy is faster for local repos but must keep .git.
        if verbose:
            print(f"[repo] copying local repo {repo} -> {dest}")
        shutil.copytree(repo, dest, symlinks=True)
        return

    if verbose:
        print(f"[repo] cloning {repo} -> {dest}")
    run_cmd(["git", "clone", "--no-tags", "--depth", "1", repo, str(dest)], cwd=None)


def checkout_commit(workspace: Path, commit: str) -> None:
    run_cmd(["git", "fetch", "--all", "--tags"], cwd=str(workspace))
    run_cmd(["git", "checkout", "--force", commit], cwd=str(workspace))
    # Ensure clean state
    run_cmd(["git", "clean", "-fdx"], cwd=str(workspace))


def run_agent(
    *,
    agent_py: str,
    workspace: Path,
    task_id: str,
    attempts: int,
    timeout_s: int,
    run_dir: Path,
    verbose: bool,
) -> Tuple[int, str, str]:
    """
    Calls rfsn_swe_agent.py in a subprocess so the harness can enforce timeouts
    and capture logs without modifying the agent.
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Force agent logs into this run_dir
    env["RFSN_RUN_DIR"] = str(run_dir)  # optional; agent can ignore
    ledger_path = run_dir / "ledger.jsonl"
    env["RFSN_LEDGER_PATH"] = str(ledger_path)  # optional; agent can ignore

    cmd = [
        sys.executable,
        agent_py,
        "--workspace",
        str(workspace),
        "--task-id",
        task_id,
        "--attempts",
        str(attempts),
        "--ledger",
        str(ledger_path),
        "--bandit-path",
        str(run_dir / "bandit.json"),
    ]
    if verbose:
        cmd.append("--verbose")

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(Path(agent_py).parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
    )
    wall = time.perf_counter() - t0

    # Store full stdout/stderr
    safe_write_text(run_dir / "agent_stdout.txt", proc.stdout.decode("utf-8", errors="replace"))
    safe_write_text(run_dir / "agent_stderr.txt", proc.stderr.decode("utf-8", errors="replace"))
    safe_write_text(run_dir / "agent_wall_s.txt", f"{wall:.6f}\n")

    # Tail for report
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    out_tail = out[-120_000:] if len(out) > 120_000 else out
    err_tail = err[-120_000:] if len(err) > 120_000 else err
    return proc.returncode, out_tail, err_tail


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True, help="Path to SWE-bench tasks JSON or JSONL")
    ap.add_argument("--out", required=True, help="Output directory for run artifacts")
    ap.add_argument("--max-tasks", type=int, default=0, help="0 = all")
    ap.add_argument("--attempts", type=int, default=8)
    ap.add_argument("--timeout-s", type=int, default=900)
    ap.add_argument("--agent", default="rfsn_swe_agent.py", help="Path to agent entrypoint")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks_raw = load_tasks(Path(args.tasks))
    tasks = [normalize_task(t) for t in tasks_raw]
    if args.max_tasks and args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    run_meta = {
        "created_utc": utc_ts(),
        "tasks_path": str(Path(args.tasks).resolve()),
        "agent": str(Path(args.agent).resolve()),
        "attempts": args.attempts,
        "timeout_s": args.timeout_s,
        "n_tasks": len(tasks),
        "env": {
            "LLM_MODEL": os.environ.get("LLM_MODEL"),
            "LLM_BASE_URL": os.environ.get("LLM_BASE_URL"),
        },
    }
    safe_write_text(out_dir / "RUN_META.json", json.dumps(run_meta, indent=2, sort_keys=True))

    results: List[TaskRunResult] = []

    for i, t in enumerate(tasks, start=1):
        task_id = t["task_id"]
        repo = t["repo"]
        base_commit = t["base_commit"]

        run_dir = out_dir / f"{i:05d}_{task_id}"
        ensure_empty_dir(run_dir)

        if args.verbose:
            print(f"\n=== [{i}/{len(tasks)}] task_id={task_id} repo={repo} base={base_commit} ===")

        workspace = run_dir / "workspace"
        ensure_empty_dir(workspace)

        try:
            clone_or_copy_repo(repo, workspace, verbose=args.verbose)
            checkout_commit(workspace, base_commit)

            rc, out_tail, err_tail = run_agent(
                agent_py=str(Path(args.agent).resolve()),
                workspace=workspace,
                task_id=task_id,
                attempts=args.attempts,
                timeout_s=args.timeout_s,
                run_dir=run_dir,
                verbose=args.verbose,
            )

            # Heuristic ok flag: agent returncode 0 means tests passing at end (your agent uses that)
            ok = (rc == 0)

            ledger = run_dir / "ledger.jsonl"
            ledger_hash = sha256_file(ledger) if ledger.exists() else None

            wall_s = float((run_dir / "agent_wall_s.txt").read_text().strip())

            res = TaskRunResult(
                task_id=task_id,
                repo=repo,
                base_commit=base_commit,
                workspace_dir=str(workspace),
                ok=ok,
                returncode=rc,
                wall_s=wall_s,
                agent_stdout_tail=out_tail,
                agent_stderr_tail=err_tail,
                ledger_sha256=ledger_hash,
                notes={"index": i},
            )
            results.append(res)

            safe_write_text(run_dir / "RESULT.json", json.dumps(asdict(res), indent=2, sort_keys=True))

        except subprocess.TimeoutExpired:
            res = TaskRunResult(
                task_id=task_id,
                repo=repo,
                base_commit=base_commit,
                workspace_dir=str(workspace),
                ok=False,
                returncode=124,
                wall_s=float(args.timeout_s),
                agent_stdout_tail="",
                agent_stderr_tail="timeout",
                ledger_sha256=None,
                notes={"error": "timeout"},
            )
            results.append(res)
            safe_write_text(run_dir / "RESULT.json", json.dumps(asdict(res), indent=2, sort_keys=True))

        except Exception as e:
            res = TaskRunResult(
                task_id=task_id,
                repo=repo,
                base_commit=base_commit,
                workspace_dir=str(workspace),
                ok=False,
                returncode=2,
                wall_s=0.0,
                agent_stdout_tail="",
                agent_stderr_tail=str(e),
                ledger_sha256=None,
                notes={"error": "exception"},
            )
            results.append(res)
            safe_write_text(run_dir / "RESULT.json", json.dumps(asdict(res), indent=2, sort_keys=True))

    # Summary report
    solved = sum(1 for r in results if r.ok)
    total = len(results)
    summary = {
        "created_utc": utc_ts(),
        "total": total,
        "solved": solved,
        "solve_rate": (solved / total) if total else 0.0,
        "results": [asdict(r) for r in results],
    }
    safe_write_text(out_dir / "SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True))

    if args.verbose:
        print(f"\n[summary] solved={solved}/{total} ({summary['solve_rate']:.3f}) artifacts={out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
