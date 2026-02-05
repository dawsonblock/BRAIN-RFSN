# rfsn_swe_agent.py
"""
Minimal "make it real" loop for this repo:

- Uses the existing kernel gate + controller + ledger
- Runs tests, parses failing paths from output
- Reads a small context pack via gated READ_FILE actions
- Calls an external LLM (configurable) to generate a unified diff
- Applies patch via gated APPLY_PATCH, re-runs tests
- Repeats for N attempts

This is intentionally small and strict. It will not score well on SWE-bench yet,
but it creates the missing spine: (harness-ish loop + proposer + context pack).

Usage (local repo already checked out into --workspace):

  python rfsn_swe_agent.py --workspace /path/to/repo --task-id demo --attempts 6 --verbose

LLM config (OpenAI-compatible JSON API by default):
  export LLM_API_KEY="..."
  export LLM_MODEL="gpt-4.1-mini"
  export LLM_BASE_URL="https://api.openai.com/v1/chat/completions"
"""
from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from rfsn_kernel.types import Action, Decision, ExecResult, Proposal, StateSnapshot
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.replay import verify_ledger_chain

from upstream_learner.bandit import ThompsonBandit
from upstream_learner.policy_executor import PolicyExecutor

from rfsn_swe_llm import LLMClient, extract_unified_diff
from context_builder import build_context_pack, format_context_pack


# --------- small utilities ---------

