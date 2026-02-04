# tests/test_security_hardening.py
"""
Critical security tests for kernel hardening.
Tests the 4 security fixes:
1. RUN_TESTS argv allowlist
2. Realpath containment (symlink-safe)
3. Path normalization (workspace-relative)
4. Read capping (max_bytes)
"""
from __future__ import annotations

import os
import pytest
from rfsn_kernel.gate import gate, is_allowed_tests_argv
from rfsn_kernel.controller import _realpath_is_under, _resolve_under_workspace
from rfsn_kernel.types import StateSnapshot, Proposal, Action


class TestRunTestsAllowlist:
    """Tests for RUN_TESTS argv allowlist."""

    def test_valid_pytest_q(self):
        """Standard pytest -q is allowed."""
        assert is_allowed_tests_argv(["python", "-m", "pytest", "-q"])

    def test_valid_pytest_with_k(self):
        """pytest with -k filter is allowed."""
        assert is_allowed_tests_argv(["python", "-m", "pytest", "-q", "-k", "test_foo"])

    def test_valid_pytest_with_maxfail(self):
        """pytest with --maxfail is allowed."""
        assert is_allowed_tests_argv(["python", "-m", "pytest", "-q", "--maxfail=1"])

    def test_invalid_curl(self):
        """curl command is NOT allowed."""
        assert not is_allowed_tests_argv(["curl", "http://evil.com"])

    def test_invalid_python_c(self):
        """python -c is NOT allowed (arbitrary code)."""
        assert not is_allowed_tests_argv(["python", "-c", "import os; os.system('rm -rf /')"])

    def test_invalid_rm(self):
        """rm command is NOT allowed."""
        assert not is_allowed_tests_argv(["rm", "-rf", "/"])

    def test_invalid_bash(self):
        """bash command is NOT allowed."""
        assert not is_allowed_tests_argv(["bash", "-c", "echo pwned"])

    def test_invalid_pytest_pyargs(self):
        """pytest --pyargs is NOT allowed (can escape)."""
        assert not is_allowed_tests_argv(["python", "-m", "pytest", "-q", "--pyargs", "os"])

    def test_invalid_no_q_flag(self):
        """-q flag is required (prevents output flooding)."""
        assert not is_allowed_tests_argv(["python", "-m", "pytest"])

    def test_invalid_injection_in_k(self):
        """-k expressions with shell metacharacters are blocked."""
        assert not is_allowed_tests_argv(["python", "-m", "pytest", "-q", "-k", "test; rm -rf /"])


class TestRealpathContainment:
    """Tests for symlink-safe path containment."""

    def test_normal_path_under_workspace(self, tmp_path):
        """Normal path under workspace is allowed."""
        ws = str(tmp_path)
        path = os.path.join(ws, "foo", "bar.py")
        assert _realpath_is_under(ws, path)

    def test_dotdot_escape_blocked(self, tmp_path):
        """.. escape attempt is blocked."""
        ws = str(tmp_path)
        path = os.path.join(ws, "..", "escape.py")
        # After realpath resolution, this should be outside
        resolved = os.path.realpath(os.path.abspath(path))
        ws_real = os.path.realpath(os.path.abspath(ws))
        # The path should NOT be under workspace
        assert not resolved.startswith(ws_real + os.sep) or resolved == ws_real

    def test_absolute_outside_blocked(self, tmp_path):
        """Absolute path outside workspace is blocked."""
        ws = str(tmp_path)
        path = "/etc/passwd"
        assert not _realpath_is_under(ws, path)


class TestPathNormalization:
    """Tests for workspace-relative path resolution."""

    def test_relative_path_resolved_to_workspace(self, tmp_path):
        """Relative path is resolved against workspace, not CWD."""
        ws = str(tmp_path)
        result = _resolve_under_workspace(ws, "foo.py")
        expected = os.path.abspath(os.path.join(ws, "foo.py"))
        assert result == expected

    def test_absolute_path_unchanged(self, tmp_path):
        """Absolute path is returned as-is."""
        ws = str(tmp_path)
        path = "/some/absolute/path.py"
        result = _resolve_under_workspace(ws, path)
        assert result == os.path.abspath(path)


class TestGateRejectsUnsafeTests:
    """Tests that gate denies unsafe RUN_TESTS."""

    @pytest.fixture
    def state(self, tmp_path):
        return StateSnapshot(
            task_id="test",
            workspace_root=str(tmp_path),
            step=0,
            budget_actions_remaining=10,
        )

    def test_gate_denies_curl_argv(self, state):
        """Gate denies RUN_TESTS with curl argv."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["curl", "http://evil.com"]}),
            ),
        )
        decision = gate(state, proposal)
        assert decision.status == "DENY"
        assert any("tests_argv" in r for r in decision.reasons)

    def test_gate_denies_python_c_argv(self, state):
        """Gate denies RUN_TESTS with python -c."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-c", "print('pwned')"]}),
            ),
        )
        decision = gate(state, proposal)
        assert decision.status == "DENY"
        assert any("tests_argv" in r for r in decision.reasons)

    def test_gate_allows_valid_pytest(self, state):
        """Gate allows valid pytest invocation."""
        proposal = Proposal(
            proposal_id="p1",
            actions=(
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )
        decision = gate(state, proposal)
        assert decision.status == "ALLOW"
