# rfsn_kernel/gate.py
from __future__ import annotations

from typing import List, Set
import os

from .types import StateSnapshot, Proposal, Action, Decision
from .envelopes import default_envelopes, validate_action_against_envelope
from .policy import DEFAULT_POLICY, KernelPolicy
from .patch_apply import parse_unified_diff


def _norm_path(p: str) -> str:
    return os.path.abspath(p)


# ----------------------------
# RUN_TESTS allowlist (HARD SECURITY BOUNDARY)
# ----------------------------
def _normalize_test_argv(argv: List[str]) -> List[str]:
    """Normalize argv for robust matching."""
    return [str(x).strip() for x in argv]


def is_allowed_tests_argv(argv: List[str]) -> bool:
    """
    Only allow a small set of safe, deterministic test invocations.
    No arbitrary python -c, no arbitrary binaries, no curl, no rm, etc.
    
    Allowlisted forms:
      python -m pytest -q [optional flags]
      python -m pytest -q -k <expr>
      python -m pytest -q --maxfail=N
    """
    a = _normalize_test_argv(argv)
    if not a:
        return False

    # Require: python -m pytest (at minimum)
    if len(a) < 3:
        return False
    if a[0] != "python" or a[1] != "-m" or a[2] != "pytest":
        return False

    # Allowed flags (subset)
    allowed_flags = {"-q", "-x", "--tb=short", "--tb=no", "-v"}
    
    i = 3
    saw_q = False
    while i < len(a):
        tok = a[i]
        
        # Check for -q flag
        if tok == "-q":
            saw_q = True
            i += 1
            continue
        
        # Allow simple flags
        if tok in allowed_flags:
            i += 1
            continue
        
        # Allow -k <expr> for test selection
        if tok == "-k":
            if i + 1 >= len(a):
                return False
            expr = a[i + 1]
            if not isinstance(expr, str) or not expr:
                return False
            # Block injection attempts
            if any(c in expr for c in [";", "|", "&", "`", "$", ">"]):
                return False
            i += 2
            continue
        
        # Allow --maxfail=N
        if tok.startswith("--maxfail="):
            try:
                int(tok.split("=")[1])
                i += 1
                continue
            except (ValueError, IndexError):
                return False
        
        # Disallow everything else (paths, plugins, --pyargs, -c, etc.)
        return False
    
    # Require -q to limit output
    return saw_q


def gate(
    state: StateSnapshot,
    proposal: Proposal,
    policy: KernelPolicy | None = None,
) -> Decision:
    """
    Pure, deterministic validator.
    - No I/O
    - No randomness
    - No clocks
    - No cognitive leakage (brain_state removed)
    """
    if policy is None:
        policy = DEFAULT_POLICY
    envs = default_envelopes(state.workspace_root)
    ws = os.path.abspath(state.workspace_root)

    reasons: List[str] = []
    approved: List[Action] = []
    denied: List[Action] = []

    # --- REFLEXIVE SAFETY (HARD OVERRIDES) ---
    # Panic mode is now a first-class kernel concept via state.mode
    is_panic = state.mode == "PANIC"

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
    # Normalize paths relative to workspace_root (not CWD)
    def _resolve_path(p: str) -> str:
        if os.path.isabs(p):
            return os.path.abspath(p)
        return os.path.abspath(os.path.join(ws, p))

    read_paths: Set[str] = set()
    write_paths: Set[str] = set()
    for a in proposal.actions:
        if a.name == "READ_FILE" and "path" in a.args:
            read_paths.add(_resolve_path(str(a.args["path"])))
        if a.name in write_names and "path" in a.args:
            write_paths.add(_resolve_path(str(a.args["path"])))

    # Require read of each written path in the same proposal
    missing_reads = sorted(p for p in write_paths if p not in read_paths)
    if missing_reads:
        reasons.append("order:write_without_read_same_proposal")

    # 5) Validate each action against envelopes + policy
    for a in proposal.actions:
        # Reflexive Overrides
        deny_network = policy.deny_network
        if is_panic:
            deny_network = True  # Force isolation in panic
            # In panic, only allow kernel-only read/test actions (no write)
            if a.name not in {"READ_FILE", "RUN_TESTS"}:
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

        # Resolve paths relative to workspace_root before envelope validation
        action_args_resolved = dict(a.args)
        if "path" in action_args_resolved:
            action_args_resolved["path"] = _resolve_path(str(action_args_resolved["path"]))

        v = validate_action_against_envelope(spec, action_args_resolved)
        if v is not None:
            reasons.append(f"envelope:{a.name}:{v}")
            denied.append(a)
            continue

        # CRITICAL: RUN_TESTS allowlist enforcement
        if a.name == "RUN_TESTS":
            argv = a.args.get("argv")
            if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
                reasons.append("tests_argv_invalid")
                denied.append(a)
                continue
            if not is_allowed_tests_argv(argv):
                reasons.append("tests_argv_not_allowlisted")
                denied.append(a)
                continue

        # CRITICAL: APPLY_PATCH enforcement (file count + line change caps)
        if a.name == "APPLY_PATCH":
            diff = a.args.get("diff")
            if not isinstance(diff, str) or not diff.strip():
                reasons.append("patch:missing_diff")
                denied.append(a)
                continue

            files, changed = parse_unified_diff(diff)
            # Policy-level caps (gate enforcement)
            if len(files) > policy.max_patch_files:
                reasons.append(f"patch:max_patch_files_exceeded:{len(files)}")
                denied.append(a)
                continue
            if changed > policy.max_lines_changed:
                reasons.append(f"patch:max_lines_changed_exceeded:{changed}")
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

