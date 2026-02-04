# tests/test_gate_security.py
"""
Critical security tests for gate enforcement.
These tests verify that shell/network policies are enforced by envelope capability,
not by optional args or action names.
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
POLICY_DENY_SHELL = KernelPolicy(
    deny_shell=True,
    deny_network=False,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)

POLICY_ALLOW_SHELL = KernelPolicy(
    deny_shell=False,
    deny_network=False,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)

POLICY_DENY_NETWORK = KernelPolicy(
    deny_shell=False,
    deny_network=True,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)

POLICY_ALLOW_NETWORK = KernelPolicy(
    deny_shell=False,
    deny_network=False,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)

POLICY_DENY_BOTH = KernelPolicy(
    deny_shell=True,
    deny_network=True,
    deny_unknown_actions=True,
    require_tests_after_write=False,
)


class TestShellEnforcement:
    """Tests for deny_shell policy enforcement."""

    def test_gate_denies_shell_exec_when_deny_shell(self, state):
        """SHELL_EXEC must be denied when deny_shell=True."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="SHELL_EXEC", args={"command": "ls", "cwd": state.workspace_root}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_SHELL)

        assert decision.status == "DENY"
        assert any("shell_denied" in r for r in decision.reasons)

    def test_gate_allows_shell_exec_when_deny_shell_false(self, state):
        """SHELL_EXEC must be allowed when deny_shell=False."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="SHELL_EXEC", args={"command": "ls", "cwd": state.workspace_root}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_ALLOW_SHELL)

        assert decision.status == "ALLOW"


class TestNetworkEnforcement:
    """Tests for deny_network policy enforcement."""

    def test_gate_denies_web_search_when_deny_network(self, state):
        """WEB_SEARCH must be denied when deny_network=True."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="WEB_SEARCH", args={"query": "test query"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_NETWORK)

        assert decision.status == "DENY"
        assert any("network_denied" in r for r in decision.reasons)

    def test_gate_denies_browse_url_when_deny_network(self, state):
        """BROWSE_URL must be denied when deny_network=True."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="BROWSE_URL", args={"url": "https://example.com"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_NETWORK)

        assert decision.status == "DENY"
        assert any("network_denied" in r for r in decision.reasons)

    def test_gate_allows_web_search_when_deny_network_false(self, state):
        """WEB_SEARCH must be allowed when deny_network=False."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="WEB_SEARCH", args={"query": "test query"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_ALLOW_NETWORK)

        assert decision.status == "ALLOW"


class TestCombinedEnforcement:
    """Tests for combined shell+network denial."""

    def test_gate_denies_delegate_when_both_policies_set(self, state):
        """DELEGATE (shell+network) must be denied when both policies set."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="DELEGATE", args={"task": "sub-task"}),
            ),
        )

        decision = gate(state, proposal, policy=POLICY_DENY_BOTH)

        assert decision.status == "DENY"
        # Should be denied for at least one reason
        assert len(decision.reasons) >= 1
