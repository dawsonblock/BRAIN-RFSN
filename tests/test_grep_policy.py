# tests/test_grep_policy.py
"""Tests for GREP pattern policy - prevent regex DoS."""
from __future__ import annotations

import pytest

from rfsn_kernel.gate import gate, _validate_grep_pattern
from rfsn_kernel.types import Action, Proposal, StateSnapshot


class TestValidateGrepPattern:
    """Unit tests for _validate_grep_pattern."""

    def test_accepts_normal_pattern(self):
        ok, why = _validate_grep_pattern("foo_bar")
        assert ok is True
        assert why == "ok"

    def test_accepts_regex_pattern(self):
        ok, why = _validate_grep_pattern(r"def\s+(\w+)\(")
        assert ok is True

    def test_rejects_empty_pattern(self):
        ok, why = _validate_grep_pattern("")
        assert ok is False
        assert "empty" in why

    def test_rejects_whitespace_only(self):
        ok, why = _validate_grep_pattern("   ")
        assert ok is False

    def test_rejects_long_pattern(self):
        ok, why = _validate_grep_pattern("a" * 500)
        assert ok is False
        assert "too long" in why

    def test_rejects_catastrophic_backtracking_plus(self):
        ok, why = _validate_grep_pattern("(.+)+")
        assert ok is False
        assert "suspicious" in why

    def test_rejects_catastrophic_backtracking_star(self):
        ok, why = _validate_grep_pattern("(.*)+")
        assert ok is False
        assert "suspicious" in why

    def test_rejects_nested_quantifier(self):
        ok, why = _validate_grep_pattern(".++")
        assert ok is False


class TestGateRejectsUnsafeGrep:
    """Integration tests: gate rejects unsafe GREP patterns."""

    def test_gate_rejects_long_pattern(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        st = StateSnapshot(workspace=str(ws), notes={})
        prop = Proposal(actions=(Action("GREP", {"pattern": "a" * 2000, "path": "."}),), meta={})

        d = gate(st, prop)
        assert d.allowed is False
        assert "too long" in d.reason or "GREP rejected" in d.reason

    def test_gate_rejects_suspicious_regex(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        st = StateSnapshot(workspace=str(ws), notes={})
        prop = Proposal(actions=(Action("GREP", {"pattern": "(.+)+", "path": "."}),), meta={})

        d = gate(st, prop)
        assert d.allowed is False
        assert "GREP rejected" in d.reason

    def test_gate_accepts_safe_pattern(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        st = StateSnapshot(workspace=str(ws), notes={})
        prop = Proposal(actions=(Action("GREP", {"pattern": "ValueError", "path": "."}),), meta={})

        d = gate(st, prop)
        assert d.allowed is True
