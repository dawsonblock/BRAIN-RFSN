# rfsn_companion/planner/plan_executor.py
"""Execute plans step-by-step with rollback and replanning support."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict
import uuid

from rfsn_kernel.types import StateSnapshot, Proposal, Action, ExecResult
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger
from rfsn_kernel.policy import KernelPolicy

from .goal_decomposer import Plan, PlanStep


@dataclass
class StepResult:
    step: PlanStep
    success: bool
    exec_result: Optional[ExecResult] = None
    error: Optional[str] = None


@dataclass
class PlanResult:
    plan: Plan
    step_results: List[StepResult]
    success: bool
    error: Optional[str] = None


def execute_plan(
    plan: Plan,
    state: StateSnapshot,
    ledger_path: str,
    policy: KernelPolicy | None = None,
) -> PlanResult:
    """
    Execute a plan step-by-step.
    
    - Respects step dependencies
    - Gates each step through the kernel
    - Stops on first failure (can be extended for rollback)
    - Logs each step to the ledger
    """
    results: List[StepResult] = []
    completed_steps: Dict[int, StepResult] = {}

    # Build dependency graph
    remaining = list(plan.steps)

    while remaining:
        # Find steps with satisfied dependencies
        ready = [
            s for s in remaining
            if all(d in completed_steps for d in s.depends_on)
        ]

        if not ready:
            # Circular dependency or bug
            return PlanResult(
                plan=plan,
                step_results=results,
                success=False,
                error="Stuck: no steps ready (circular dependency?)",
            )

        # Execute first ready step
        step = ready[0]
        remaining.remove(step)

        step_result = _execute_step(step, state, ledger_path, policy)
        results.append(step_result)
        completed_steps[step.step_id] = step_result

        if not step_result.success:
            # Stop on failure
            return PlanResult(
                plan=plan,
                step_results=results,
                success=False,
                error=f"Step {step.step_id} failed: {step_result.error}",
            )

        # Update state for next step (increment step counter)
        state = StateSnapshot(
            task_id=state.task_id,
            workspace_root=state.workspace_root,
            step=state.step + 1,
            budget_actions_remaining=state.budget_actions_remaining - 1,
            budget_wall_ms_remaining=state.budget_wall_ms_remaining,
            mode=state.mode,  # Preserve kernel mode
            notes=state.notes,
        )

    return PlanResult(
        plan=plan,
        step_results=results,
        success=True,
    )


def _execute_step(
    step: PlanStep,
    state: StateSnapshot,
    ledger_path: str,
    policy: KernelPolicy | None = None,
) -> StepResult:
    """Execute a single plan step through the kernel."""

    # Create action
    action = Action(
        name=step.action_name,
        args=step.action_args,
    )

    # Create proposal
    proposal = Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=(action,),
        rationale=step.description,
        metadata={"step_id": step.step_id},
    )

    # Gate the proposal
    decision = gate(state, proposal, policy=policy)

    if decision.status != "ALLOW":
        return StepResult(
            step=step,
            success=False,
            error=f"Gate denied: {decision.reasons}",
        )

    # Execute
    try:
        exec_results = execute_decision(state, decision)
        exec_result = exec_results[0] if exec_results else None

        # Log to ledger
        append_ledger(
            ledger_path=ledger_path,
            state=state,
            proposal=proposal,
            decision=decision,
            results=exec_results,
            meta={"step_id": step.step_id, "description": step.description},
        )

        if exec_result and not exec_result.ok:
            return StepResult(
                step=step,
                success=False,
                exec_result=exec_result,
                error=exec_result.stderr or "Execution failed",
            )

        return StepResult(
            step=step,
            success=True,
            exec_result=exec_result,
        )

    except Exception as e:
        return StepResult(
            step=step,
            success=False,
            error=str(e),
        )
