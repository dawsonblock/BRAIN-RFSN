# rfsn_kernel/envelopes.py
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
    max_lines_changed: int = 2_000
    rate_limit_per_min: int = 0  # 0 = no limit
    domain_allowlist: Tuple[str, ...] = ()  # For web actions


def default_envelopes(workspace_root: str) -> Dict[str, EnvelopeSpec]:
    """
    Kernel-only action envelopes.
    
    IMPORTANT: Web, memory, shell, and delegate actions are NOT kernel actions.
    They belong to upstream (rfsn_companion) and should never pass through the gate.
    """
    ws = os.path.abspath(workspace_root)

    envs: Dict[str, EnvelopeSpec] = {
        # === File Operations (Kernel-Only) ===
        "RUN_TESTS": EnvelopeSpec(
            name="RUN_TESTS",
            max_wall_ms=180_000,
            allow_network=False,
            allow_shell=False,
            path_roots=(ws,),
        ),
        "READ_FILE": EnvelopeSpec(
            name="READ_FILE",
            max_wall_ms=5_000,
            allow_network=False,
            allow_shell=False,
            path_roots=(ws,),
            max_bytes=1_000_000,
        ),
        "WRITE_FILE": EnvelopeSpec(
            name="WRITE_FILE",
            max_wall_ms=10_000,
            allow_network=False,
            allow_shell=False,
            path_roots=(ws,),
            max_bytes=2_000_000,
            max_lines_changed=2_000,
        ),
        "APPLY_PATCH": EnvelopeSpec(
            name="APPLY_PATCH",
            max_wall_ms=20_000,
            allow_network=False,
            allow_shell=False,
            path_roots=(ws,),
            max_bytes=2_000_000,
            max_lines_changed=2_000,
        ),
        # NOTE: WEB_SEARCH, BROWSE_URL, SHELL_EXEC, REMEMBER, RECALL, DELEGATE
        # have been removed from kernel. They belong to upstream_learner/rfsn_companion.
    }

    return envs


def _is_under_roots(path: str, roots: Tuple[str, ...]) -> bool:
    ap = os.path.abspath(path)
    for r in roots:
        rr = os.path.abspath(r)
        if ap == rr or ap.startswith(rr + os.sep):
            return True
    return False


def validate_action_against_envelope(spec: EnvelopeSpec, action_args: Dict[str, Any]) -> Optional[str]:
    # Path checks
    if "path" in action_args:
        p = str(action_args["path"])
        if spec.path_roots and not _is_under_roots(p, spec.path_roots):
            return f"path_out_of_bounds:{p}"
    if "paths" in action_args:
        paths = action_args["paths"]
        if not isinstance(paths, list):
            return "paths_not_list"
        for p in paths:
            ps = str(p)
            if spec.path_roots and not _is_under_roots(ps, spec.path_roots):
                return f"path_out_of_bounds:{ps}"

    # Payload size checks
    if "content" in action_args:
        b = str(action_args["content"]).encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"content_too_large:{len(b)}"
    if "patch" in action_args:
        b = str(action_args["patch"]).encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"patch_too_large:{len(b)}"
    if "query" in action_args:
        b = str(action_args["query"]).encode("utf-8", errors="replace")
        if len(b) > spec.max_bytes:
            return f"query_too_large:{len(b)}"

    # URL domain checks
    if "url" in action_args and spec.domain_allowlist:
        url = str(action_args["url"])
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if domain and not any(domain.endswith(d) for d in spec.domain_allowlist):
            return f"domain_not_allowed:{domain}"

    # Network checks
    if action_args.get("network", False) and not spec.allow_network:
        return "network_disallowed"

    # Shell checks
    if "argv" in action_args and not spec.allow_shell:
        argv = action_args["argv"]
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            return "argv_invalid"
        joined = " ".join(argv)
        if "bash" in joined or "-lc" in joined or "sh" in joined:
            return "shell_disallowed"

    # Command string checks for SHELL_EXEC
    if "command" in action_args:
        if not spec.allow_shell:
            return "shell_disallowed"
        cmd = str(action_args["command"])
        # Block dangerous commands
        dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /"]
        for d in dangerous:
            if d in cmd:
                return f"dangerous_command:{d}"

    return None
