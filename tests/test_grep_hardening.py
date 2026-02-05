# tests/test_grep_hardening.py
"""Tests for GREP hardening (excludes, fixed_string)."""
from __future__ import annotations

import pytest

from rfsn_kernel.gate import gate
from rfsn_kernel.types import Action, Proposal, StateSnapshot


def test_gate_accepts_grep_fixed_string_true(tmp_path):
    """Gate should accept GREP with fixed_string=True."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("GREP", {"pattern": "test", "fixed_string": True}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_accepts_grep_fixed_string_false(tmp_path):
    """Gate should accept GREP with fixed_string=False."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("GREP", {"pattern": "test.*foo", "fixed_string": False}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_accepts_grep_no_fixed_string(tmp_path):
    """Gate should accept GREP without fixed_string (default: regex mode)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("GREP", {"pattern": "test"}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_rejects_non_bool_fixed_string(tmp_path):
    """Gate should reject GREP with non-bool fixed_string."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("GREP", {"pattern": "test", "fixed_string": "yes"}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is False
    assert "fixed_string must be bool" in d.reason
