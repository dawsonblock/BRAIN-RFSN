# rfsn_kernel/policy.py
"""
Kernel policy is STATIC. It defines hard limits and order rules.
Learning belongs upstream - not here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KernelPolicy:
    """
    Kernel policy defines hard limits and order rules.
    These are NOT learned - they are enforced deterministically.
    """
    max_actions_per_proposal: int = 20

    require_tests_after_write: bool = True
    enforce_write_then_tests: bool = True

    deny_unknown_actions: bool = True
    deny_shell: bool = True
    deny_network: bool = True

    # Dangerous surface; keep off until you have a real sandbox + allowlist.
    allow_run_cmd: bool = False

    # Patch safety caps (gate-level enforcement)
    max_patch_files: int = 8
    max_lines_changed: int = 500


DEFAULT_POLICY = KernelPolicy()
