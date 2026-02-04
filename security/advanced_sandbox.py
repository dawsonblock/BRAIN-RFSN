"""
Advanced Sandbox (Docker-backed).
Provides an isolated environment for command execution using Docker containers.
"""
from __future__ import annotations

import logging
import os
import docker # type: ignore
from docker.errors import DockerException, APIError # type: ignore
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class SandboxConfig:
    network_enabled: bool = False
    timeout_seconds: int = 30
    image: str = "python:3.12-slim"
    mem_limit: str = "512m"
    nano_cpus: int = 500000000 # 0.5 CPU

@dataclass
class SandboxInstance:
    workspace_path: str
    container_id: Optional[str] = None

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str

class DockerSandbox:
    def __init__(self):
        self.config = SandboxConfig()
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("🐳 Docker Sandbox initialized successfully.")
        except (DockerException, APIError) as e:
            logger.warning(f"⚠️ Docker not available: {e}. Sandbox will fail on execution.")
            self.client = None

    def create_sandbox(self, workspace_path: str) -> SandboxInstance:
        """Creates a new sandbox instance (workspace)."""
        os.makedirs(workspace_path, exist_ok=True)
        return SandboxInstance(workspace_path=os.path.abspath(workspace_path))

    def execute(self, sandbox: SandboxInstance, command: List[str]) -> ExecutionResult:
        """
        Executes a command within a secure Docker container.
        The container mounts the workspace_path to /workspace and runs the command there.
        """
        if not self.client:
            return ExecutionResult(-1, "", "Docker client not initialized.")

        cmd_str = " ".join(command)
        
        # Configure network
        network_mode = "bridge" if self.config.network_enabled else "none"

        try:
            # We run the container, execute the command, and capture the logs.
            # For simplicity in this v1, we run a fresh container for each command.
            # In a persistent session, we would use 'exec_run' on a sleeping container.
            
            logger.info(f"🐳 executing in sandbox: {cmd_str}")
            
            # Using specific volume mount syntax
            volumes = {
                sandbox.workspace_path: {'bind': '/workspace', 'mode': 'rw'}
            }
            
            # Run the container
            # auto_remove=False so we can inspect exit code/logs, then remove manually
            # We pass the command list directly to avoid shell quoting issues
            container = self.client.containers.run(
                image=self.config.image,
                command=command, 
                working_dir="/workspace",
                volumes=volumes,
                network_mode=network_mode,
                mem_limit=self.config.mem_limit,
                nano_cpus=self.config.nano_cpus,
                detach=True,
                user=str(os.getuid()) # Run as current user to avoid permission issues with mounted files
            )
            
            # Wait for result
            result = container.wait(timeout=self.config.timeout_seconds)
            logs = container.logs(stdout=True, stderr=True)
            
            exit_code = result.get('StatusCode', -1)
            stdout = logs.decode('utf-8')
            stderr = "" # Docker combines stdout/stderr in logs() mixed stream usually, or we split if needed.
                        # For simple 'logs()', it returns byte string. 
                        
            # Cleanup
            container.remove()

            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return ExecutionResult(exit_code=-1, stdout="", stderr=str(e))

# Singleton instance
_sandbox: Optional[DockerSandbox] = None

def get_sandbox() -> DockerSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = DockerSandbox()
    return _sandbox
