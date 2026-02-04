# rfsn_companion/selectors/traceback_selector.py
from __future__ import annotations

from typing import List
import os
import re
from collections import Counter


# Standard Python traceback format: File "path", line N
_FILE_RE = re.compile(r'File "([^"]+)", line (\d+)')

# Pytest format: path.py:line (various patterns)
_PYTEST_RE = re.compile(r'^([^\s:]+\.py):(\d+)', re.MULTILINE)

# Also match "path.py:line: AssertionError" style
_PYTEST_COLON_RE = re.compile(r'([^\s]+\.py):(\d+):')


def _is_under_workspace(path: str, workspace_root: str) -> bool:
    ap = os.path.abspath(path)
    ws = os.path.abspath(workspace_root)
    return ap == ws or ap.startswith(ws + os.sep)


def _resolve_path(path: str, workspace_root: str) -> str:
    """Resolve a potentially relative path to absolute."""
    if os.path.isabs(path):
        return os.path.abspath(path)
    # Try relative to workspace
    candidate = os.path.join(workspace_root, path)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    return os.path.abspath(path)


def select_candidate_paths(trace_text: str, workspace_root: str, k: int = 3) -> List[str]:
    """
    Deterministic:
    - extract File "...", line N frames (Python tracebacks)
    - extract path.py:line patterns (pytest output)
    - keep only paths under workspace_root
    - count frequency
    - sort by (-count, path)
    """
    ws = os.path.abspath(workspace_root)
    hits: List[str] = []

    # Standard Python traceback
    for m in _FILE_RE.finditer(trace_text or ""):
        p = m.group(1)
        if not p:
            continue
        ap = _resolve_path(p, ws)
        if _is_under_workspace(ap, ws) and os.path.exists(ap):
            hits.append(ap)

    # Pytest format
    for m in _PYTEST_RE.finditer(trace_text or ""):
        p = m.group(1)
        if not p:
            continue
        ap = _resolve_path(p, ws)
        if _is_under_workspace(ap, ws) and os.path.exists(ap):
            hits.append(ap)

    # Pytest colon format
    for m in _PYTEST_COLON_RE.finditer(trace_text or ""):
        p = m.group(1)
        if not p:
            continue
        ap = _resolve_path(p, ws)
        if _is_under_workspace(ap, ws) and os.path.exists(ap):
            hits.append(ap)

    if not hits:
        return []

    c = Counter(hits)
    ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
    return [p for p, _ in ranked[: max(0, int(k))]]
