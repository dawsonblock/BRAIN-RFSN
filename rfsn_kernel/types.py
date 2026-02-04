# rfsn_kernel/types.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Literal, Tuple
import json
import hashlib


ActionType = Literal["READ_FILE", "WRITE_FILE", "APPLY_PATCH", "RUN_TESTS"]


@dataclass(frozen=True)
class StateSnapshot:
    workspace: str
    notes: Dict[str, Any]


@dataclass(frozen=True)
class Action:
    type: ActionType
    payload: Dict[str, Any]


@dataclass(frozen=True)
class Proposal:
    """Upstream proposes a sequence of actions. Kernel decides allow/deny and executes if allowed."""
    actions: Tuple[Action, ...]
    meta: Dict[str, Any]


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    approved_actions: Tuple[Action, ...]


@dataclass(frozen=True)
class ExecResult:
    ok: bool
    action: Action
    output: Dict[str, Any]


def dataclass_to_dict(x: Any) -> Any:
    if hasattr(x, "__dataclass_fields__"):
        return asdict(x)
    if isinstance(x, tuple):
        return [dataclass_to_dict(v) for v in x]
    if isinstance(x, list):
        return [dataclass_to_dict(v) for v in x]
    if isinstance(x, dict):
        return {k: dataclass_to_dict(v) for k, v in x.items()}
    return x


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
