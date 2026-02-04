# upstream_learner/episode_runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import time
import os

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger

from .features import reward_from_episode


@dataclass(frozen=True)
class EpisodeOutcome:
    decision_status: str
    tests_passed: bool
    wall_ms: int
    reward: float
    phase_count: int = 1


def run_episode(
    *,
    ledger_path: str,
    state: StateSnapshot,
    proposal: Proposal,
) -> EpisodeOutcome:
    """Single-phase episode (original behavior)."""
    t0 = time.perf_counter()

    decision = gate(state, proposal)
    results: Tuple = ()
    tests_passed = False

    if decision.status == "ALLOW":
        results = execute_decision(state, decision)

        for r in results:
            if r.action.name == "RUN_TESTS":
                tests_passed = bool(r.ok)

    wall_ms = int((time.perf_counter() - t0) * 1000)
    reward = reward_from_episode(decision.status, tests_passed, wall_ms)

    append_ledger(
        ledger_path=ledger_path,
        state=state,
        proposal=proposal,
        decision=decision,
        results=results,
        meta={"wall_ms": wall_ms, "tests_passed": tests_passed, "reward": reward},
    )

    return EpisodeOutcome(
        decision_status=decision.status,
        tests_passed=tests_passed,
        wall_ms=wall_ms,
        reward=reward,
        phase_count=1,
    )


