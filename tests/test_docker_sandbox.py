"""
Tests for Docker Integration and Isolation.
"""
import pytest
docker = pytest.importorskip("docker")
from security.advanced_sandbox import DockerSandbox
import os

# Marker for tests that require a live Docker daemon
# To run these: pytest -m docker
# To skip these: pytest -m "not docker"

@pytest.fixture
def docker_sandbox():
    return DockerSandbox()

@pytest.fixture
def temp_workspace(tmp_path):
    return str(tmp_path)

@pytest.mark.docker
def test_docker_basic_execution(docker_sandbox, temp_workspace):
    """Verifies that we can run a simple python command inside the container."""
    if not docker_sandbox.client:
        pytest.skip("Docker client not available")
    
    sandbox = docker_sandbox.create_sandbox(temp_workspace)
    result = docker_sandbox.execute(sandbox, ["python", "-c", "print('Hello from Docker')"])
    
    assert result.exit_code == 0
    assert "Hello from Docker" in result.stdout

@pytest.mark.docker
def test_docker_file_persistence(docker_sandbox, temp_workspace):
    """Verifies that files written in the container persist to the host workspace."""
    if not docker_sandbox.client:
        pytest.skip("Docker client not available")
        
    sandbox = docker_sandbox.create_sandbox(temp_workspace)
    
    # Write a file inside the mounted /workspace
    cmd = ["python", "-c", "with open('test_file.txt', 'w') as f: f.write('persistent data')"]
    result = docker_sandbox.execute(sandbox, cmd)
    assert result.exit_code == 0
    
    # Check host filesystem
    host_file = os.path.join(temp_workspace, "test_file.txt")
    assert os.path.exists(host_file)
    with open(host_file, 'r') as f:
        content = f.read()
    assert content == "persistent data"

@pytest.mark.docker
def test_docker_network_isolation(docker_sandbox, temp_workspace):
    """Verifies that the container cannot access the internet."""
    if not docker_sandbox.client:
        pytest.skip("Docker client not available")
        
    # Ensure network is disabled by default
    docker_sandbox.config.network_enabled = False
    sandbox = docker_sandbox.create_sandbox(temp_workspace)
    
    # Try to curl google.com (should fail)
    # Note: python:3.12-slim might not have curl, so we use python socket
    cmd = [
        "python", "-c", 
        "import urllib.request; urllib.request.urlopen('http://google.com', timeout=2)"
    ]
    
    result = docker_sandbox.execute(sandbox, cmd)
    # It should fail either with timeout or network unreachable
    assert result.exit_code != 0
    # Error might be in stdout because docker logs combines streams
    error_msg = result.stderr + result.stdout
    assert "urllib.error.URLError" in error_msg or "timed out" in error_msg or "Temporary failure in name resolution" in error_msg

def test_sandbox_fallback_without_docker():
    """Verifies that the sandbox safely handles missing Docker daemon."""
    # Temporarily break the client
    original_client = docker.from_env
    docker.from_env = lambda: (_ for _ in ()).throw(docker.errors.DockerException("Mock failure"))
    
    try:
        broken_sandbox = DockerSandbox()
        assert broken_sandbox.client is None
        
        result = broken_sandbox.execute(None, ["ls"])
        assert result.exit_code == -1
        assert "not initialized" in result.stderr
    finally:
        docker.from_env = original_client
