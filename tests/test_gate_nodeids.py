# tests/test_gate_nodeids.py
"""Tests for extended pytest nodeid allowlist in gate."""
from __future__ import annotations

from rfsn_kernel.gate import is_allowed_tests_argv


class TestAllowedTestsArgv:
    def test_basic_pytest_q(self):
        """Basic pytest -q should be allowed."""
        assert is_allowed_tests_argv(["pytest", "-q"]) is True
        assert is_allowed_tests_argv(["python", "-m", "pytest", "-q"]) is True

    def test_single_nodeid(self):
        """Single nodeid after -q is allowed."""
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py"]) is True
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py::test_bar"]) is True
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py::TestClass::test_method"]) is True

    def test_multiple_nodeids(self):
        """Multiple nodeids are allowed."""
        assert is_allowed_tests_argv([
            "pytest", "-q",
            "tests/test_a.py::test_x",
            "tests/test_b.py::test_y",
        ]) is True

    def test_rejects_flags_after_q(self):
        """Flags (like -s, --cov) after -q should be rejected."""
        assert is_allowed_tests_argv(["pytest", "-q", "-s"]) is False
        assert is_allowed_tests_argv(["pytest", "-q", "--cov"]) is False
        assert is_allowed_tests_argv(["pytest", "-q", "tests/foo.py", "-v"]) is False

    def test_rejects_bad_patterns(self):
        """Reject patterns that could be shell injection or other exploits."""
        assert is_allowed_tests_argv(["pytest", "-q", "; rm -rf /"]) is False
        assert is_allowed_tests_argv(["pytest", "-q", "$(malicious)"]) is False
        assert is_allowed_tests_argv(["pytest", "-q", "`whoami`"]) is False

    def test_rejects_empty_and_invalid(self):
        """Empty and invalid argv should be rejected."""
        assert is_allowed_tests_argv([]) is False
        assert is_allowed_tests_argv(["pytest"]) is False  # missing -q
        assert is_allowed_tests_argv(["python", "pytest", "-q"]) is False  # wrong prefix

    def test_path_with_dashes_in_name(self):
        """Paths with dashes (like my-test.py) are valid."""
        assert is_allowed_tests_argv(["pytest", "-q", "tests/my-test.py::test_thing"]) is True

    def test_colons_in_nodeid(self):
        """Nodeids can have multiple :: separators."""
        assert is_allowed_tests_argv([
            "pytest", "-q",
            "tests/test_foo.py::TestClass::test_method"
        ]) is True
