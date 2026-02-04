# tests/test_traceback_selector.py
from __future__ import annotations

import os
from rfsn_companion.selectors.traceback_selector import select_candidate_paths


def test_selector_filters_to_workspace_and_is_deterministic(tmp_path):
    ws = os.path.abspath(str(tmp_path))

    # Create the files so they exist
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    a = pkg_dir / "a.py"
    b = pkg_dir / "b.py"
    a.write_text("# a")
    b.write_text("# b")

    a_path = str(a)
    b_path = str(b)
    outside = "/usr/lib/python3.12/site-packages/x.py"

    trace = (
        f'Traceback (most recent call last):\n'
        f'  File "{outside}", line 1, in <module>\n'
        f'  File "{a_path}", line 10, in f\n'
        f'  File "{a_path}", line 20, in g\n'
        f'  File "{b_path}", line 5, in h\n'
    )

    c1 = select_candidate_paths(trace, ws, k=3)
    c2 = select_candidate_paths(trace, ws, k=3)

    assert c1 == c2
    assert a_path in c1
    assert b_path in c1
    assert all(p.startswith(ws) for p in c1)


def test_selector_ranks_by_frequency(tmp_path):
    ws = str(tmp_path)

    # Create the files
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("# a")
    b.write_text("# b")

    a_path = str(a)
    b_path = str(b)

    trace = (
        f'  File "{a_path}", line 1\n'
        f'  File "{a_path}", line 2\n'
        f'  File "{a_path}", line 3\n'
        f'  File "{b_path}", line 1\n'
    )

    cands = select_candidate_paths(trace, ws, k=2)
    assert len(cands) == 2
    assert cands[0] == a_path  # a appears 3 times, b once


def test_selector_returns_empty_for_no_matches(tmp_path):
    ws = str(tmp_path)
    trace = "no file frames here"

    cands = select_candidate_paths(trace, ws, k=3)
    assert cands == []


def test_selector_excludes_outside_paths(tmp_path):
    ws = str(tmp_path)
    outside = "/etc/passwd"

    trace = f'  File "{outside}", line 1\n'

    cands = select_candidate_paths(trace, ws, k=3)
    assert cands == []


def test_selector_handles_pytest_format(tmp_path):
    """Test pytest output format: file.py:line"""
    ws = str(tmp_path)

    a = tmp_path / "test_example.py"
    a.write_text("# test")

    trace = f"{a}:10: AssertionError\n"

    cands = select_candidate_paths(trace, ws, k=3)
    assert str(a) in cands


def test_selector_resolves_relative_paths(tmp_path):
    """Test relative path resolution."""
    ws = str(tmp_path)

    a = tmp_path / "module.py"
    a.write_text("# module")

    # Pytest often uses relative paths
    trace = "module.py:5: AssertionError\n"

    cands = select_candidate_paths(trace, ws, k=3)
    assert str(a) in cands
