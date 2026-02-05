# tests/test_security_hardening.py
"""Tests for security hardening: realpath, write caps, symlink escape."""
from __future__ import annotations

from rfsn_kernel.gate import (
    gate,
    is_allowed_tests_argv,
    _realpath_in_workspace,
    _is_confined_relative,
    _MAX_WRITE_BYTES,
)
from rfsn_kernel.types import Action, Proposal, StateSnapshot


class TestRealpathConfinement:
    def test_realpath_in_workspace_normal(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        assert _realpath_in_workspace(str(ws), "foo.py") is True
        assert _realpath_in_workspace(str(ws), "sub/bar.py") is True

    def test_realpath_rejects_symlink_escape(self, tmp_path):
        """Symlink inside workspace pointing outside should be rejected."""
        ws = tmp_path / "ws"
        ws.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        
        # Create symlink inside workspace pointing to outside
        link = ws / "escape.txt"
        link.symlink_to(outside)
        
        # Realpath should detect escape
        assert _realpath_in_workspace(str(ws), "escape.txt") is False

    def test_realpath_rejects_traversal_via_symlink_dir(self, tmp_path):
        """Symlink directory that allows traversal should be rejected."""
        ws = tmp_path / "ws"
        ws.mkdir()
        
        # Create symlink to parent
        link = ws / "parent"
        link.symlink_to(tmp_path)
        
        # Trying to access parent/../outside via symlink
        assert _realpath_in_workspace(str(ws), "parent") is False


class TestConfinedRelative:
    def test_rejects_absolute(self):
        assert _is_confined_relative("/etc/passwd") is False
        assert _is_confined_relative("~/.bashrc") is False

    def test_rejects_traversal(self):
        assert _is_confined_relative("../foo.py") is False
        assert _is_confined_relative("a/../../../etc/passwd") is False
        assert _is_confined_relative("..") is False

    def test_accepts_normal_paths(self):
        assert _is_confined_relative("foo.py") is True
        assert _is_confined_relative("a/b/c.py") is True
        assert _is_confined_relative("tests/test_foo.py") is True


class TestWriteCaps:
    def test_gate_rejects_oversized_write(self, tmp_path):
        big_text = "x" * (_MAX_WRITE_BYTES + 1)
        st = StateSnapshot(workspace=str(tmp_path), notes={})
        prop = Proposal(
            actions=(Action("WRITE_FILE", {"path": "big.txt", "text": big_text}),),
            meta={},
        )
        d = gate(st, prop)
        assert d.allowed is False
        assert "per-file cap" in d.reason

    def test_gate_rejects_cumulative_overflow(self, tmp_path):
        # Multiple writes that are individually under per-file cap but together exceed proposal cap
        # Per-file: 512KB, Proposal: 2MB. Use 5 writes of 500KB each = 2.5MB > 2MB
        size = 500_000  # 500KB each, under 512KB per-file cap
        st = StateSnapshot(workspace=str(tmp_path), notes={})
        prop = Proposal(
            actions=(
                Action("WRITE_FILE", {"path": "a.txt", "text": "a" * size}),
                Action("WRITE_FILE", {"path": "b.txt", "text": "b" * size}),
                Action("WRITE_FILE", {"path": "c.txt", "text": "c" * size}),
                Action("WRITE_FILE", {"path": "d.txt", "text": "d" * size}),
                Action("WRITE_FILE", {"path": "e.txt", "text": "e" * size}),
            ),
            meta={},
        )
        d = gate(st, prop)
        assert d.allowed is False
        assert "proposal cap" in d.reason


class TestGateSymlinkEscape:
    def test_read_file_rejects_symlink_escape(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        outside = tmp_path / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        link = ws / "link.txt"
        link.symlink_to(outside)

        st = StateSnapshot(workspace=str(ws), notes={})
        prop = Proposal(actions=(Action("READ_FILE", {"path": "link.txt"}),), meta={})
        d = gate(st, prop)
        assert d.allowed is False
        assert "symlink" in d.reason.lower()

    def test_write_file_rejects_symlink_escape(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        outside = tmp_path / "target.txt"
        link = ws / "link.txt"
        link.symlink_to(outside)

        st = StateSnapshot(workspace=str(ws), notes={})
        prop = Proposal(actions=(Action("WRITE_FILE", {"path": "link.txt", "text": "pwned"}),), meta={})
        d = gate(st, prop)
        assert d.allowed is False
        assert "symlink" in d.reason.lower()


class TestNodeidValidation:
    def test_nodeid_with_traversal_rejected(self, tmp_path):
        """Nodeids with traversal in file path should be rejected."""
        ws = tmp_path / "ws"
        ws.mkdir()
        tests_dir = ws / "tests"
        tests_dir.mkdir()

        st = StateSnapshot(workspace=str(ws), notes={})
        
        # Traversal in nodeid
        prop = Proposal(
            actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q", "../etc/passwd::test"]}),),
            meta={},
        )
        d = gate(st, prop)
        assert d.allowed is False

    def test_nodeid_pointing_outside_rejected(self, tmp_path):
        """Nodeids pointing to files outside workspace should be rejected."""
        ws = tmp_path / "ws"
        ws.mkdir()

        st = StateSnapshot(workspace=str(ws), notes={})
        
        # Absolute path as nodeid
        prop = Proposal(
            actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q", "/etc/passwd::test"]}),),
            meta={},
        )
        d = gate(st, prop)
        assert d.allowed is False

    def test_valid_nodeids_accepted(self, tmp_path):
        """Valid nodeids pointing inside workspace should be accepted."""
        ws = tmp_path / "ws"
        ws.mkdir()
        tests_dir = ws / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_foo.py"
        test_file.write_text("def test_x(): pass", encoding="utf-8")

        # Valid nodeid
        assert is_allowed_tests_argv(
            ["pytest", "-q", "tests/test_foo.py::test_x"],
            workspace=str(ws),
        ) is True
