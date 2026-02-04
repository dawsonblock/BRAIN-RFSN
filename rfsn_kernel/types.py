# rfsn_kernel/types.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Tuple, Literal
import json
import hashlib


DecisionStatus = Literal["ALLOW", "DENY"]
KernelMode = Literal["NORMAL", "PANIC"]


@dataclass(frozen=True)
class StateSnapshot:
    """
    Deterministic snapshot inputs for gate().

    Keep this minimal and stable. The kernel should not depend on live world state
    that changes nondeterministically unless you explicitly record it into the ledger.
    """
    task_id: str
    workspace_root: str
    step: int = 0
    budget_actions_remaining: int = 50
    budget_wall_ms_remaining: int = 300_000  # 5 min default
    mode: KernelMode = "NORMAL"  # Kernel-native panic field (no cognitive leakage)
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """
    Typed action with explicit name and args.
    The gate validates name+args against envelopes.
    """
    name: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Proposal:
    """
    Companion output. Must be side-effect free to produce.
    """
    proposal_id: str
    actions: Tuple[Action, ...]
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    status: DecisionStatus
    reasons: Tuple[str, ...] = ()
    approved_actions: Tuple[Action, ...] = ()
    denied_actions: Tuple[Action, ...] = ()
    transforms: Dict[str, Any] = field(default_factory=dict)  # optional rewrites


@dataclass(frozen=True)
class ExecResult:
    action: Action
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    artifacts: Dict[str, Any] = field(default_factory=dict)


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON for hashing/replay consistency.
    - sort keys
    - no whitespace
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def dataclass_to_dict(dc: Any) -> Any:
    """
    Safe conversion for dataclasses to JSON-serializable dict.
    """
    if hasattr(dc, "__dataclass_fields__"):
        return asdict(dc)
    return dc
