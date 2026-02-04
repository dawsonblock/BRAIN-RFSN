# rfsn_kernel/gate.py
from __future__ import annotations

from typing import List, Set, Optional, Any
import os

from .types import StateSnapshot, Proposal, Action, Decision
from .envelopes import default_envelopes, validate_action_against_envelope
from .policy import DEFAULT_POLICY, KernelPolicy


def _norm_path(p: str) -> str:
    return os.path.abspath(p)


def gate(
    state: StateSnapshot,
    proposal: Proposal,
    policy: KernelPolicy | None = None,
    brain_state: Optional[Any] = None,
) -> Decision:
    """
    Pure, deterministic validator.
    - No I/O
    - No randomness
    - No clocks
    """
    if policy is None:
        policy = DEFAULT_POLICY
    envs = default_envelopes(state.workspace_root)

    reasons: List[str] = []
    approved: List[Action] = []
    denied: List[Action] = []

    # --- REFLEXIVE SAFETY (HARD OVERRIDES) ---
    is_panic = False
    if brain_state and hasattr(brain_state, "mode") and brain_state.mode == "PANIC":
        is_panic = True
    
    # Check notes for stress/panic if brain_state not passed directly
    if not is_panic and state.notes.get("mode") == "PANIC":
        is_panic = True

    if is_panic:
        # Emergency Lockdown: Max 1 action per proposal
        if len(proposal.actions) > 1:
            reasons.append("reflexive:panic_lockdown:single_action_only")

    # 1) No empty proposals
    if not proposal.actions:
        return Decision(
            status="DENY",
            reasons=("empty_proposal",),
            approved_actions=(),
            denied_actions=(),
        )

    # 2) Budget checks
    if len(proposal.actions) > policy.max_actions_per_proposal:
        reasons.append("policy:max_actions_per_proposal_exceeded")

    if len(proposal.actions) > state.budget_actions_remaining:
        reasons.append("budget:actions_exceeded")

    # 3) Ordering rules: write => must include RUN_TESTS after the last write
    write_names = {"WRITE_FILE", "APPLY_PATCH"}
    has_write = any(a.name in write_names for a in proposal.actions)

    if has_write and policy.require_tests_after_write:
        test_idxs = [i for i, a in enumerate(proposal.actions) if a.name == "RUN_TESTS"]
        if not test_idxs:
            reasons.append("order:missing_run_tests_after_write")
        else:
            last_write_idx = max(i for i, a in enumerate(proposal.actions) if a.name in write_names)
            if policy.enforce_write_then_tests and min(test_idxs) < last_write_idx:
                reasons.append("order:run_tests_before_last_write")

    # 4) Read-before-write rule (same proposal)
    read_paths: Set[str] = set()
    write_paths: Set[str] = set()
    for a in proposal.actions:
        if a.name == "READ_FILE" and "path" in a.args:
            read_paths.add(_norm_path(str(a.args["path"])))
        if a.name in write_names and "path" in a.args:
            write_paths.add(_norm_path(str(a.args["path"])))

    # Require read of each written path in the same proposal
    missing_reads = sorted(p for p in write_paths if p not in read_paths)
    if missing_reads:
        reasons.append("order:write_without_read_same_proposal")

    # 5) Validate each action against envelopes + policy
    for a in proposal.actions:
        # Reflexive Overrides
        deny_network = policy.deny_network
        if is_panic:
            deny_network = True # Force isolation in panic
            if a.name not in {"READ_FILE", "RUN_TESTS", "RECALL", "REMEMBER"}:
                 # In panic, only allow read, search or test (for recovery/debugging)
                 reasons.append(f"reflexive:panic_lockdown:action_denied:{a.name}")
                 denied.append(a)
                 continue

        # Explicitly deny RUN_CMD unless policy allows it
        if a.name == "RUN_CMD" and not policy.allow_run_cmd:
            reasons.append("policy:run_cmd_disabled")
            denied.append(a)
            continue

        if a.name not in envs:
            if policy.deny_unknown_actions:
                reasons.append(f"unknown_action:{a.name}")
                denied.append(a)
                continue
            denied.append(a)
            continue

        spec = envs[a.name]

        # CRITICAL: Enforce by envelope capability (NOT by optional args)
        if deny_network and spec.allow_network:
            reasons.append(f"policy:network_denied:{a.name}")
            denied.append(a)
            continue

        if policy.deny_shell and spec.allow_shell:
            reasons.append(f"policy:shell_denied:{a.name}")
            denied.append(a)
            continue

        v = validate_action_against_envelope(spec, a.args)
        if v is not None:
            reasons.append(f"envelope:{a.name}:{v}")
            denied.append(a)
            continue

        approved.append(a)

    if reasons:
        return Decision(
            status="DENY",
            reasons=tuple(sorted(set(reasons))),
            approved_actions=(),
            denied_actions=tuple(denied),
        )

    return Decision(status="ALLOW", reasons=(), approved_actions=tuple(approved), denied_actions=())
