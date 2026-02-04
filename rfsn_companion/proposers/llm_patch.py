# rfsn_companion/proposers/llm_patch.py
"""
LLM-powered proposer that uses DeepSeek to generate patches.

Flow:
1. Read .rfsn/last_tests.txt to get error trace
2. Find failing test file, extract its imports
3. Call DeepSeek to analyze and generate a fix for the imported source
4. Propose: READ + APPLY_PATCH + RUN_TESTS
"""
from __future__ import annotations

import os
import uuid
import re
from typing import List, Optional

from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_companion.selectors.traceback_selector import select_candidate_paths


def _extract_imports_from_file(file_path: str, workspace_root: str) -> List[str]:
    """Extract imported module files from a Python file."""
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    ws = os.path.abspath(workspace_root)
    imports = []

    # Match "from X import" or "import X"
    import_re = re.compile(r'(?:from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import|^import\s+([a-zA-Z_][a-zA-Z0-9_]*))', re.MULTILINE)
    for match in import_re.finditer(content):
        module = match.group(1) or match.group(2)
        if module:
            candidate = os.path.join(ws, f"{module}.py")
            if os.path.exists(candidate):
                imports.append(os.path.abspath(candidate))

    return imports


def _prioritize_source_files(candidates: List[str]) -> List[str]:
    """Sort candidates: source files first, test files last."""
    def score(path: str) -> int:
        basename = os.path.basename(path)
        if basename.startswith("test_") or basename.endswith("_test.py"):
            return 1  # Test file, lower priority
        return 0  # Source file, higher priority

    return sorted(candidates, key=score)


def propose_llm_patch(state: StateSnapshot) -> Proposal:
    ws = os.path.abspath(state.workspace_root)
    last_tests_path = os.path.join(ws, ".rfsn", "last_tests.txt")

    actions: List[Action] = []
    rationale_parts: List[str] = []

    # Get API key from notes or env
    api_key = state.notes.get("deepseek_api_key") or os.environ.get("DEEPSEEK_API_KEY", "")

    # Read last test output if available
    trace_text = state.notes.get("last_tests_text", "")
    if not trace_text and os.path.exists(last_tests_path):
        try:
            with open(last_tests_path, "r", encoding="utf-8") as f:
                trace_text = f.read()
        except Exception:
            pass

    # Select candidate files from trace
    trace_candidates = select_candidate_paths(trace_text, ws, k=5)

    # For each test file in candidates, extract its imports
    all_candidates = list(trace_candidates)
    for cand in trace_candidates:
        basename = os.path.basename(cand)
        if basename.startswith("test_") or basename.endswith("_test.py"):
            imports = _extract_imports_from_file(cand, ws)
            for imp in imports:
                if imp not in all_candidates:
                    all_candidates.append(imp)

    # Prioritize source files over test files
    all_candidates = _prioritize_source_files(all_candidates)

    if not all_candidates:
        # No candidates, just run tests
        actions.append(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}))
        return Proposal(
            proposal_id=str(uuid.uuid4()),
            actions=tuple(actions),
            rationale="llm_patch: no candidates found, running tests only",
            metadata={"variant": "v5_llm_patch", "candidates": []},
        )

    target_path = all_candidates[0]
    rationale_parts.append(f"target:{os.path.basename(target_path)}")

    # Read the target file
    target_content = ""
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                target_content = f.read()
        except Exception:
            pass

    # Add READ_FILE action (required for gate)
    actions.append(Action(name="READ_FILE", args={"path": target_path}))

    # Call DeepSeek to generate patch
    patch_content: Optional[str] = None
    if api_key and target_content and trace_text:
        try:
            from rfsn_companion.llm.deepseek_client import generate_patch_from_context

            patch_content = generate_patch_from_context(
                file_path=target_path,
                file_content=target_content,
                error_trace=trace_text,
                api_key=api_key,
            )

            if patch_content:
                rationale_parts.append("llm_generated_patch")
            else:
                rationale_parts.append("llm_no_fix")

        except Exception as e:
            rationale_parts.append(f"llm_error:{str(e)[:50]}")

    # Add APPLY_PATCH if we have a patch
    if patch_content and patch_content != target_content:
        actions.append(Action(name="APPLY_PATCH", args={"path": target_path, "content": patch_content}))
        rationale_parts.append("applying_patch")

    # Always run tests
    actions.append(Action(name="RUN_TESTS", args={"argv": ["python", "-m", "pytest", "-q"]}))
    rationale_parts.append("run_tests")

    return Proposal(
        proposal_id=str(uuid.uuid4()),
        actions=tuple(actions),
        rationale="; ".join(rationale_parts),
        metadata={"variant": "v5_llm_patch", "candidates": all_candidates},
    )
