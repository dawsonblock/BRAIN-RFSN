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
    ws = os.path.abspath(workspace_root)

    envs: Dict[str, EnvelopeSpec] = {
        # === File Operations ===
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
        # === Web Actions ===
        "WEB_SEARCH": EnvelopeSpec(
            name="WEB_SEARCH",
            max_wall_ms=30_000,
            allow_network=True,
            rate_limit_per_min=10,
            max_bytes=100_000,  # Max query size
        ),
        "BROWSE_URL": EnvelopeSpec(
            name="BROWSE_URL",
            max_wall_ms=60_000,
            allow_network=True,
            rate_limit_per_min=20,
            max_bytes=500_000,  # Max response size to store
            domain_allowlist=(),  # Empty = all domains allowed (can be restricted)
        ),
        # === Shell Execution ===
        "SHELL_EXEC": EnvelopeSpec(
            name="SHELL_EXEC",
            max_wall_ms=120_000,
            allow_network=False,
            allow_shell=True,
            path_roots=(ws,),
            max_bytes=1_000_000,
        ),
        # === Memory Actions ===
        "REMEMBER": EnvelopeSpec(
            name="REMEMBER",
            max_wall_ms=5_000,
            allow_network=False,
            max_bytes=100_000,  # Max memory chunk
        ),
        "RECALL": EnvelopeSpec(
            name="RECALL",
            max_wall_ms=10_000,
            allow_network=False,
            max_bytes=50_000,  # Max query size
        ),
        # === Agent Actions ===
        "DELEGATE": EnvelopeSpec(
            name="DELEGATE",
            max_wall_ms=300_000,  # 5 min for sub-agent
            allow_network=True,
            allow_shell=True,
            rate_limit_per_min=5,  # Limit spawning
        ),
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
