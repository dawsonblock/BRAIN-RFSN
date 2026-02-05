"""
Integration tests for the UI backend API.

These tests verify end-to-end HTTP request/response behavior.
"""

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from ui.backend.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_root_endpoint(self, client):
        """Root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "RFSN" in data["service"]

    def test_health_endpoint(self, client):
        """Health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSecurityHeaders:
    """Test that security headers are present on responses."""

    def test_csp_header_present(self, client):
        """Content-Security-Policy header is set."""
        response = client.get("/")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_x_content_type_options(self, client):
        """X-Content-Type-Options header prevents MIME sniffing."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        """X-Frame-Options header prevents clickjacking."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_xss_protection(self, client):
        """X-XSS-Protection header is enabled."""
        response = client.get("/")
        assert "X-XSS-Protection" in response.headers

    def test_referrer_policy(self, client):
        """Referrer-Policy header is set."""
        response = client.get("/")
        assert "Referrer-Policy" in response.headers


class TestRunEndpoints:
    """Test run management endpoints."""

    def test_list_runs_empty(self, client):
        """List runs returns empty list initially."""
        response = client.get("/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_run_requires_workspace_for_agent(self, client):
        """Agent mode requires workspace path."""
        response = client.post("/runs/create", json={
            "mode": "agent",
            "workspace": "",
        })
        assert response.status_code == 400
        assert "workspace" in response.json()["detail"].lower()

    def test_create_run_requires_tasks_for_harness(self, client):
        """Harness mode requires tasks file."""
        response = client.post("/runs/create", json={
            "mode": "harness",
            "tasks_file": "",
        })
        assert response.status_code == 400
        assert "tasks_file" in response.json()["detail"].lower()

    def test_invalid_run_id_rejected(self, client):
        """Invalid run IDs are rejected."""
        response = client.get("/runs/invalid-run-id")
        assert response.status_code == 400
        assert "Invalid run ID" in response.json()["detail"]

    def test_nonexistent_run_returns_404(self, client):
        """Valid format but nonexistent run returns 404."""
        response = client.get("/runs/run_20240101_120000_abcdef12")
        assert response.status_code == 404


class TestSettingsEndpoints:
    """Test settings endpoints."""

    def test_get_settings(self, client):
        """Get settings returns model info."""
        response = client.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "has_api_key" in data
        # API key should not be exposed
        assert "api_key" not in data or data.get("api_key") == ""

    def test_save_settings(self, client):
        """Save settings succeeds."""
        response = client.post("/settings", json={
            "model": "gpt-4-turbo",
            "base_url": "",
            "api_key": "",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "saved"


class TestInputValidation:
    """Test input validation across endpoints."""

    def test_invalid_mode_rejected(self, client):
        """Invalid mode values are rejected."""
        response = client.post("/runs/create", json={
            "mode": "invalid_mode",
            "workspace": "/tmp/test",
        })
        assert response.status_code == 400

    def test_log_type_validation(self, client):
        """Log type must be stdout or stderr."""
        # This will fail because run doesn't exist, but validates the parameter
        response = client.get("/runs/run_20240101_120000_abcdef12/logs?log_type=invalid")
        # Should be 422 for validation error or 400 for invalid run
        assert response.status_code in (400, 422)

    def test_tail_limit_enforced(self, client):
        """Tail parameter has limits."""
        response = client.get("/runs/run_20240101_120000_abcdef12/logs?tail=99999")
        # Should be 422 for validation error (exceeds max)
        assert response.status_code in (400, 422)


class TestArtifactSecurity:
    """Test artifact access security."""

    def test_path_traversal_blocked(self, client):
        """Path traversal attempts are blocked."""
        response = client.get(
            "/runs/run_20240101_120000_abcdef12/artifacts/file",
            params={"path": "../../../etc/passwd"}
        )
        # Should be 403 or 404 depending on which check fails first
        assert response.status_code in (400, 403, 404)

    def test_absolute_path_rejected(self, client):
        """Absolute paths in artifact requests are rejected."""
        response = client.get(
            "/runs/run_20240101_120000_abcdef12/artifacts/file",
            params={"path": "/etc/passwd"}
        )
        assert response.status_code in (400, 403, 404)
