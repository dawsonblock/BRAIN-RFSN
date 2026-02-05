# tests/test_new_actions.py
"""
Tests for GREP, LIST_DIR, GIT_DIFF actions.
"""
import subprocess
import pytest

from rfsn_kernel.types import StateSnapshot, Action, Proposal
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision


@pytest.fixture
def git_workspace(tmp_path):
    """Create a git workspace with some files."""
    ws = tmp_path / "ws"
    ws.mkdir()
    subprocess.run(["git", "init"], cwd=str(ws), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(ws), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(ws), capture_output=True)
    
    # Create some files
    (ws / "foo.py").write_text("def hello():\n    return 'world'\n")
    (ws / "bar.py").write_text("import foo\nprint(foo.hello())\n")
    (ws / "subdir").mkdir()
    (ws / "subdir" / "baz.py").write_text("# nested file\nx = 42\n")
    
    subprocess.run(["git", "add", "."], cwd=str(ws), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(ws), capture_output=True)
    
    return ws


class TestGrepAction:
    def test_grep_basic(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GREP", payload={"pattern": "hello"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok
        assert results[0].output["count"] >= 1
        assert any("hello" in m for m in results[0].output["matches"])

    def test_grep_with_path(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GREP", payload={"pattern": "nested", "path": "subdir"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok

    def test_grep_rejects_traversal(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GREP", payload={"pattern": "hello", "path": "../outside"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "not confined" in decision.reason

    def test_grep_rejects_empty_pattern(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GREP", payload={"pattern": ""})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "missing pattern" in decision.reason


class TestListDirAction:
    def test_list_dir_root(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="LIST_DIR", payload={})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok
        entries = results[0].output["entries"]
        names = [e["name"] for e in entries]
        assert "foo.py" in names
        assert "bar.py" in names
        assert "subdir" in names

    def test_list_dir_subdir(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="LIST_DIR", payload={"path": "subdir"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok
        entries = results[0].output["entries"]
        names = [e["name"] for e in entries]
        assert "baz.py" in names

    def test_list_dir_rejects_traversal(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="LIST_DIR", payload={"path": "../"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "not confined" in decision.reason

    def test_list_dir_rejects_symlink_escape(self, git_workspace, tmp_path):
        # Create outside directory and symlink to it
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret")
        
        link = git_workspace / "escape"
        link.symlink_to(outside)
        
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="LIST_DIR", payload={"path": "escape"})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert not decision.allowed
        assert "symlink" in decision.reason.lower() or "escapes" in decision.reason.lower()


class TestGitDiffAction:
    def test_git_diff_basic(self, git_workspace):
        # Make a change
        (git_workspace / "foo.py").write_text("def hello():\n    return 'changed'\n")
        
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GIT_DIFF", payload={})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok
        # Should have diff output
        assert "foo.py" in results[0].output["diff"]

    def test_git_diff_no_changes(self, git_workspace):
        state = StateSnapshot(workspace=str(git_workspace), notes={})
        action = Action(type="GIT_DIFF", payload={})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert results[0].ok

    def test_git_diff_not_git_repo(self, tmp_path):
        ws = tmp_path / "not_git"
        ws.mkdir()
        
        state = StateSnapshot(workspace=str(ws), notes={})
        action = Action(type="GIT_DIFF", payload={})
        proposal = Proposal(actions=(action,), meta={})
        
        decision = gate(state, proposal)
        assert decision.allowed  # Gate doesn't check for .git
        
        results = execute_decision(state, decision)
        assert len(results) == 1
        assert not results[0].ok
        assert "not a git repo" in results[0].output["error"]
