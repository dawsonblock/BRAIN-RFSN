# rfsn_kernel/sandbox/sandbox_adapter.py
from __future__ import annotations

from typing import Any, Dict, List
import subprocess
import time


def run_cmd(
    argv: List[str],
    cwd: str,
    timeout_ms: int,
    network: bool = False,
) -> Dict[str, Any]:
    """
    Minimal execution adapter. You should harden this later:
    - namespace/container
    - resource limits
    - seccomp
    - no network enforcement
    For now: deterministic wrapper around subprocess.
    """
    start = time.perf_counter()
    try:
        p = subprocess.run(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(1, timeout_ms / 1000.0),
        )
        dur = int((time.perf_counter() - start) * 1000)
        return {
            "ok": (p.returncode == 0),
            "stdout": p.stdout,
            "stderr": p.stderr,
            "exit_code": int(p.returncode),
            "duration_ms": dur,
        }
    except subprocess.TimeoutExpired as ex:
        dur = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "stdout": ex.stdout or "",
            "stderr": (ex.stderr or "") + "\nTIMEOUT",
            "exit_code": 124,
            "duration_ms": dur,
        }
