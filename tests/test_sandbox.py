"""
Unit tests for Advanced Sandbox.
"""
import os
from security.advanced_sandbox import get_sandbox, ExecutionResult


def test_sandbox_execution_success():
    """Test that the sandbox can execute a simple command."""
    sandbox = get_sandbox()
    instance = sandbox.create_sandbox("/tmp/test_sandbox_success")
    result = sandbox.execute(instance, ["echo", "Hello, World!"])
    
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout


def test_sandbox_execution_failure():
    """Test that the sandbox handles failed commands."""
    sandbox = get_sandbox()
    instance = sandbox.create_sandbox("/tmp/test_sandbox_failure")
    result = sandbox.execute(instance, ["ls", "/nonexistent_directory_xyz"])
    
    assert isinstance(result, ExecutionResult)
    assert result.exit_code != 0
    # Docker combines stdout/stderr, so check both
    error_output = result.stderr + result.stdout
    assert len(error_output) > 0


def test_sandbox_workspace_creation():
    """Test that sandbox workspaces are created."""
    sandbox = get_sandbox()
    workspace_path = "/tmp/test_sandbox_workspace"
    instance = sandbox.create_sandbox(workspace_path)
    
    assert os.path.exists(workspace_path)
    assert instance.workspace_path == workspace_path


def test_sandbox_command_in_workspace():
    """Test that commands execute in the correct workspace."""
    sandbox = get_sandbox()
    workspace_path = "/tmp/test_sandbox_cwd"
    instance = sandbox.create_sandbox(workspace_path)
    
    # Create a test file
    test_file = os.path.join(workspace_path, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")
    
    # List files in workspace
    result = sandbox.execute(instance, ["ls"])
    assert result.exit_code == 0
    assert "test.txt" in result.stdout


def test_sandbox_timeout():
    """Test that long-running commands timeout."""
    sandbox = get_sandbox()
    sandbox.config.timeout_seconds = 1
    instance = sandbox.create_sandbox("/tmp/test_sandbox_timeout")
    
    # This command should timeout
    result = sandbox.execute(instance, ["sleep", "10"])
    assert result.exit_code == -1
    # Docker timeout message differs from subprocess
    assert "timed out" in result.stderr.lower() or "timeout" in result.stderr.lower()
