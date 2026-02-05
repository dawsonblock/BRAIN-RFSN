"""
Task loading + normalization.

Supports:
- JSON array:   [ {...}, {...} ]
- JSONL:        one JSON object per line

Normalization target schema:
  {
    "task_id": str,
    "repo": str,             # clone URL or local path
    "base_commit": str,      # git sha
    "instance_id": optional  # preserved if present
  }

This intentionally ignores other SWE-bench fields for now.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        return []
    if raw[0] == "[":
        return json.loads(raw)

    out: List[Dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def normalize_task(t: Dict[str, Any]) -> Dict[str, Any]:
    """
    Try common SWE-bench keys; fall back to minimal required keys.
    """
    # Common dataset keys seen in variants
    task_id = (
        t.get("task_id")
        or t.get("instance_id")
        or t.get("id")
        or t.get("problem_id")
        or ""
    )
    repo = t.get("repo") or t.get("repository") or t.get("repo_name") or ""
    base_commit = t.get("base_commit") or t.get("commit") or t.get("base_sha") or ""

    if not task_id or not repo or not base_commit:
        raise ValueError(f"Task missing required fields: task_id={task_id!r} repo={repo!r} base_commit={base_commit!r}")

    out = {
        "task_id": str(task_id),
        "repo": str(repo),
        "base_commit": str(base_commit),
    }
    if "instance_id" in t:
        out["instance_id"] = t["instance_id"]
    return out
