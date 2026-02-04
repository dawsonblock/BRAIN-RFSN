# tests/test_kernel_comprehensive.py
"""Comprehensive tests for the RFSN kernel."""
from __future__ import annotations


from rfsn_kernel.types import StateSnapshot, Proposal, Action, Decision, ExecResult
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger, iter_ledger_entries
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism


class TestGateEdgeCases:
    """Test edge cases for the gate validator."""

    def test_gate_allows_read_then_write_then_test(self, tmp_path):
        """Valid proposal: read -> write -> test."""
        ws = str(tmp_path)
        target = f"{ws}/file.py"

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": target}),
                Action(name="WRITE_FILE", args={"path": target, "content": "# fixed\n"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "ALLOW", f"Expected ALLOW, got {d.status} with reasons: {d.reasons}"

    def test_gate_denies_run_cmd_by_default(self, tmp_path):
        """RUN_CMD should be denied by default policy."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="RUN_CMD", args={"argv": ["echo", "hello"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert any("run_cmd" in r.lower() for r in d.reasons)

    def test_gate_denies_too_many_actions(self, tmp_path):
        """Exceeding max_actions_per_proposal should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=100)

        # Create 25 actions (exceeds default 20 limit)
        actions = tuple(
            Action(name="READ_FILE", args={"path": f"{ws}/file{i}.py"})
            for i in range(25)
        )
        proposal = Proposal(proposal_id="p", actions=actions)

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "policy:max_actions_per_proposal_exceeded" in d.reasons

    def test_gate_denies_budget_exceeded(self, tmp_path):
        """Exceeding budget_actions_remaining should be denied."""
        ws = str(tmp_path)
        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=2)

        actions = tuple(
            Action(name="READ_FILE", args={"path": f"{ws}/file{i}.py"})
            for i in range(5)
        )
        proposal = Proposal(proposal_id="p", actions=actions)

        d = gate(state, proposal)
        assert d.status == "DENY"
        assert "budget:actions_exceeded" in d.reasons

    def test_gate_allows_multiple_reads_one_write(self, tmp_path):
        """Multiple reads should be allowed before writing one of them."""
        ws = str(tmp_path)
        target = f"{ws}/main.py"
        other = f"{ws}/utils.py"

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0, budget_actions_remaining=10)
        proposal = Proposal(
            proposal_id="p",
            actions=(
                Action(name="READ_FILE", args={"path": target}),
                Action(name="READ_FILE", args={"path": other}),
                Action(name="WRITE_FILE", args={"path": target, "content": "# changed\n"}),
                Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),
            ),
        )

        d = gate(state, proposal)
        assert d.status == "ALLOW"


class TestControllerExecution:
    """Test the controller executor."""

    def test_controller_executes_read_file(self, tmp_path):
        """Controller should read existing files."""
        ws = str(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world\n")

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        decision = Decision(
            status="ALLOW",
            approved_actions=(Action(name="READ_FILE", args={"path": str(test_file)}),),
        )

        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok is True
        assert "hello world" in results[0].stdout

    def test_controller_executes_write_file(self, tmp_path):
        """Controller should write files."""
        ws = str(tmp_path)
        target = tmp_path / "output.txt"

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        decision = Decision(
            status="ALLOW",
            approved_actions=(Action(name="WRITE_FILE", args={"path": str(target), "content": "new content\n"}),),
        )

        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok is True
        assert target.read_text() == "new content\n"

    def test_controller_handles_missing_file(self, tmp_path):
        """Controller should handle missing file gracefully."""
        ws = str(tmp_path)
        nonexistent = tmp_path / "nonexistent.txt"

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        decision = Decision(
            status="ALLOW",
            approved_actions=(Action(name="READ_FILE", args={"path": str(nonexistent)}),),
        )

        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok is False


class TestLedgerOperations:
    """Test ledger operations."""

    def test_ledger_append_and_iterate(self, tmp_path):
        """Test basic ledger append and iteration."""
        ledger_path = str(tmp_path / "ledger.jsonl")
        ws = str(tmp_path)

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        proposal = Proposal(
            proposal_id="p1",
            actions=(Action(name="RUN_TESTS", args={"argv": ["pytest"]}),),
        )
        decision = Decision(status="ALLOW", approved_actions=proposal.actions)
        results = (ExecResult(action=proposal.actions[0], ok=True, stdout="ok", stderr="", exit_code=0, duration_ms=100),)

        append_ledger(ledger_path, state, proposal, decision, results, meta={"test": True})

        entries = list(iter_ledger_entries(ledger_path))
        assert len(entries) == 1
        assert entries[0].idx == 0
        assert entries[0].payload["meta"]["test"] is True

    def test_ledger_hash_chain_continues(self, tmp_path):
        """Test that hash chain properly links entries."""
        ledger_path = str(tmp_path / "ledger.jsonl")
        ws = str(tmp_path)

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        proposal = Proposal(proposal_id="p", actions=(Action(name="RUN_TESTS", args={"argv": ["pytest"]}),))
        decision = Decision(status="ALLOW", approved_actions=proposal.actions)
        results = ()

        # Append 5 entries
        for i in range(5):
            append_ledger(ledger_path, state, proposal, decision, results, meta={"step": i})

        entries = list(iter_ledger_entries(ledger_path))
        assert len(entries) == 5

        # Verify chain linkage
        for i in range(1, 5):
            assert entries[i].prev_hash == entries[i - 1].entry_hash

        # Verify with replay
        ok, errs = verify_ledger_chain(ledger_path)
        assert ok, f"Chain verification failed: {errs}"


class TestReplayVerification:
    """Test replay verification."""

    def test_replay_gate_determinism(self, tmp_path):
        """Replay should verify gate produces same decisions."""
        ledger_path = str(tmp_path / "ledger.jsonl")
        ws = str(tmp_path)

        state = StateSnapshot(task_id="t", workspace_root=ws, step=0)
        proposal = Proposal(
            proposal_id="p",
            actions=(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}),),
        )
        decision = gate(state, proposal)
        results = ()

        append_ledger(ledger_path, state, proposal, decision, results)

        ok, errs = verify_gate_determinism(ledger_path)
        assert ok, f"Gate determinism failed: {errs}"