def run_two_phase_episode(
    *,
    ledger_path: str,
    state: StateSnapshot,
    proposer_fn,  # Callable[[StateSnapshot], Proposal]
    max_candidates: int = 3,
) -> EpisodeOutcome:
    """
    Two-phase episode for trace-based candidate selection:
    
    Phase 1: Read .rfsn/last_tests.txt + run tests (to generate fresh trace)
    Phase 2: Parse trace -> select candidates -> read them -> optionally patch -> run tests
    
    Each phase is ledgered separately. Budget is decremented across phases.
    """
    from rfsn_companion.selectors.traceback_selector import select_candidate_paths

    t0 = time.perf_counter()
    ws = os.path.abspath(state.workspace_root)
    last_tests_path = os.path.join(ws, ".rfsn", "last_tests.txt")

    # =========================================================================
    # PHASE 1: Read last test output + run tests to refresh trace
    # =========================================================================
    phase1_actions = [
        Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
    ]

    # Optionally read existing trace first
    if os.path.exists(last_tests_path):
        phase1_actions.insert(0, Action(name="READ_FILE", args={"path": last_tests_path}))

    from rfsn_kernel.types import Proposal as P
    import uuid

    phase1_proposal = P(
        proposal_id=str(uuid.uuid4()),
        actions=tuple(phase1_actions),
        rationale="phase1: run tests to generate fresh trace",
        metadata={"phase": 1, "variant": state.notes.get("prompt_variant", "v4_trace_read")},
    )

    phase1_decision = gate(state, phase1_proposal)
    phase1_results: Tuple = ()
    phase1_tests_passed = False

    if phase1_decision.status == "ALLOW":
        phase1_results = execute_decision(state, phase1_decision)
        for r in phase1_results:
            if r.action.name == "RUN_TESTS":
                phase1_tests_passed = bool(r.ok)

    phase1_wall = int((time.perf_counter() - t0) * 1000)

    append_ledger(
        ledger_path=ledger_path,
        state=state,
        proposal=phase1_proposal,
        decision=phase1_decision,
        results=phase1_results,
        meta={"wall_ms": phase1_wall, "tests_passed": phase1_tests_passed, "phase": 1},
    )

    # If phase 1 was denied or tests passed, we're done
    if phase1_decision.status != "ALLOW":
        return EpisodeOutcome(
            decision_status="DENY",
            tests_passed=False,
            wall_ms=phase1_wall,
            reward=0.0,
            phase_count=1,
        )

    if phase1_tests_passed:
        # Tests already pass, no need for phase 2
        reward = reward_from_episode("ALLOW", True, phase1_wall)
        return EpisodeOutcome(
            decision_status="ALLOW",
            tests_passed=True,
            wall_ms=phase1_wall,
            reward=reward,
            phase_count=1,
        )

    # =========================================================================
    # PHASE 2: Parse trace -> select candidates -> read -> run tests
    # =========================================================================
    t1 = time.perf_counter()

    # Read the freshly-written trace
    trace_text = ""
    if os.path.exists(last_tests_path):
        try:
            with open(last_tests_path, "r", encoding="utf-8") as f:
                trace_text = f.read()
        except Exception:
            pass

    # Select candidate files deterministically
    candidates = select_candidate_paths(trace_text, ws, k=max_candidates)

    # Build phase 2 actions: read candidates + run tests
    phase2_actions = []
    for cand in candidates:
        phase2_actions.append(Action(name="READ_FILE", args={"path": cand}))

    # Check if user provided explicit patch target
    patch_path = state.notes.get("patch_path")
    patch_content = state.notes.get("patch_content")
    if isinstance(patch_path, str) and patch_path and isinstance(patch_content, str) and patch_content:
        ap = os.path.abspath(patch_path)
        if ap in set(candidates):
            # read-before-write satisfied since we read all candidates above
            phase2_actions.append(Action(name="APPLY_PATCH", args={"path": ap, "content": patch_content}))

    phase2_actions.append(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}))

    # Decrement budget for phase 2
    used_actions = len(phase1_actions)
    remaining_budget = max(0, state.budget_actions_remaining - used_actions)

    phase2_state = StateSnapshot(
        task_id=state.task_id,
        workspace_root=state.workspace_root,
        step=state.step + 1,
        budget_actions_remaining=remaining_budget,
        budget_wall_ms_remaining=max(0, state.budget_wall_ms_remaining - phase1_wall),
        notes={**state.notes, "last_tests_text": trace_text, "candidates": candidates},
    )

    phase2_proposal = P(
        proposal_id=str(uuid.uuid4()),
        actions=tuple(phase2_actions),
        rationale=f"phase2: read {len(candidates)} candidates from trace, run tests",
        metadata={"phase": 2, "candidates": candidates, "variant": state.notes.get("prompt_variant", "v4_trace_read")},
    )

    phase2_decision = gate(phase2_state, phase2_proposal)
    phase2_results: Tuple = ()
    phase2_tests_passed = False

    if phase2_decision.status == "ALLOW":
        phase2_results = execute_decision(phase2_state, phase2_decision)
        for r in phase2_results:
            if r.action.name == "RUN_TESTS":
                phase2_tests_passed = bool(r.ok)

    total_wall = int((time.perf_counter() - t0) * 1000)
    phase2_wall = int((time.perf_counter() - t1) * 1000)

    append_ledger(
        ledger_path=ledger_path,
        state=phase2_state,
        proposal=phase2_proposal,
        decision=phase2_decision,
        results=phase2_results,
        meta={"wall_ms": phase2_wall, "tests_passed": phase2_tests_passed, "phase": 2, "candidates": candidates},
    )

    final_status = phase2_decision.status
    final_tests = phase2_tests_passed
    reward = reward_from_episode(final_status, final_tests, total_wall)

    return EpisodeOutcome(
        decision_status=final_status,
        tests_passed=final_tests,
        wall_ms=total_wall,
        reward=reward,
        phase_count=2,
    )


# =============================================================================
# TRAJECTORY EPISODE (N-STEP REPAIR LOOP)
# =============================================================================

def _pytest_argv_full() -> list[str]:
    """Default pytest argv for full test suite."""
    return ["python", "-m", "pytest", "-q"]


def _pytest_argv_targeted(nodeids: list[str]) -> list[str]:
    """
    Build targeted pytest argv using -k expression.
    Stays within gate allowlist (which supports -k).
    """
    if not nodeids:
        return _pytest_argv_full()
    
    # Extract just the test function names (after last '::')
    names = []
    for n in nodeids[:25]:  # Cap to avoid pathologically long -k
        part = n.split("::")[-1]
        # Remove any parameterized parts like [param]
        if "[" in part:
            part = part.split("[")[0]
        part = part.replace('"', "").replace("'", "")
        if part:
            names.append(part)
    
    if not names:
        return _pytest_argv_full()
    
    expr = " or ".join(names)
    return ["python", "-m", "pytest", "-q", "-k", expr]


