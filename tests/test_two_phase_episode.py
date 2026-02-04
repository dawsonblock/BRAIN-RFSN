# tests/test_two_phase_episode.py
from __future__ import annotations


from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposer import propose
from upstream_learner.episode_runner import run_two_phase_episode


def test_two_phase_episode_runs_both_phases(tmp_path):
    """Two-phase episode should run phase 1 and phase 2."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    # Create a minimal test that fails
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_fail(): assert False\n")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={"prompt_variant": "v4_trace_read"},
    )

    outcome = run_two_phase_episode(
        ledger_path=ledger,
        state=state,
        proposer_fn=propose,
        max_candidates=3,
    )

    # Should complete with 2 phases (test fails, so phase 2 runs)
    assert outcome.phase_count == 2
    assert outcome.wall_ms > 0


def test_two_phase_episode_stops_if_tests_pass(tmp_path):
    """If tests pass in phase 1, phase 2 is skipped."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    # Create a passing test
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_pass(): assert True\n")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={"prompt_variant": "v4_trace_read"},
    )

    outcome = run_two_phase_episode(
        ledger_path=ledger,
        state=state,
        proposer_fn=propose,
        max_candidates=3,
    )

    # Should complete in 1 phase since tests pass
    assert outcome.phase_count == 1
    assert outcome.tests_passed is True
    assert outcome.decision_status == "ALLOW"


def test_two_phase_ledger_entries(tmp_path):
    """Two-phase episode should create ledger entries for each phase."""
    ws = str(tmp_path)
    ledger = tmp_path / "ledger.jsonl"

    # Create failing test
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_fail(): assert False\n")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={"prompt_variant": "v4_trace_read"},
    )

    run_two_phase_episode(
        ledger_path=str(ledger),
        state=state,
        proposer_fn=propose,
        max_candidates=3,
    )

    # Should have 2 ledger entries (phase 1 + phase 2)
    lines = ledger.read_text().strip().split("\n")
    assert len(lines) == 2


def test_two_phase_extracts_candidates_from_trace(tmp_path):
    """Phase 2 should extract candidate files from trace."""
    ws = str(tmp_path)
    ledger = str(tmp_path / "ledger.jsonl")

    # Create a file that will appear in the trace
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    buggy = pkg_dir / "buggy.py"
    buggy.write_text("def broken():\n    raise ValueError('boom')\n")

    test_file = tmp_path / "test_buggy.py"
    test_file.write_text("from pkg.buggy import broken\ndef test_it(): broken()\n")

    state = StateSnapshot(
        task_id="t",
        workspace_root=ws,
        step=0,
        budget_actions_remaining=20,
        notes={"prompt_variant": "v4_trace_read"},
    )

    outcome = run_two_phase_episode(
        ledger_path=ledger,
        state=state,
        proposer_fn=propose,
        max_candidates=3,
    )

    # Should complete with 2 phases
    assert outcome.phase_count == 2

    # Check that .rfsn/last_tests.txt was created
    last_tests = tmp_path / ".rfsn" / "last_tests.txt"
    assert last_tests.exists()
    content = last_tests.read_text()
    assert "buggy.py" in content or "ValueError" in content
