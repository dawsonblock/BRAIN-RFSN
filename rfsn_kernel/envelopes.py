# rfsn_kernel/envelopes.py
"""
Envelope specifications for kernel actions.
Envelopes define resource limits and containment rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import os


@dataclass(frozen=True)
class EnvelopeSpec:
    name: str
    max_wall_ms: int
    allow_network: bool = False
    allow_shell: bool = False
    path_roots: Tuple[str, ...] = ()
    max_bytes: int = 2_000_000
    max_lines_changed: int = 500  # For APPLY_PATCH


def default_envelopes(workspace_root: str) -> Dict[str, EnvelopeSpec]:
    """
    Kernel-only action envelopes.
    
    IMPORTANT: Web, memory, shell, and delegate actions are NOT kernel actions.
    They belong to upstream (rfsn_companion) and should never pass through the gate.
    """
    ws = os.path.abspath(workspace_root)

    return {
        "RUN_TESTS": EnvelopeSpec(
            name="RUN_TESTS",
            max_wall_ms=180_000,
            path_roots=(ws,),
        ),
        "READ_FILE": EnvelopeSpec(
            name="READ_FILE",
            max_wall_ms=5_000,
            path_roots=(ws,),
            max_bytes=1_000_000,
        ),
        "WRITE_FILE": EnvelopeSpec(
            name="WRITE_FILE",
            max_wall_ms=10_000,
            path_roots=(ws,),
            max_bytes=2_000_000,
        ),
        "APPLY_PATCH": EnvelopeSpec(
            name="APPLY_PATCH",
            max_wall_ms=20_000,
            path_roots=(ws,),
            max_bytes=2_000_000,
            max_lines_changed=500,
        ),
    }


def _is_under_roots(path: str, roots: Tuple[str, ...]) -> bool:
    ap = os.path.abspath(path)
    for r in roots:
        rr = os.path.abspath(r)
        if ap == rr or ap.startswith(rr + os.sep):
            return True
    return False


def validate_action_against_envelope(spec: EnvelopeSpec, action_args: Dict[str, Any]) -> Optional[str]:
    """
    Validate action arguments against envelope spec.
    Returns None if valid, or error string if invalid.
    """
    # Path containment checks
    if "path" in action_args:
        p = str(action_args["path"])
        if spec.path_roots and not _is_under_roots(p, spec.path_roots):
            return f"path_out_of_bounds:{p}"

    # Payload size checks
    if "content" in action_args:
        b = str(action_args["content"]).encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"content_too_large:{len(b)}"

    # Diff size checks (for APPLY_PATCH)
    if "diff" in action_args:
        diff_text = str(action_args["diff"])
        b = diff_text.encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"diff_too_large:{len(b)}"
        
        # Count changed lines in diff
        changed = 0
        for ln in diff_text.splitlines():
            if ln.startswith("+++ ") or ln.startswith("--- "):
                continue
            if ln.startswith("+") or ln.startswith("-"):
                changed += 1
        if changed > spec.max_lines_changed:
            return f"diff_lines_changed_exceeded:{changed}"

    # Legacy patch field (content replace)
    if "patch" in action_args:
        b = str(action_args["patch"]).encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"patch_too_large:{len(b)}"

    # Network checks
    if action_args.get("network", False) and not spec.allow_network:
        return "network_disallowed"

    # Shell/argv checks
    if "argv" in action_args and not spec.allow_shell:
        argv = action_args["argv"]
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            return "argv_invalid"
        joined = " ".join(argv)
        if "bash" in joined or "-lc" in joined or "sh" in joined:
            return "shell_disallowed"

    return None
