# context_builder.py
"""
Deterministic context builder that uses ONLY kernel-approved primitives:
- LIST_DIR
- GREP
- READ_FILE

Goal:
Given failing pytest output, build a capped context pack:
- pick likely file paths from tracebacks
- grep for referenced symbols / exception names
- read top-ranked files (byte budgeted)
- return a single prompt-ready text blob

Design constraints:
- deterministic ordering (stable sort)
- hard budgets (bytes / files / grep results)
- no recursion beyond LIST_DIR (we use GREP to locate content instead)
- no shell execution except through kernel controller

Integration:
- Use build_context_pack(...) from rfsn_swe_agent.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from rfsn_kernel.types import Action, Proposal, StateSnapshot
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger


_TRACEBACK_FILE_RE = re.compile(r'File "([^"]+)", line (\d+), in ([^\n]+)')
_EXCEPTION_NAME_RE = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*Error|Exception|AssertionError)\b")
_IMPORT_FROM_RE = re.compile(r"(?m)^\s*from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)")
_IMPORT_RE = re.compile(r"(?m)^\s*import\s+([a-zA-Z0-9_.]+)")
_SYMBOL_RE = re.compile(r"(?m)\b([A-Za-z_][A-Za-z0-9_]{2,})\b")


@dataclass(frozen=True)
class ContextFile:
    path: str
    text: str
    score: float
    why: str


@dataclass(frozen=True)
class ContextPack:
    files: Tuple[ContextFile, ...]
    meta: Dict[str, object]


def _now_meta() -> Dict[str, object]:
    return {}


def _cap_tail(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[-n:]


def _is_rel_path(p: str) -> bool:
    p = (p or "").strip().replace("\\", "/")
    if not p:
        return False
    if p.startswith("/"):
        return False
    if ":" in p.split("/")[0]:
        return False
    return True


def _uniq(seq: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _extract_traceback_paths(pytest_text: str, *, limit: int = 20) -> List[str]:
    out: List[str] = []
    for m in _TRACEBACK_FILE_RE.finditer(pytest_text):
        p = m.group(1).strip()
        if _is_rel_path(p):
            out.append(p)
        if len(out) >= limit:
            break
    return _uniq(out)


def _extract_exception_names(pytest_text: str, *, limit: int = 12) -> List[str]:
    names: List[str] = []
    for m in _EXCEPTION_NAME_RE.finditer(pytest_text):
        nm = m.group(1).strip()
        if nm not in names:
            names.append(nm)
        if len(names) >= limit:
            break
    return names


def _extract_symbols(pytest_text: str, *, limit: int = 20) -> List[str]:
    """
    Pull a few mid-length identifiers from the tail of output (where failures tend to be).
    This is intentionally noisy but deterministic.
    """
    tail = _cap_tail(pytest_text, 50_000)
    toks = _SYMBOL_RE.findall(tail)
    bad = {
        "Traceback", "Assertion", "FAILED", "ERROR", "Exception", "pytest",
        "line", "File", "return", "raise", "True", "False", "None",
    }
    out: List[str] = []
    for t in toks:
        if t in bad:
            continue
        if len(t) > 3 and t.isupper():
            continue
        if t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _score_path(p: str) -> float:
    """Simple deterministic prior: tests and core modules are often most relevant."""
    s = 0.0
    if p.startswith("tests/") or "/tests/" in p:
        s += 2.0
    if p.endswith(".py"):
        s += 1.0
    if p.endswith(".toml") or p.endswith(".cfg") or p.endswith(".ini"):
        s += 0.5
    if p.endswith("conftest.py"):
        s += 1.0
    return s


def _run_step(*, ledger_path: str, state: StateSnapshot, proposal: Proposal):
    """Minimal step runner: gate + execute + ledger append."""
    decision = gate(state, proposal)
    results = ()
    if decision.allowed:
        results = execute_decision(state, decision)
    append_ledger(
        ledger_path,
        state=state,
        proposal=proposal,
        decision=decision,
        results=results,
        meta={"purpose": "context_builder", **_now_meta()},
    )
    return decision, results


def _listdir(*, ledger_path: str, workspace: str, task_id: str, path: str) -> List[Dict[str, object]]:
    st = StateSnapshot(workspace=workspace, notes={"task_id": task_id, "phase": "context_listdir"})
    prop = Proposal(actions=(Action("LIST_DIR", {"path": path}),), meta={"path": path})
    d, res = _run_step(ledger_path=ledger_path, state=st, proposal=prop)
    if not d.allowed or not res:
        return []
    r0 = res[0]
    if not r0.ok:
        return []
    entries = r0.output.get("entries")
    if isinstance(entries, list):
        return [x for x in entries if isinstance(x, dict)]
    return []


def _grep(*, ledger_path: str, workspace: str, task_id: str, pattern: str, path: str = ".", fixed_string: bool = True) -> List[Dict[str, object]]:
    st = StateSnapshot(workspace=workspace, notes={"task_id": task_id, "phase": "context_grep"})
    prop = Proposal(
        actions=(Action("GREP", {"pattern": pattern, "path": path, "fixed_string": fixed_string}),),
        meta={"pattern": pattern, "path": path},
    )
    d, res = _run_step(ledger_path=ledger_path, state=st, proposal=prop)
    if not d.allowed or not res:
        return []
    r0 = res[0]
    if not r0.ok:
        return []
    matches = r0.output.get("matches")
    if isinstance(matches, list):
        # matches are lines like "/path/to/file.py:123:content"
        hits: List[Dict[str, object]] = []
        for line in matches:
            if not isinstance(line, str):
                continue
            parts = line.split(":", 2)
            if len(parts) >= 2:
                hits.append({"path": parts[0], "line": parts[1], "text": parts[2] if len(parts) > 2 else ""})
        return hits
    return []


def _read_file(*, ledger_path: str, workspace: str, task_id: str, path: str) -> Optional[str]:
    st = StateSnapshot(workspace=workspace, notes={"task_id": task_id, "phase": "context_read"})
    prop = Proposal(actions=(Action("READ_FILE", {"path": path}),), meta={"path": path})
    d, res = _run_step(ledger_path=ledger_path, state=st, proposal=prop)
    if not d.allowed or not res:
        return None
    r0 = res[0]
    if not r0.ok:
        return None
    txt = r0.output.get("text")
    return txt if isinstance(txt, str) else None


def build_context_pack(
    *,
    ledger_path: str,
    workspace: str,
    task_id: str,
    pytest_stdout: str,
    pytest_stderr: str,
    focus_paths: Optional[Sequence[str]] = None,
    max_files: int = 12,
    max_total_bytes: int = 240_000,
    max_per_file_bytes: int = 60_000,
    max_grep_patterns: int = 10,
    include_traceback_files: bool = True,
    include_imports: bool = False,
    include_grep_expansion: bool = True,
    deep_grep: bool = False,
    minimal_mode: bool = False,
) -> ContextPack:
    """Returns a deterministic ranked set of files with capped text."""
    combined = (pytest_stdout or "") + "\n" + (pytest_stderr or "")
    
    trace_paths: List[str] = []
    if include_traceback_files:
        trace_paths = _extract_traceback_paths(combined, limit=20)
        
    exc_names = _extract_exception_names(combined, limit=10)
    symbols = _extract_symbols(combined, limit=20)

    fp = [p for p in (focus_paths or []) if _is_rel_path(p)]
    seed_paths = _uniq(fp + trace_paths)

    # Grep patterns: exception names and a few symbols (deterministic slice)
    patterns: List[str] = []
    for x in exc_names:
        if x not in patterns:
            patterns.append(x)
    for x in symbols:
        if len(patterns) >= max_grep_patterns:
            break
        if x not in patterns:
            patterns.append(x)

    # Collect candidate paths and reasons with scores
    candidates: Dict[str, Tuple[float, str]] = {}

    def add_candidate(path: str, bump: float, why: str) -> None:
        if not _is_rel_path(path):
            return
        # Normalize path
        path = path.replace("\\", "/").lstrip("./")
        if not path:
            return
        base = _score_path(path)
        s = base + bump
        if path in candidates:
            prev_s, prev_why = candidates[path]
            if s > prev_s:
                candidates[path] = (s, prev_why + " | " + why)
            else:
                candidates[path] = (prev_s, prev_why + " | " + why)
        else:
            candidates[path] = (s, why)

    for p in seed_paths:
        add_candidate(p, 5.0, "traceback/focus")

    # Use grep to expand candidates
    if include_grep_expansion:
        # Default to fixed string unless deep_grep is explicitly enabled (which allows regex)
        use_fixed = not deep_grep
        for pat in patterns:
            hits = _grep(
                ledger_path=ledger_path,
                workspace=workspace,
                task_id=task_id,
                pattern=pat,
                path=".",
                fixed_string=use_fixed,
            )
            hits_sorted = sorted(
                hits,
                key=lambda h: (str(h.get("path") or ""), str(h.get("line") or "0"), str(h.get("text") or "")),
            )
            for h in hits_sorted[:80]:
                path = str(h.get("path") or "")
                add_candidate(path, 2.0, f"grep:{pat}")

    # Add common config files if present
    top = _listdir(ledger_path=ledger_path, workspace=workspace, task_id=task_id, path=".")
    top_names = {str(x.get("name") or "") for x in top}
    for cfg in ("pyproject.toml", "pytest.ini", "setup.cfg", "setup.py", "requirements.txt"):
        if cfg in top_names:
            add_candidate(cfg, 1.0, "top-config")

    # Rank deterministically
    ranked = sorted(candidates.items(), key=lambda kv: (-kv[1][0], kv[0]))

    # Read and cap content with global budget
    picked: List[ContextFile] = []
    total = 0
    for path, (score, why) in ranked:
        if len(picked) >= max_files:
            break
        txt = _read_file(ledger_path=ledger_path, workspace=workspace, task_id=task_id, path=path)
        if txt is None:
            continue
        b = txt.encode("utf-8", errors="replace")
        if len(b) > max_per_file_bytes:
            txt = b[:max_per_file_bytes].decode("utf-8", errors="replace")
            b = txt.encode("utf-8", errors="replace")
        if total + len(b) > max_total_bytes:
            remain = max_total_bytes - total
            if remain <= 0:
                break
            txt = b[:remain].decode("utf-8", errors="replace")
            b = txt.encode("utf-8", errors="replace")
        picked.append(ContextFile(path=path, text=txt, score=float(score), why=why))
        total += len(b)
        if total >= max_total_bytes:
            break

    meta = {
        "task_id": task_id,
        "n_trace_paths": len(trace_paths),
        "n_focus_paths": len(fp),
        "grep_patterns": patterns,
        "bytes_total": total,
        "max_total_bytes": max_total_bytes,
        "max_files": max_files,
    }
    return ContextPack(files=tuple(picked), meta=meta)


def format_context_pack(pack: ContextPack) -> str:
    """Deterministic prompt-ready formatting."""
    lines: List[str] = []
    lines.append("=== CONTEXT PACK ===")
    lines.append(f"files: {len(pack.files)}, bytes: {pack.meta.get('bytes_total', 0)}")
    lines.append("")
    for f in pack.files:
        lines.append(f"--- FILE: {f.path} (score={f.score:.2f}) ---")
        lines.append(f.text)
        lines.append(f"--- END FILE: {f.path} ---")
        lines.append("")
    return "\n".join(lines)