_TRACEBACK_FILE_RE = re.compile(r'File "([^"]+)", line (\d+), in ([^\n]+)')
_PYTEST_NODEID_RE = re.compile(r"^(.+::.+)$", re.MULTILINE)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _cap(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + "\n[...truncated...]"


def _is_rel_path(p: str) -> bool:
    p = p.strip().replace("\\", "/")
    if p.startswith("/"):
        return False
    if ":" in p.split("/")[0]:  # windows drive
        return False
    return True


def parse_hot_paths(test_output: str, *, limit: int = 14) -> List[str]:
    """
    Extract likely relevant file paths from tracebacks.
    Keeps only relative paths (workspace-confined).
    """
    seen: List[str] = []
    for m in _TRACEBACK_FILE_RE.finditer(test_output):
        raw = m.group(1).strip()
        if not _is_rel_path(raw):
            continue
        if raw not in seen:
            seen.append(raw)
        if len(seen) >= limit:
            break
    return seen


def parse_pytest_focus_nodeids(test_output: str, *, limit: int = 6) -> List[str]:
    """
    Heuristic: look for failing nodeids in output.
    If we find any, we can run a narrower pytest invocation later.
    """
    found: List[str] = []
    for m in _PYTEST_NODEID_RE.finditer(test_output):
        nodeid = m.group(1).strip()
        if "::" in nodeid and nodeid not in found:
            found.append(nodeid)
        if len(found) >= limit:
            break
    return found


def build_prompt(
    *,
    task_id: str,
    test_stdout: str,
    test_stderr: str,
    context_pack_text: str,
    instruction_suffix: str = "",
) -> str:
    """
    The prompt is deliberately rigid:
    - Provide failing output
    - Provide context pack (built by context_builder)
    - Demand a unified diff only
    """
    parts: List[str] = []
    parts.append(f"Task: Fix failing tests for task_id={task_id}.")
    parts.append("")
    parts.append("You must output ONLY a unified diff (git-style) that applies cleanly with `git apply`.")
    parts.append("No commentary. No Markdown fences. Just the diff.")
    if instruction_suffix:
        parts.append(instruction_suffix)
    parts.append("")
    parts.append("=== PYTEST STDOUT (tail) ===")
    parts.append(_cap(test_stdout, 8000))
    parts.append("")
    parts.append("=== PYTEST STDERR (tail) ===")
    parts.append(_cap(test_stderr, 8000))
    parts.append("")
    parts.append(context_pack_text)
    return "\n".join(parts)


# --------- gated step runner ---------

@dataclass(frozen=True)
class StepOutcome:
    decision: Decision
    results: Tuple[ExecResult, ...]
    wall_ms: int


def run_step(*, ledger_path: str, state: StateSnapshot, proposal: Proposal) -> StepOutcome:
    """
    Like upstream_learner.episode.run_episode, but returns results so upstream can use outputs.
    Still logs the full step to the ledger.
    """
    t0 = time.perf_counter()
    decision = gate(state, proposal)

    results: Tuple[ExecResult, ...] = ()
    if decision.allowed:
        results = execute_decision(state, decision)

    wall_ms = int((time.perf_counter() - t0) * 1000)

    append_ledger(
        ledger_path,
        state=state,
        proposal=proposal,
        decision=decision,
        results=results,
        meta={"wall_ms": wall_ms, "ts_ms": _now_ms()},
    )
    return StepOutcome(decision=decision, results=results, wall_ms=wall_ms)


def _last_run_tests_output(results: Iterable[ExecResult]) -> Tuple[str, str, bool]:
    for r in results:
        if r.action.type == "RUN_TESTS":
            out = r.output
            return (
                str(out.get("stdout") or ""),
                str(out.get("stderr") or ""),
                bool(out.get("ok")),
            )
    return ("", "", False)


def _read_files_via_gate(
    *,
    ledger_path: str,
    workspace: str,
    task_id: str,
    paths: List[str],
) -> List[Tuple[str, str]]:
    actions = [Action("READ_FILE", {"path": p}) for p in paths]
    proposal = Proposal(actions=tuple(actions), meta={"purpose": "context_pack", "paths": paths})
    state = StateSnapshot(workspace=workspace, notes={"task_id": task_id, "phase": "read_context"})
    step = run_step(ledger_path=ledger_path, state=state, proposal=proposal)

    out: List[Tuple[str, str]] = []
    if not step.decision.allowed:
        return out

    for r in step.results:
        if r.action.type == "READ_FILE" and r.ok:
            out.append((str(r.output.get("path")), str(r.output.get("text") or "")))
    return out


# --------- main loop ---------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--task-id", default="local_task")
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    ap.add_argument("--bandit-path", default="./run_logs/bandit.json")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(args.ledger), exist_ok=True)

    executor = PolicyExecutor(
        bandit=ThompsonBandit.load_or_create(args.bandit_path, seed=args.seed, decay=0.999)
    )

    llm = LLMClient.from_env()

    # Always start with a baseline test run (full suite allowlist)
    base_state = StateSnapshot(workspace=args.workspace, notes={"task_id": args.task_id, "phase": "baseline"})
    base_prop = Proposal(actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),), meta={"attempt": 0})
    base_step = run_step(ledger_path=args.ledger, state=base_state, proposal=base_prop)
    out_stdout, out_stderr, ok = _last_run_tests_output(base_step.results)

    if args.verbose:
        print(f"[baseline] allowed={base_step.decision.allowed} ok={ok}")

    if ok:
        verify_ledger_chain(args.ledger)
        if args.verbose:
            print("[done] tests already passing")
        return 0

    # Attempts: read context -> ask LLM -> apply patch -> rerun tests
    for attempt in range(1, args.attempts + 1):
        arm_id = executor.select_arm()
        plan = executor.get_execution_plan(arm_id)
        if not plan:
            if args.verbose:
                print(f"[error] unknown arm {arm_id} selected")
            continue

        # Build context pack using deterministic context builder with policy config
        pack = build_context_pack(
            ledger_path=args.ledger,
            workspace=args.workspace,
            task_id=args.task_id,
            pytest_stdout=out_stdout,
            pytest_stderr=out_stderr,
            focus_paths=None,
            max_files=plan.context_config.max_files,
            max_total_bytes=plan.context_config.max_total_bytes,
            max_per_file_bytes=60_000,
            max_grep_patterns=plan.context_config.max_grep_patterns,
            include_traceback_files=plan.context_config.include_traceback_files,
            include_imports=plan.context_config.include_imports,
            include_grep_expansion=plan.context_config.include_grep_expansion,
            deep_grep=plan.context_config.deep_grep,
            minimal_mode=plan.context_config.minimal_mode,
        )
        context_pack_text = format_context_pack(pack)

        prompt = build_prompt(
            task_id=args.task_id,
            test_stdout=out_stdout,
            test_stderr=out_stderr,
            context_pack_text=context_pack_text,
            instruction_suffix=plan.prompt_suffix,
        )

        if args.verbose:
            print(f"[attempt {attempt}] arm={arm_id} ctx_files={len(pack.files)} bytes={pack.meta.get('bytes_total')}")

        # Ask model for a diff; extract defensively.
        # Pass policy-specific model parameters
        raw = llm.complete(
            prompt=prompt,
            temperature=plan.model_config.temperature,
            max_tokens=plan.model_config.max_tokens,
            # model=plan.model_config.model_tier, # TODO: Map tiers to actual models if needed
        )
        diff = extract_unified_diff(raw)

        if not diff.strip():
            # Update bandit as failure and keep going.
            executor.record_outcome(arm_id, 0.0)
            if args.verbose:
                print(f"[attempt {attempt}] model returned no usable diff")
            continue

        patch_state = StateSnapshot(
            workspace=args.workspace,
            notes={
                "task_id": args.task_id,
                "phase": "patch",
                "attempt": attempt,
                "arm_id": arm_id,
                "policy_context": plan.arm.context.value,
                "policy_model": plan.arm.model.value,
            },
        )
        patch_prop = Proposal(
            actions=(
                Action("APPLY_PATCH", {"patch": diff}),
                Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),
            ),
            meta={"attempt": attempt, "arm_id": arm_id},
        )
        step = run_step(ledger_path=args.ledger, state=patch_state, proposal=patch_prop)
        out_stdout, out_stderr, ok = _last_run_tests_output(step.results)

        reward = 1.0 if (step.decision.allowed and ok) else 0.0
        executor.record_outcome(arm_id, reward)

        if args.verbose:
            print(f"[attempt {attempt}] allowed={step.decision.allowed} ok={ok} reward={reward}")

        if ok:
            break

    executor.bandit.save(args.bandit_path)
    verify_ledger_chain(args.ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
