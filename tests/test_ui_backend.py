# tests/test_ui_backend.py
"""Minimal tests for UI backend."""
from __future__ import annotations

import json
from pathlib import Path


def test_security_path_confinement():
    """Test path confinement checks."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))
    
    from backend.security import is_path_confined, safe_join, validate_run_id
    
    # Valid run IDs
    assert validate_run_id("run_20240101_120000_abc12345")
    assert validate_run_id("run_20240215_235959_abc98765")
    
    # Invalid run IDs
    assert not validate_run_id("../../../etc/passwd")
    assert not validate_run_id("run_id; rm -rf /")
    assert not validate_run_id("")
    
    # Path confinement
    assert is_path_confined("/base", "/base/sub/file.txt")
    assert not is_path_confined("/base", "/other/file.txt")
    assert not is_path_confined("/base", "/base/../other")
    
    # Safe join
    assert safe_join("/base", "sub/file.txt") == "/base/sub/file.txt"
    assert safe_join("/base", "../other") is None
    assert safe_join("/base", "/absolute/path") is None


def test_ledger_parsing():
    """Test ledger parsing and timeline building."""
    import sys
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))
    
    from backend.ledger_parse import parse_ledger_file, build_timeline, verify_ledger_chain
    
    # Create test ledger
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write some test entries
        entries = [
            {"seq": 0, "event_type": "PROPOSAL", "data": {"actions": []}, "hash": "abc", "prev_hash": "000"},
            {"seq": 1, "event_type": "DECISION", "data": {"allowed": True}, "hash": "def", "prev_hash": "abc"},
            {"seq": 2, "event_type": "RESULT", "data": {"ok": True}, "hash": "ghi", "prev_hash": "def"},
        ]
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
        ledger_path = f.name
    
    # Parse
    parsed = parse_ledger_file(ledger_path)
    assert len(parsed) == 3
    assert parsed[0].event_type == "PROPOSAL"
    
    # Build timeline
    timeline = build_timeline(parsed)
    assert len(timeline) >= 1
    
    # Cleanup
    Path(ledger_path).unlink()


def test_run_manager():
    """Test run manager creation."""
    import sys
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))
    
    from backend.run_manager import RunManager, RunConfig, RunMode
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RunManager(runs_dir=tmpdir)
        
        # Create a run
        config = RunConfig(
            mode=RunMode.AGENT,
            workspace="/tmp/test",
            model="gpt-4",
        )
        run = manager.create_run(config)
        
        assert run.id.startswith("run_")
        assert run.status.value == "created"
        assert run.config.mode == RunMode.AGENT
        
        # List runs
        runs = manager.list_runs()
        assert len(runs) == 1
        
        # Get run
        retrieved = manager.get_run(run.id)
        assert retrieved is not None
        assert retrieved.id == run.id
