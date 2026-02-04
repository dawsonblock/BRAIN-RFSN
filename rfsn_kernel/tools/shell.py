# rfsn_kernel/tools/shell.py
"""Sandboxed shell execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
import subprocess
import os


@dataclass
class ShellResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None


def shell_exec(
    command: str,
    cwd: Optional[str] = None,
    timeout_seconds: int = 60,
    env: Optional[dict] = None,
) -> ShellResult:
    """
    Execute a shell command with safety constraints.
    
    Safety:
    - Runs in specified cwd (defaults to /tmp)
    - Has timeout
    - Captures output
    - Does NOT run in a full sandbox (for that, use Docker)
    """
    working_dir = cwd or "/tmp"

    # Merge environment
    shell_env = os.environ.copy()
    if env:
        shell_env.update(env)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=shell_env,
        )

        return ShellResult(
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return ShellResult(
            command=command,
            stdout="",
            stderr="",
            exit_code=-1,
            error=f"Command timed out after {timeout_seconds}s",
        )
    except Exception as e:
        return ShellResult(
            command=command,
            stdout="",
            stderr="",
            exit_code=-1,
            error=str(e),
        )


def shell_exec_safe(
    command: str,
    cwd: str,
    allowed_commands: Optional[List[str]] = None,
    timeout_seconds: int = 60,
) -> ShellResult:
    """
    Execute shell command with command allowlist.
    
    Args:
        command: The command string
        cwd: Working directory (must be specified)
        allowed_commands: List of allowed command prefixes (e.g., ["git", "python", "pip"])
        timeout_seconds: Max execution time
    """
    # Validate command against allowlist
    if allowed_commands:
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return ShellResult(
                command=command,
                stdout="",
                stderr="",
                exit_code=-1,
                error="Empty command",
            )

        base_cmd = os.path.basename(cmd_parts[0])
        if base_cmd not in allowed_commands:
            return ShellResult(
                command=command,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Command '{base_cmd}' not in allowlist: {allowed_commands}",
            )

    return shell_exec(command, cwd=cwd, timeout_seconds=timeout_seconds)
