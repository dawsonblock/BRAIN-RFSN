# upstream_learner/failing_tests.py
"""
Parse failing test node IDs from pytest output.
Used by trajectory episodes for targeted test selection.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List


_FAILED_RE = re.compile(r"^FAILED\s+(.+)$")
_NODEID_RE = re.compile(r"^(.+::.+)$")  # Matches test_file.py::test_name format


def parse_failed_nodeids_from_text(text: str) -> List[str]:
    """
    Parse pytest output to extract failed test node IDs.
    
    Matches patterns like:
        FAILED tests/test_foo.py::test_bar - AssertionError
        FAILED tests/test_foo.py::TestClass::test_method - ...
    
    Returns:
        List of unique test node IDs in order of appearance.
    """
    out: List[str] = []
    for ln in text.splitlines():
        m = _FAILED_RE.match(ln.strip())
        if m:
            # Extract the node ID part (before any " - " error message)
            cand = m.group(1).strip()
            if " - " in cand:
                cand = cand.split(" - ")[0].strip()
            if _NODEID_RE.match(cand):
                out.append(cand)
    
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def read_failed_nodeids(workspace_root: str) -> List[str]:
    """
    Read failed test node IDs from the last test run artifact.
    
    Args:
        workspace_root: Path to the workspace directory.
        
    Returns:
        List of failed test node IDs, or empty list if no artifact exists.
    """
    p = Path(workspace_root) / ".rfsn" / "last_tests.txt"
    if not p.exists():
        return []
    try:
        return parse_failed_nodeids_from_text(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
