# tests/test_extended_actions.py
"""Tests for extended actions: web, shell, memory."""
from __future__ import annotations


from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.policy import KernelPolicy


# Permissive policy for testing actions that need shell/network
PERMISSIVE_POLICY = KernelPolicy(
    deny_shell=False,
    deny_network=False,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)


def test_web_search_action_executes(tmp_path):
    """WEB_SEARCH action should execute when policy allows network."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="WEB_SEARCH", args={"query": "python", "num_results": 2}),
        ),
        rationale="test",
    )

    decision = gate(state, proposal, policy=PERMISSIVE_POLICY)
    assert decision.status == "ALLOW"

    results = execute_decision(state, decision)
    assert len(results) == 1
    assert results[0].action.name == "WEB_SEARCH"


def test_shell_exec_action_executes(tmp_path):
    """SHELL_EXEC action should execute when policy allows shell."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="SHELL_EXEC", args={"command": "echo hello"}),
        ),
        rationale="test",
    )

    decision = gate(state, proposal, policy=PERMISSIVE_POLICY)
    assert decision.status == "ALLOW"

    results = execute_decision(state, decision)
    assert len(results) == 1
    assert results[0].ok is True
    assert "hello" in results[0].stdout


def test_remember_recall_actions(tmp_path):
    """REMEMBER and RECALL actions should store and retrieve."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    # Store something
    proposal1 = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="REMEMBER", args={"content": "The answer is 42", "metadata": {"type": "fact"}}),
        ),
        rationale="test",
    )

    decision1 = gate(state, proposal1)
    assert decision1.status == "ALLOW"

    results1 = execute_decision(state, decision1)
    assert results1[0].ok is True
    assert "STORED:" in results1[0].stdout

    # Recall it
    proposal2 = Proposal(
        proposal_id="p2",
        actions=(
            Action(name="RECALL", args={"query": "answer", "k": 1}),
        ),
        rationale="test",
    )

    decision2 = gate(state, proposal2)
    assert decision2.status == "ALLOW"

    results2 = execute_decision(state, decision2)
    assert results2[0].ok is True
    assert "42" in results2[0].stdout


def test_gate_blocks_shell_by_default(tmp_path):
    """Gate should block SHELL_EXEC with default policy (deny_shell=True)."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="SHELL_EXEC", args={"command": "echo hello"}),
        ),
        rationale="test",
    )

    # Use default policy (deny_shell=True)
    decision = gate(state, proposal)
    assert decision.status == "DENY"
    assert any("shell_denied" in r for r in decision.reasons)


def test_recall_empty_returns_no_matches(tmp_path):
    """RECALL on empty memory should return NO_MATCHES."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="RECALL", args={"query": "nonexistent"}),
        ),
        rationale="test",
    )

    decision = gate(state, proposal)
    assert decision.status == "ALLOW"

    results = execute_decision(state, decision)
    assert results[0].ok is True
    assert "NO_MATCHES" in results[0].stdout


def test_delegate_blocked_by_default(tmp_path):
    """DELEGATE action blocked by default policy (shell+network required)."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="DELEGATE", args={"task": "do something"}),
        ),
        rationale="test",
    )

    # Default policy denies shell+network, DELEGATE needs both
    decision = gate(state, proposal)
    assert decision.status == "DENY"


def test_delegate_executes_with_permissive_policy(tmp_path):
    """DELEGATE action returns not implemented when policy allows."""
    ws = str(tmp_path)

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=10,
        notes={},
    )

    proposal = Proposal(
        proposal_id="p1",
        actions=(
            Action(name="DELEGATE", args={"task": "do something"}),
        ),
        rationale="test",
    )

    decision = gate(state, proposal, policy=PERMISSIVE_POLICY)
    assert decision.status == "ALLOW"

    results = execute_decision(state, decision)
    assert results[0].ok is False  # Not implemented yet
    assert "not yet implemented" in results[0].stderr.lower()
