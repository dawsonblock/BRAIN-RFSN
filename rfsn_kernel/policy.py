# rfsn_kernel/policy.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KernelPolicy:
    """
    Kernel policy is static. It defines hard limits and order rules.
    Learning belongs upstream.
    """
    max_actions_per_proposal: int = 20

    require_tests_after_write: bool = True
    enforce_write_then_tests: bool = True

    deny_unknown_actions: bool = True
    deny_shell: bool = True
    deny_network: bool = True

    # Dangerous surface; keep off until you have a real sandbox + allowlist.
    allow_run_cmd: bool = False


DEFAULT_POLICY = KernelPolicy()
