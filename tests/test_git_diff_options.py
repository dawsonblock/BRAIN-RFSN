# tests/test_git_diff_options.py
"""Tests for GIT_DIFF action with paths and context_lines options."""
from __future__ import annotations

import os
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.types import Action, Proposal, StateSnapshot


class TestGitDiffOptions:
    def test_gate_accepts_empty_payload(self, tmp_path):
        """GIT_DIFF with no payload is valid."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        action = Action(type="GIT_DIFF", payload={})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
    
    def test_gate_accepts_valid_context_lines(self, tmp_path):
        """GIT_DIFF with valid context_lines is accepted."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        
        for ctx in [0, 1, 3, 10]:
            action = Action(type="GIT_DIFF", payload={"context_lines": ctx})
            proposal = Proposal(actions=(action,), meta={})
            decision = gate(state, proposal)
            assert decision.allowed, f"context_lines={ctx} should be allowed"
    
    def test_gate_rejects_invalid_context_lines(self, tmp_path):
        """GIT_DIFF with out-of-range context_lines is rejected."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        
        for ctx in [-1, 11, 100]:
            action = Action(type="GIT_DIFF", payload={"context_lines": ctx})
            proposal = Proposal(actions=(action,), meta={})
            decision = gate(state, proposal)
            assert not decision.allowed, f"context_lines={ctx} should be rejected"
    
    def test_gate_accepts_valid_paths(self, tmp_path):
        """GIT_DIFF with valid paths is accepted."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        action = Action(type="GIT_DIFF", payload={"paths": ["src/main.py", "tests/test_main.py"]})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
    
    def test_gate_rejects_unconfined_paths(self, tmp_path):
        """GIT_DIFF with unconfined paths is rejected."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        action = Action(type="GIT_DIFF", payload={"paths": ["../etc/passwd"]})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "not confined" in decision.reason
    
    def test_gate_rejects_too_many_paths(self, tmp_path):
        """GIT_DIFF with >20 paths is rejected."""
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".git").mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        paths = [f"file{i}.py" for i in range(25)]
        action = Action(type="GIT_DIFF", payload={"paths": paths})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "max 20" in decision.reason
    
    def test_controller_passes_options_to_git(self, tmp_path):
        """Controller passes paths and context_lines to git diff."""
        ws = tmp_path / "repo"
        ws.mkdir()
        os.system(f"cd {ws} && git init -q")
        
        # Create and commit a file
        (ws / "test.py").write_text("x = 1\n", encoding="utf-8")
        os.system(f"cd {ws} && git add . && git commit -q -m init")
        
        # Modify the file
        (ws / "test.py").write_text("x = 2\n", encoding="utf-8")
        
        state = StateSnapshot(workspace=str(ws), notes={})
        action = Action(type="GIT_DIFF", payload={"paths": ["test.py"], "context_lines": 1})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok
        assert "x = 2" in results[0].output.get("diff", "")
        assert results[0].output.get("paths") == ["test.py"]
        assert results[0].output.get("context_lines") == 1
