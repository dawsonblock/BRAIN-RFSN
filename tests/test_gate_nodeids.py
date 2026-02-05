# tests/test_gate_nodeids.py
"""Tests for extended pytest nodeid allowlist in gate."""
from __future__ import annotations

from rfsn_kernel.gate import is_allowed_tests_argv


class TestAllowedTestsArgv:
    """Test is_allowed_tests_argv with workspace parameter."""

    def test_basic_pytest_q(self, tmp_path):
        """Basic pytest -q should be allowed."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv(["pytest", "-q"], workspace=ws) is True
        assert is_allowed_tests_argv(["python", "-m", "pytest", "-q"], workspace=ws) is True

    def test_single_nodeid(self, tmp_path):
        """Single nodeid after -q is allowed if file exists inside workspace."""
        ws = tmp_path
        (ws / "tests").mkdir()
        (ws / "tests" / "test_foo.py").write_text("def test_bar(): pass", encoding="utf-8")
        
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py"], workspace=str(ws)) is True
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py::test_bar"], workspace=str(ws)) is True
        assert is_allowed_tests_argv(["pytest", "-q", "tests/test_foo.py::TestClass::test_method"], workspace=str(ws)) is True

    def test_multiple_nodeids(self, tmp_path):
        """Multiple nodeids are allowed if files exist."""
        ws = tmp_path
        (ws / "tests").mkdir()
        (ws / "tests" / "test_a.py").write_text("def test_x(): pass", encoding="utf-8")
        (ws / "tests" / "test_b.py").write_text("def test_y(): pass", encoding="utf-8")
        
        assert is_allowed_tests_argv([
            "pytest", "-q",
            "tests/test_a.py::test_x",
            "tests/test_b.py::test_y",
        ], workspace=str(ws)) is True

    def test_rejects_flags_after_q(self, tmp_path):
        """Flags (like -s, --cov) after -q should be rejected."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv(["pytest", "-q", "-s"], workspace=ws) is False
        assert is_allowed_tests_argv(["pytest", "-q", "--cov"], workspace=ws) is False
        
        # Create a test file then try adding a flag
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "foo.py").write_text("", encoding="utf-8")
        assert is_allowed_tests_argv(["pytest", "-q", "tests/foo.py", "-v"], workspace=ws) is False

    def test_rejects_bad_patterns(self, tmp_path):
        """Reject patterns that could be shell injection or other exploits."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv(["pytest", "-q", "; rm -rf /"], workspace=ws) is False
        assert is_allowed_tests_argv(["pytest", "-q", "$(malicious)"], workspace=ws) is False
        assert is_allowed_tests_argv(["pytest", "-q", "`whoami`"], workspace=ws) is False

    def test_rejects_empty_and_invalid(self, tmp_path):
        """Empty and invalid argv should be rejected."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv([], workspace=ws) is False
        assert is_allowed_tests_argv(["pytest"], workspace=ws) is False  # missing -q
        assert is_allowed_tests_argv(["python", "pytest", "-q"], workspace=ws) is False  # wrong prefix

    def test_path_with_dashes_in_name(self, tmp_path):
        """Paths with dashes (like my-test.py) are valid."""
        ws = tmp_path
        (ws / "tests").mkdir()
        (ws / "tests" / "my-test.py").write_text("def test_thing(): pass", encoding="utf-8")
        
        assert is_allowed_tests_argv(["pytest", "-q", "tests/my-test.py::test_thing"], workspace=str(ws)) is True

    def test_colons_in_nodeid(self, tmp_path):
        """Nodeids can have multiple :: separators."""
        ws = tmp_path
        (ws / "tests").mkdir()
        (ws / "tests" / "test_foo.py").write_text("class TestClass:\n  def test_method(self): pass", encoding="utf-8")
        
        assert is_allowed_tests_argv([
            "pytest", "-q",
            "tests/test_foo.py::TestClass::test_method"
        ], workspace=str(ws)) is True

    def test_rejects_traversal_in_nodeid(self, tmp_path):
        """Nodeids with traversal should be rejected."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv(["pytest", "-q", "../etc/passwd::test"], workspace=ws) is False
        assert is_allowed_tests_argv(["pytest", "-q", "a/../../b.py::test"], workspace=ws) is False

    def test_rejects_absolute_path_nodeid(self, tmp_path):
        """Nodeids with absolute paths should be rejected."""
        ws = str(tmp_path)
        assert is_allowed_tests_argv(["pytest", "-q", "/etc/passwd::test"], workspace=ws) is False
