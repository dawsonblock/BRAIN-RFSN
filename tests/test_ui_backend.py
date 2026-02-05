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


# ============ FastAPI TestClient Tests ============

import pytest


@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health endpoints."""

    def test_root_returns_ok(self, api_client):
        """GET / should return status ok."""
        resp = api_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_endpoint(self, api_client):
        """GET /health should return healthy."""
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_csp_header_present(self, api_client):
        """Responses should have CSP header."""
        resp = api_client.get("/")
        assert "Content-Security-Policy" in resp.headers

    def test_x_content_type_options(self, api_client):
        """Responses should have nosniff."""
        resp = api_client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, api_client):
        """Responses should have DENY frame options."""
        resp = api_client.get("/")
        assert resp.headers.get("X-Frame-Options") == "DENY"


class TestSettingsEndpoint:
    """Tests for settings endpoint."""

    def test_get_settings_no_api_key_leak(self, api_client):
        """GET /settings should not expose full API key."""
        resp = api_client.get("/settings")
        assert resp.status_code == 200
        data = resp.json()
        # Full api_key should not be present or should be empty
        assert "api_key" not in data or data.get("api_key") == ""
        assert "api_key_preview" in data


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint."""

    def test_websocket_connection(self, api_client):
        """WebSocket should accept valid connection."""
        with api_client.websocket_connect("/ws/run/test-run-abc") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["run_id"] == "test-run-abc"


class TestEventBroadcastEndpoint:
    """Tests for event broadcast endpoint."""

    def test_post_event_accepted(self, api_client):
        """POST /api/event should accept events."""
        resp = api_client.post(
            "/api/event/test-run?event_type=test",
            json={"key": "value"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

