# docker_runner.py
"""
Docker sandbox for running pytest in untrusted repos.

Security:
- No network access
- CPU/memory/time caps
- Mounted workspace (read-write)
- Fixed Python toolchain

Usage:
    runner = DockerRunner(workspace="/path/to/repo")
    result = runner.run_tests(["pytest", "-q"])
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# Default caps
_DEFAULT_TIMEOUT_S = 300       # 5 minutes
_DEFAULT_MEMORY_MB = 2048      # 2 GB
_DEFAULT_CPU_LIMIT = "1.0"     # 1 CPU
_MAX_OUTPUT_BYTES = 512_000    # 512 KB


@dataclass(frozen=True)
class SandboxResult:
    """Result from sandboxed test execution."""
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def _check_docker() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


class DockerRunner:
    """
    Run tests inside a Docker container with security constraints.
    """
    
    def __init__(
        self,
        workspace: str,
        image: str = "python:3.11-slim",
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        memory_mb: int = _DEFAULT_MEMORY_MB,
        cpu_limit: str = _DEFAULT_CPU_LIMIT,
        network: bool = False,
    ):
        self.workspace = os.path.realpath(workspace)
        self.image = image
        self.timeout_s = timeout_s
        self.memory_mb = memory_mb
        self.cpu_limit = cpu_limit
        self.network = network
        
        if not os.path.isdir(self.workspace):
            raise ValueError(f"Workspace not found: {self.workspace}")
    
    def is_available(self) -> bool:
        """Check if Docker is available on this system."""
        return _check_docker()
    
    def run_tests(
        self,
        argv: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        """
        Run test command inside Docker container.
        
        Args:
            argv: Test command, e.g. ["pytest", "-q"]
            env: Additional environment variables
        
        Returns:
            SandboxResult with stdout/stderr and success status
        """
        if not self.is_available():
            return SandboxResult(
                ok=False,
                returncode=-1,
                stdout="",
                stderr="Docker not available",
                timed_out=False,
            )
        
        # Build Docker command
        docker_cmd = [
            "docker", "run",
            "--rm",                                    # Remove container after run
            "-v", f"{self.workspace}:/workspace:rw",   # Mount workspace
            "-w", "/workspace",                        # Working directory
            f"--memory={self.memory_mb}m",             # Memory limit
            f"--cpus={self.cpu_limit}",                # CPU limit
        ]
        
        if not self.network:
            docker_cmd.append("--network=none")        # No network
        
        # Add environment variables
        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])
        
        # Add image and command
        docker_cmd.append(self.image)
        
        # Wrap command to install deps and run tests
        # This is a simple approach - production would use a custom image
        shell_cmd = (
            "pip install -q pytest 2>/dev/null; "
            "pip install -q -e . 2>/dev/null || true; "
            f"{' '.join(argv)}"
        )
        docker_cmd.extend(["sh", "-c", shell_cmd])
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=self.timeout_s,
            )
            
            stdout = result.stdout[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            stderr = result.stderr[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            
            return SandboxResult(
                ok=result.returncode == 0,
                returncode=result.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )
        
        except subprocess.TimeoutExpired:
            return SandboxResult(
                ok=False,
                returncode=-1,
                stdout="",
                stderr=f"Timed out after {self.timeout_s}s",
                timed_out=True,
            )
        except Exception as e:
            return SandboxResult(
                ok=False,
                returncode=-1,
                stdout="",
                stderr=str(e),
                timed_out=False,
            )


def run_tests_sandboxed(
    workspace: str,
    argv: List[str],
    timeout_s: int = _DEFAULT_TIMEOUT_S,
) -> Dict[str, Any]:
    """
    Convenience function matching controller._run_tests interface.
    
    Returns dict compatible with ExecResult.output
    """
    runner = DockerRunner(
        workspace=workspace,
        timeout_s=timeout_s,
        network=False,
    )
    
    if not runner.is_available():
        # Fall back to direct execution with warning
        return {
            "ok": False,
            "stdout": "",
            "stderr": "Docker not available - sandbox disabled",
            "returncode": -1,
        }
    
    result = runner.run_tests(argv)
    
    return {
        "ok": result.ok,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "sandboxed": True,
        "timed_out": result.timed_out,
    }


def run_pytest_in_docker(
    *,
    workspace: str,
    argv: list[str],
    timeout_s: int,
    network: bool = False,
    cpus: float = 1.0,
    mem_mb: int = 2048,
    image: str | None = None,
) -> dict[str, Any]:
    """
    API wrapper for kernel integration.

    Expected by controller.py when mode="docker".

    Args:
        workspace: Path to workspace
        argv: Test command, e.g. ["pytest", "-q"]
        timeout_s: Timeout in seconds
        network: Allow network access (default False)
        cpus: CPU limit (default 1.0)
        mem_mb: Memory limit in MB (default 2048)
        image: Docker image (default python:3.11-slim)

    Returns:
        Dict with returncode, stdout, stderr, meta
    """
    runner = DockerRunner(
        workspace=workspace,
        image=image or "python:3.11-slim",
        timeout_s=timeout_s,
        memory_mb=mem_mb,
        cpu_limit=str(cpus),
        network=network,
    )

    result = runner.run_tests(argv)

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "ok": result.ok,
        "meta": {
            "timed_out": result.timed_out,
            "sandboxed": True,
        },
    }