def run_trajectory_episode(
    *,
    ledger_path: str,
    task_id: str,
    workspace_root: str,
    proposer_fn,  # Callable[[StateSnapshot, dict], Proposal]
    max_steps: int = 6,
    panic_on_deny: bool = False,
    budget_actions: int = 100,
    budget_wall_ms: int = 300_000,
) -> EpisodeOutcome:
    """
    Run up to max_steps proposals in sequence (trajectory repair loop).
    
    Each step:
        1. Read failed tests from last run
        2. proposer_fn(state, observation) -> Proposal
        3. gate(state, proposal) -> Decision
        4. controller.execute(approved_actions) -> results
        5. ledger.append(...)
        6. If tests pass, stop. Otherwise continue.
    
    Observation includes:
        - failed_nodeids: List of failed test node IDs
        - prefer_targeted_tests: Whether to prioritize failed tests
        - suggested_test_argv: Allowlisted argv for targeted testing
    
    Returns:
        EpisodeOutcome with trajectory results.
    """
    from .failing_tests import read_failed_nodeids
    
    t0 = time.perf_counter()
    ws = os.path.abspath(workspace_root)
    
    # Initialize state
    state = StateSnapshot(
        task_id=task_id,
        workspace_root=ws,
        step=0,
        budget_actions_remaining=budget_actions,
        budget_wall_ms_remaining=budget_wall_ms,
        mode="NORMAL",
        notes={},
    )
    
    ok_final = False
    denied_count = 0
    total_phases = 0
    
    for step in range(max_steps):
        total_phases = step + 1
        
        # Get failed tests from last run
        failed = read_failed_nodeids(ws)
        
        # Build observation for proposer
        observation = {
            "failed_nodeids": failed,
            "prefer_targeted_tests": bool(failed),
            "suggested_test_argv": _pytest_argv_targeted(failed) if failed else _pytest_argv_full(),
            "step": step,
        }
        
        # Get proposal from upstream
        proposal = proposer_fn(state, observation)
        
        # Gate validation
        decision = gate(state, proposal)
        
        if decision.status != "ALLOW":
            denied_count += 1
            
            # Ledger the denial
            append_ledger(
                ledger_path=ledger_path,
                state=state,
                proposal=proposal,
                decision=decision,
                results=(),
                meta={"step": step, "denied": True},
            )
            
            if panic_on_deny:
                # Enter PANIC mode and stop
                state = StateSnapshot(
                    task_id=state.task_id,
                    workspace_root=state.workspace_root,
                    step=state.step + 1,
                    budget_actions_remaining=state.budget_actions_remaining,
                    budget_wall_ms_remaining=state.budget_wall_ms_remaining,
                    mode="PANIC",
                    notes=dict(state.notes),
                )
                break
            
            # Continue to next step (learner can try another variant)
            break
        
        # Execute approved actions
        results = execute_decision(state, decision)
        
        # Check if tests passed
        step_tests_passed = False
        for r in results:
            if r.action.name == "RUN_TESTS":
                step_tests_passed = bool(r.ok)
        
        # Ledger the step
        step_wall_ms = int((time.perf_counter() - t0) * 1000)
        append_ledger(
            ledger_path=ledger_path,
            state=state,
            proposal=proposal,
            decision=decision,
            results=results,
            meta={"step": step, "tests_passed": step_tests_passed, "wall_ms": step_wall_ms},
        )
        
        # Success check
        if step_tests_passed:
            # Double check no more failures
            remaining_failures = read_failed_nodeids(ws)
            if not remaining_failures:
                ok_final = True
                break
        
        # Advance state for next step
        used_actions = len(proposal.actions)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        
        state = StateSnapshot(
            task_id=state.task_id,
            workspace_root=state.workspace_root,
            step=state.step + 1,
            budget_actions_remaining=max(0, state.budget_actions_remaining - used_actions),
            budget_wall_ms_remaining=max(0, state.budget_wall_ms_remaining - elapsed_ms),
            mode=state.mode,
            notes=dict(state.notes),
        )
        
        # Budget check
        if state.budget_actions_remaining <= 0:
            break
    
    total_wall_ms = int((time.perf_counter() - t0) * 1000)
    status = "ALLOW" if denied_count == 0 else "DENY"
    reward = reward_from_episode(status, ok_final, total_wall_ms)
    
    return EpisodeOutcome(
        decision_status=status,
        tests_passed=ok_final,
        wall_ms=total_wall_ms,
        reward=reward,
        phase_count=total_phases,
    )
