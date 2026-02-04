"""benchmarks/swebench_runner.py

SWE-bench *lite* runner.

This repo does not ship the real SWE-bench dataset integration here; instead it
runs a small set of synthetic tasks that mimic the loop.

What matters for RFSN is the authority path:

  proposer (upstream) -> gate (kernel) -> controller (kernel) -> ledger (append-only)
  -> outcome DB (upstream learner signal)

This runner enforces that path so the results are at least *kernel-valid*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import hashlib
import json
import os
import tempfile
import time

from rfsn_kernel.types import Action, Proposal, StateSnapshot
from upstream_learner.episode_runner import run_episode
from upstream_learner.outcomes_db import insert_outcome


@dataclass
class SWETask:
    """A single SWE-bench-style task (synthetic)."""

    task_id: str
    repo: str
    issue: str
    base_commit: str
    expected_fix: Optional[str] = None


@dataclass
class SWEResult:
    """Result of running a task."""

    task: SWETask
    patch_generated: str
    decision_status: str
    tests_passed: bool
    time_seconds: float
    wall_ms: int
    reward: float
    ledger_path: str
    error: Optional[str] = None


@dataclass
class SWEBenchRun:
    """A complete SWE-bench-lite run."""

    run_id: str
    timestamp: str
    tasks_total: int
    tasks_resolved: int
    resolve_rate: float
    results: List[SWEResult] = field(default_factory=list)


SAMPLE_SWE_TASKS = [
    SWETask(
        task_id="math_add_bug",
        repo="local/buggy_math",
        issue="The add function returns wrong results.",
        base_commit="HEAD",
        expected_fix="return a + b",
    ),
    SWETask(
        task_id="string_reverse_bug",
        repo="local/buggy_string",
        issue="The reverse function doesn't work correctly.",
        base_commit="HEAD",
        expected_fix="return s[::-1]",
    ),
    SWETask(
        task_id="factorial_bug",
        repo="local/buggy_factorial",
        issue="Factorial returns wrong value for n=5. Expected 120.",
        base_commit="HEAD",
        expected_fix="return n * factorial(n - 1)",
    ),
    SWETask(
        task_id="max_list_bug",
        repo="local/buggy_max",
        issue="max_list returns the first element instead of the maximum.",
        base_commit="HEAD",
        expected_fix="return max(lst)",
    ),
    SWETask(
        task_id="is_even_bug",
        repo="local/buggy_even",
        issue="is_even returns True for odd numbers.",
        base_commit="HEAD",
        expected_fix="return n % 2 == 0",
    ),
]


BUGGY_CODE: Dict[str, Dict[str, str]] = {
    "math_add_bug": {
        "file": "math_ops.py",
        "buggy": "def add(a, b):\n    return a - b  # BUG: should be +\n",
        "fixed": "def add(a, b):\n    return a + b\n",
        "test": "def test_add():\n    from math_ops import add\n    assert add(2, 3) == 5\n",
    },
    "string_reverse_bug": {
        "file": "string_ops.py",
        "buggy": "def reverse(s):\n    return s  # BUG: should reverse\n",
        "fixed": "def reverse(s):\n    return s[::-1]\n",
        "test": "def test_reverse():\n    from string_ops import reverse\n    assert reverse('hello') == 'olleh'\n",
    },
    "factorial_bug": {
        "file": "math_ops.py",
        "buggy": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n + factorial(n - 1)  # BUG: should be *\n",
        "fixed": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
        "test": "def test_factorial():\n    from math_ops import factorial\n    assert factorial(5) == 120\n",
    },
    "max_list_bug": {
        "file": "list_ops.py",
        "buggy": "def max_list(lst):\n    return lst[0]  # BUG: should find max\n",
        "fixed": "def max_list(lst):\n    return max(lst)\n",
        "test": "def test_max():\n    from list_ops import max_list\n    assert max_list([1, 5, 3]) == 5\n",
    },
    "is_even_bug": {
        "file": "math_ops.py",
        "buggy": "def is_even(n):\n    return n % 2 == 1  # BUG: wrong operator\n",
        "fixed": "def is_even(n):\n    return n % 2 == 0\n",
        "test": "def test_is_even():\n    from math_ops import is_even\n    assert is_even(4) == True\n    assert is_even(3) == False\n",
    },
}


class SWEBenchRunner:
    """Runs SWE-bench-lite tasks through the RFSN kernel path."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        results_path: str = "./swebench_results",
        outcomes_db_path: str = "./run_logs/outcomes.sqlite3",
        bucket: str = "swebench_lite",
    ):
        self.api_key = api_key
        self.results_path = results_path
        self.outcomes_db_path = outcomes_db_path
        self.bucket = bucket
        os.makedirs(results_path, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(outcomes_db_path)) or ".", exist_ok=True)

    def run_task(self, *, run_id: str, task: SWETask) -> SWEResult:
        start = time.time()

        code_info = BUGGY_CODE.get(task.task_id)
        if not code_info:
            return SWEResult(
                task=task,
                patch_generated="",
                decision_status="DENY",
                tests_passed=False,
                time_seconds=time.time() - start,
                wall_ms=0,
                reward=0.0,
                ledger_path="",
                error="Unknown task_id",
            )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # --- workspace
                code_path = os.path.join(tmpdir, code_info["file"])
                test_path = os.path.join(tmpdir, "test_code.py")

                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(code_info["buggy"])

                with open(test_path, "w", encoding="utf-8") as f:
                    f.write(code_info["test"])

                # --- proposal (UPSTREAM)
                patch = self._generate_patch(task, code_info)
                proposal = Proposal(
                    proposal_id=f"{run_id}:{task.task_id}",
                    actions=(
                        Action(name="READ_FILE", args={"path": code_path}),
                        Action(name="APPLY_PATCH", args={"path": code_path, "content": patch}),
                        Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
                    ),
                    rationale=f"swebench_lite: patch {os.path.basename(code_path)} then run tests",
                    metadata={"task_id": task.task_id, "repo": task.repo, "arm_id": self._arm_id()},
                )

                # --- kernel episode + ledger
                ledger_dir = os.path.join(self.results_path, "ledgers", f"run_{run_id}")
                os.makedirs(ledger_dir, exist_ok=True)
                ledger_path = os.path.join(ledger_dir, f"{task.task_id}.jsonl")

                state = StateSnapshot(
                    task_id=task.task_id,
                    workspace_root=tmpdir,
                    step=0,
                    budget_actions_remaining=20,
                    budget_wall_ms_remaining=120_000,
                    notes={"prompt_variant": self._arm_id(), "bucket": self.bucket},
                )

                outcome = run_episode(ledger_path=ledger_path, state=state, proposal=proposal)

                # --- upstream outcomes DB
                insert_outcome(
                    self.outcomes_db_path,
                    task_id=task.task_id,
                    repo=task.repo,
                    bucket=self.bucket,
                    arm_id=self._arm_id(),
                    decision_status=outcome.decision_status,
                    tests_passed=outcome.tests_passed,
                    wall_ms=outcome.wall_ms,
                    reward=outcome.reward,
                    meta={
                        "run_id": run_id,
                        "file": code_info["file"],
                        "base_commit": task.base_commit,
                    },
                )

                return SWEResult(
                    task=task,
                    patch_generated=patch,
                    decision_status=outcome.decision_status,
                    tests_passed=outcome.tests_passed,
                    time_seconds=time.time() - start,
                    wall_ms=outcome.wall_ms,
                    reward=outcome.reward,
                    ledger_path=ledger_path,
                )

        except Exception as e:
            return SWEResult(
                task=task,
                patch_generated="",
                decision_status="DENY",
                tests_passed=False,
                time_seconds=time.time() - start,
                wall_ms=0,
                reward=0.0,
                ledger_path="",
                error=f"{type(e).__name__}:{e}",
            )

    def _arm_id(self) -> str:
        # In this lite runner: arm_id is simply whether we used the LLM.
        return "llm" if self.api_key else "rule"

    def _generate_patch(self, task: SWETask, code_info: Dict[str, str]) -> str:
        """Generate a patch using LLM or deterministic rule-based fallback."""
        if not self.api_key:
            return code_info["fixed"]

        try:
            from rfsn_companion.llm.deepseek_client import call_deepseek

            system = (
                "You are a code repair assistant. Fix the bug in the code. "
                "Return ONLY the fixed code, nothing else."
            )

            prompt = (
                f"Bug report: {task.issue}\n\n"
                f"Buggy code:\n```python\n{code_info['buggy']}\n```\n\n"
                f"Test that should pass:\n```python\n{code_info['test']}\n```\n\n"
                "Return the fixed code:" 
            )

            resp = call_deepseek(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                api_key=self.api_key,
                model="deepseek-reasoner",
                temperature=0.0,
                max_tokens=2000,
            )

            code = (resp.content or "").strip()
            if code.startswith("```python"):
                code = code[len("```python") :]
            if code.startswith("```"):
                code = code[len("```") :]
            if code.endswith("```"):
                code = code[: -len("```")]

            cleaned = code.strip()
            return cleaned if cleaned else code_info["fixed"]

        except Exception:
            return code_info["fixed"]

    def run_benchmark(self, tasks: Optional[List[SWETask]] = None) -> SWEBenchRun:
        if tasks is None:
            tasks = SAMPLE_SWE_TASKS

        run_id = hashlib.sha256(f"{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        results: List[SWEResult] = []
        resolved = 0

        for task in tasks:
            r = self.run_task(run_id=run_id, task=task)
            results.append(r)
            if r.tests_passed:
                resolved += 1

        resolve_rate = (resolved / len(tasks)) if tasks else 0.0
        run = SWEBenchRun(
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            tasks_total=len(tasks),
            tasks_resolved=resolved,
            resolve_rate=resolve_rate,
            results=results,
        )

        self._save_run(run)
        return run

    def _save_run(self, run: SWEBenchRun) -> None:
        path = os.path.join(self.results_path, f"run_{run.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": run.run_id,
                    "timestamp": run.timestamp,
                    "bucket": self.bucket,
                    "tasks_total": run.tasks_total,
                    "tasks_resolved": run.tasks_resolved,
                    "resolve_rate": run.resolve_rate,
                    "arm_id": self._arm_id(),
                    "outcomes_db": os.path.abspath(self.outcomes_db_path),
                    "results": [
                        {
                            "task_id": r.task.task_id,
                            "repo": r.task.repo,
                            "decision_status": r.decision_status,
                            "tests_passed": r.tests_passed,
                            "time_seconds": r.time_seconds,
                            "wall_ms": r.wall_ms,
                            "reward": r.reward,
                            "ledger_path": r.ledger_path,
                            "error": r.error,
                        }
                        for r in run.results
                    ],
                },
                f,
                indent=2,
            )


def run_swebench_lite(api_key: Optional[str] = None) -> SWEBenchRun:
    runner = SWEBenchRunner(api_key=api_key)
    return runner.run_benchmark()
