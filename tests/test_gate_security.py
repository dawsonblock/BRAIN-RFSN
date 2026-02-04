# tests/test_gate_security.py
"""
Critical security tests for gate enforcement.

NOTE: SHELL_EXEC, WEB_SEARCH, BROWSE_URL, DELEGATE have been removed from kernel.
These tests now verify they are correctly denied as unknown actions.
"""
from __future__ import annotations

import pytest
from rfsn_kernel.gate import gate
from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.policy import KernelPolicy


@pytest.fixture
def state(tmp_path):
    return StateSnapshot(
        task_id="test",
        workspace_root=str(tmp_path),
        step=0,
        budget_actions_remaining=10,
    )


# Policies for testing
POLICY_DENY_UNKNOWN = KernelPolicy(
    deny_shell=True,
    deny_network=True,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)

POLICY_ALLOW_UNKNOWN = KernelPolicy(
    deny_shell=False,
    deny_network=False,
    deny_unknown_actions=False,  # Allow unknown actions (still won't have envelope)
    require_tests_after_write=False,
)


class TestRemovedActionsAreDenied:
    """Tests that verify non-kernel actions are denied as unknown_action.
    
    SHELL_EXEC, WEB_SEARCH, BROWSE_URL, DELEGATE have been moved to upstream.
    They should not be recognized by the kernel gate.
    """

    def test_shell_exec_denied_as_unknown(self, state):
        """SHELL_EXEC is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="SHELL_EXEC", args={"command": "ls", "cwd": state.workspace_root}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:SHELL_EXEC" in r for r in decision.reasons)

    def test_web_search_denied_as_unknown(self, state):
        """WEB_SEARCH is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="WEB_SEARCH", args={"query": "test query"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:WEB_SEARCH" in r for r in decision.reasons)

    def test_browse_url_denied_as_unknown(self, state):
        """BROWSE_URL is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="BROWSE_URL", args={"url": "https://example.com"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:BROWSE_URL" in r for r in decision.reasons)

    def test_delegate_denied_as_unknown(self, state):
        """DELEGATE is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="DELEGATE", args={"task": "sub-task"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:DELEGATE" in r for r in decision.reasons)

    def test_remember_denied_as_unknown(self, state):
        """REMEMBER is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="REMEMBER", args={"content": "test", "metadata": {}}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:REMEMBER" in r for r in decision.reasons)

    def test_recall_denied_as_unknown(self, state):
        """RECALL is not a kernel action - must be denied as unknown."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="RECALL", args={"query": "test", "k": 5}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "DENY"
        assert any("unknown_action:RECALL" in r for r in decision.reasons)


class TestKernelActionsStillWork:
    """Verify kernel-only actions still work correctly."""

    def test_read_file_allowed(self, state):
        """READ_FILE is a kernel action and should be allowed."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="READ_FILE", args={"path": f"{state.workspace_root}/test.py"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "ALLOW"

    def test_run_tests_allowed(self, state):
        """RUN_TESTS is a kernel action and should be allowed."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_UNKNOWN)

        assert decision.status == "ALLOW"

