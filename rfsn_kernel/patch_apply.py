# rfsn_kernel/patch_apply.py
"""
Unified diff parser and applier.
Pure Python implementation - no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re


@dataclass(frozen=True)
class Hunk:
    """A single hunk from a unified diff."""
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: List[str]  # Each line begins with ' ', '+', '-'


_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


def parse_unified_diff(diff_text: str) -> Tuple[List[Tuple[str, str, str]], int]:
    """
    Parse a unified diff into files and count changed lines.
    
    Returns:
        files: list of (old_path, new_path, file_diff_text)
        changed_lines: int (sum of + and - lines across all hunks)
    
    Supports standard unified diff with ---/+++ headers and @@ hunks.
    """
    lines = diff_text.splitlines(keepends=True)
    files: List[Tuple[str, str, str]] = []

    cur_old: Optional[str] = None
    cur_new: Optional[str] = None
    buf: List[str] = []
    changed = 0

    def flush():
        nonlocal buf, cur_old, cur_new
        if cur_old is not None and cur_new is not None and buf:
            files.append((cur_old, cur_new, "".join(buf)))
        buf = []

    for ln in lines:
        if ln.startswith("--- "):
            flush()
            cur_old = ln[4:].strip()
            buf.append(ln)
            continue
        if ln.startswith("+++ "):
            cur_new = ln[4:].strip()
            buf.append(ln)
            continue
        if ln.startswith("@@ "):
            buf.append(ln)
            continue

        # Count changed lines (excluding file headers)
        if ln.startswith("+") and not ln.startswith("+++ "):
            changed += 1
        elif ln.startswith("-") and not ln.startswith("--- "):
            changed += 1

        buf.append(ln)

    flush()
    return files, changed


def _parse_hunks(file_diff_text: str) -> List[Hunk]:
    """Parse hunks from a single file's diff text."""
    lines = file_diff_text.splitlines(keepends=False)
    hunks: List[Hunk] = []
    i = 0
    
    while i < len(lines):
        ln = lines[i]
        m = _HUNK_RE.match(ln)
        if not m:
            i += 1
            continue
            
        old_start = int(m.group(1))
        old_len = int(m.group(2) or "1")
        new_start = int(m.group(3))
        new_len = int(m.group(4) or "1")
        i += 1
        
        hunk_lines: List[str] = []
        while i < len(lines):
            l2 = lines[i]
            if l2.startswith("@@ "):
                break
            if l2.startswith((" ", "+", "-")):
                hunk_lines.append(l2)
                i += 1
                continue
            # Allow "\ No newline at end of file" and other metadata
            if l2.startswith("\\"):
                i += 1
                continue
            # Unknown line; treat as context break
            i += 1
            
        hunks.append(Hunk(old_start, old_len, new_start, new_len, hunk_lines))
    
    return hunks


def apply_unified_diff_to_text(original: str, file_diff_text: str) -> str:
    """
    Apply hunks from a unified diff to file text.
    
    Args:
        original: The original file content
        file_diff_text: The diff text for this specific file
        
    Returns:
        The patched file content
        
    Raises:
        ValueError: If the diff cannot be applied (context mismatch, etc.)
    """
    orig_lines = original.splitlines(keepends=False)
    out: List[str] = []
    hunks = _parse_hunks(file_diff_text)
    
    # Current position in orig_lines (0-based)
    cur = 0

    for h in hunks:
        # Hunk old_start is 1-based line number
        target = h.old_start - 1
        if target < 0:
            raise ValueError("invalid_hunk_old_start")

        # Copy unchanged lines before hunk
        if target < cur:
            raise ValueError("overlapping_hunks")
        out.extend(orig_lines[cur:target])
        cur = target

        # Apply hunk lines
        for hl in h.lines:
            if not hl:
                # Empty line in diff is valid; treat as context line with ""
                prefix = " "
                content = ""
            else:
                prefix = hl[0]
                content = hl[1:]

            if prefix == " ":
                # Context line - must match original
                if cur >= len(orig_lines) or orig_lines[cur] != content:
                    raise ValueError("context_mismatch")
                out.append(orig_lines[cur])
                cur += 1
            elif prefix == "-":
                # Delete line - must match original
                if cur >= len(orig_lines) or orig_lines[cur] != content:
                    raise ValueError("delete_mismatch")
                cur += 1
            elif prefix == "+":
                # Add line
                out.append(content)
            else:
                raise ValueError("invalid_diff_line_prefix")

    # Copy remaining original lines after last hunk
    out.extend(orig_lines[cur:])

    # Preserve trailing newline if original had it
    if original.endswith("\n"):
        return "\n".join(out) + "\n"
    return "\n".join(out)


def normalize_diff_path(p: str) -> str:
    """
    Normalize a path from diff header, stripping a/ b/ prefixes.
    """
    p = p.strip()
    if p in ("/dev/null", "dev/null"):
        return p
    if p.startswith("a/") or p.startswith("b/"):
        return p[2:]
    return p
