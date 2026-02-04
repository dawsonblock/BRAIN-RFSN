from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import os
import re


@dataclass(frozen=True)
class PatchFile:
    old_path: Optional[str]
    new_path: Optional[str]


_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)\s*$")
_OLD_RE = re.compile(r"^---\s+(.*)\s*$")
_NEW_RE = re.compile(r"^\+\+\+\s+(.*)\s*$")


def _strip_prefix(p: str) -> str:
    p = p.strip()
    if p.startswith("a/") or p.startswith("b/"):
        return p[2:]
    return p


def _normalize_rel(p: str) -> str:
    p = p.strip().replace("\\", "/")
    # git uses /dev/null for adds/deletes
    if p == "/dev/null":
        return p
    # disallow absolute paths and drive letters
    if p.startswith("/") or re.match(r"^[A-Za-z]:/", p):
        raise ValueError(f"absolute path in patch: {p}")
    # collapse
    norm = os.path.normpath(p).replace("\\", "/")
    # normpath can produce "."; treat as invalid
    if norm in (".", ""):
        raise ValueError(f"invalid patch path: {p}")
    # disallow traversal
    if norm.startswith("../") or norm == ".." or "/../" in f"/{norm}/":
        raise ValueError(f"path traversal in patch: {p}")
    return norm


def parse_unified_diff_files(patch_text: str) -> List[PatchFile]:
    """
    Parse a unified diff and extract file pairs.
    Supports either:
      - `diff --git a/X b/Y` headers (preferred)
      - `--- X` / `+++ Y` pairs
    Returns a list of PatchFile(old_path,new_path) where paths are repo-relative (no a/ b/),
    or '/dev/null' for add/delete sides.
    """
    if not isinstance(patch_text, str) or not patch_text.strip():
        return []

    files: List[PatchFile] = []
    last_old: Optional[str] = None
    last_new: Optional[str] = None

    lines = patch_text.splitlines()
    for line in lines:
        m = _DIFF_HEADER_RE.match(line)
        if m:
            a_path = _normalize_rel(_strip_prefix(f"a/{m.group(1)}"))
            b_path = _normalize_rel(_strip_prefix(f"b/{m.group(2)}"))
            files.append(PatchFile(old_path=a_path, new_path=b_path))
            last_old = None
            last_new = None
            continue

        m = _OLD_RE.match(line)
        if m:
            raw = m.group(1).strip()
            raw = _strip_prefix(raw)
            last_old = _normalize_rel(raw)
            continue

        m = _NEW_RE.match(line)
        if m:
            raw = m.group(1).strip()
            raw = _strip_prefix(raw)
            last_new = _normalize_rel(raw)
            if last_old is not None:
                files.append(PatchFile(old_path=last_old, new_path=last_new))
                last_old = None
                last_new = None
            continue

    return files


def patch_paths_are_confined(workspace: str, patch_text: str) -> Tuple[bool, str, List[PatchFile]]:
    """
    Enforce that every touched file path (old/new) is inside the workspace when resolved.
    Also rejects absolute paths and traversal during parsing.
    """
    ws = os.path.abspath(workspace)
    try:
        files = parse_unified_diff_files(patch_text)
    except Exception as e:
        return False, f"patch parse rejected: {e}", []

    if not files:
        return False, "patch contains no file headers", []

    def in_ws(rel: str) -> bool:
        if rel == "/dev/null":
            return True
        ap = os.path.abspath(os.path.join(ws, rel))
        try:
            return os.path.commonpath([ws, ap]) == ws
        except ValueError:
            return False

    for pf in files:
        for rel in (pf.old_path, pf.new_path):
            if rel is None:
                continue
            if not in_ws(rel):
                return False, f"patch path escapes workspace: {rel}", files

    return True, "OK", files
