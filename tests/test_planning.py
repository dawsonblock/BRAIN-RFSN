# tests/test_planning.py
"""Tests for the planning layer."""
from __future__ import annotations


from rfsn_kernel.types import StateSnapshot
from rfsn_kernel.policy import KernelPolicy
from rfsn_companion.planner.goal_decomposer import Goal, decompose_goal, Plan, PlanStep
from rfsn_companion.planner.plan_executor import execute_plan, PlanResult


# Permissive policy for testing shell execution in plans
PERMISSIVE_POLICY = KernelPolicy(
    deny_shell=False,
    deny_network=False,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)


def test_rule_based_decompose_research():
    """Rule-based decomposer should handle 'research' goals."""
    goal = Goal(description="research Python asyncio")
    plan = decompose_goal(goal, api_key=None)

    assert isinstance(plan, Plan)
    assert len(plan.steps) >= 1
    assert plan.steps[0].action_name == "WEB_SEARCH"
    assert plan.metadata.get("source") == "rules"


def test_rule_based_decompose_fix():
    """Rule-based decomposer should handle 'fix' goals."""
    goal = Goal(description="fix the failing tests")
    plan = decompose_goal(goal, api_key=None)

    assert len(plan.steps) >= 1
    assert plan.steps[0].action_name == "RUN_TESTS"


def test_rule_based_decompose_default():
    """Rule-based decomposer should default to running tests."""
    goal = Goal(description="do something random")
    plan = decompose_goal(goal, api_key=None)

    assert len(plan.steps) >= 1


def test_plan_executor_runs_steps(tmp_path):
    """Plan executor should run steps and report results."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={},
    )

    # Simple plan: shell echo (allowed with permissive policy)
    plan = Plan(
        goal=Goal(description="test"),
        steps=[
            PlanStep(1, "SHELL_EXEC", {"command": "echo hello"}, "Echo test", []),
        ],
    )

    result = execute_plan(plan, state, ledger, policy=PERMISSIVE_POLICY)

    assert isinstance(result, PlanResult)
    assert result.success is True
    assert len(result.step_results) == 1
    assert result.step_results[0].success is True


def test_plan_executor_respects_dependencies(tmp_path):
    """Plan executor should execute steps in dependency order."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={},
    )

    # Plan with dependencies
    plan = Plan(
        goal=Goal(description="test"),
        steps=[
            PlanStep(1, "SHELL_EXEC", {"command": "echo step1"}, "Step 1", []),
            PlanStep(2, "SHELL_EXEC", {"command": "echo step2"}, "Step 2", [1]),
            PlanStep(3, "SHELL_EXEC", {"command": "echo step3"}, "Step 3", [1, 2]),
        ],
    )

    result = execute_plan(plan, state, ledger, policy=PERMISSIVE_POLICY)

    assert result.success is True
    assert len(result.step_results) == 3
    # All should succeed
    assert all(r.success for r in result.step_results)


def test_plan_executor_stops_on_failure(tmp_path):
    """Plan executor should stop on first failure."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={},
    )

    # Plan with a failing step
    plan = Plan(
        goal=Goal(description="test"),
        steps=[
            PlanStep(1, "SHELL_EXEC", {"command": "exit 1"}, "Fail", []),
            PlanStep(2, "SHELL_EXEC", {"command": "echo never"}, "Never run", [1]),
        ],
    )

    result = execute_plan(plan, state, ledger, policy=PERMISSIVE_POLICY)

    assert result.success is False
    assert len(result.step_results) == 1  # Only first step attempted
    assert result.step_results[0].success is False


def test_plan_executor_logs_to_ledger(tmp_path):
    """Plan executor should log each step to the ledger."""
    ws = str(tmp_path)
    ledger = tmp_path / "ledger.jsonl"

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={},
    )

    plan = Plan(
        goal=Goal(description="test"),
        steps=[
            PlanStep(1, "SHELL_EXEC", {"command": "echo a"}, "Step A", []),
            PlanStep(2, "SHELL_EXEC", {"command": "echo b"}, "Step B", [1]),
        ],
    )

    execute_plan(plan, state, str(ledger), policy=PERMISSIVE_POLICY)

    # Should have 2 ledger entries
    lines = ledger.read_text().strip().split("\n")
    assert len(lines) == 2


def test_plan_blocked_by_default_policy(tmp_path):
    """Plans with SHELL_EXEC should be blocked by default policy."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={},
    )

    plan = Plan(
        goal=Goal(description="test"),
        steps=[
            PlanStep(1, "SHELL_EXEC", {"command": "echo hello"}, "Echo", []),
        ],
    )

    # Use default policy (deny_shell=True)
    result = execute_plan(plan, state, ledger)

    assert result.success is False
    assert "Gate denied" in (result.error or "")
