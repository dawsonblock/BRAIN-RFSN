# tests/test_run_tests_mode.py
"""Tests for RUN_TESTS mode validation and execution."""
from __future__ import annotations

import pytest

from rfsn_kernel.gate import gate
from rfsn_kernel.types import Action, Proposal, StateSnapshot


def test_gate_accepts_run_tests_mode_host(tmp_path):
    """Gate should accept RUN_TESTS with mode='host'."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"], "mode": "host"}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_accepts_run_tests_mode_docker(tmp_path):
    """Gate should accept RUN_TESTS with mode='docker'."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"], "mode": "docker"}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_accepts_run_tests_no_mode(tmp_path):
    """Gate should accept RUN_TESTS without mode (uses default)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"]}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True


def test_gate_rejects_invalid_run_tests_mode(tmp_path):
    """Gate should reject RUN_TESTS with invalid mode."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"], "mode": "k8s"}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is False
    assert "mode" in d.reason.lower()


def test_gate_rejects_non_string_mode(tmp_path):
    """Gate should reject RUN_TESTS with non-string mode."""
    ws = tmp_path / "ws"
    ws.mkdir()
    st = StateSnapshot(workspace=str(ws), notes={})
    prop = Proposal(
        actions=(Action("RUN_TESTS", {"argv": ["pytest", "-q"], "mode": 123}),),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is False
    assert "mode must be string" in d.reason
