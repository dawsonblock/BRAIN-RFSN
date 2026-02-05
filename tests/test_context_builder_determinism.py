# tests/test_context_builder_determinism.py
"""Tests for context_builder determinism."""
from __future__ import annotations

from pathlib import Path

from context_builder import (
    build_context_pack,
    format_context_pack,
    _extract_traceback_paths,
    _extract_exception_names,
    _extract_symbols,
)


class TestExtractTraceback:
    def test_extracts_relative_paths(self):
        text = '''
Traceback (most recent call last):
  File "tests/test_foo.py", line 12, in test_bar
    result = do_thing()
  File "src/module.py", line 45, in do_thing
    raise ValueError("oops")
'''
        paths = _extract_traceback_paths(text)
        assert "tests/test_foo.py" in paths
        assert "src/module.py" in paths

    def test_ignores_absolute_paths(self):
        text = 'File "/usr/lib/python3.9/site.py", line 1'
        paths = _extract_traceback_paths(text)
        assert len(paths) == 0

    def test_deterministic_order(self):
        text = 'File "b.py", line 1, in func1\nFile "a.py", line 2, in func2'
        p1 = _extract_traceback_paths(text)
        p2 = _extract_traceback_paths(text)
        assert p1 == p2
        assert p1 == ["b.py", "a.py"]  # order of appearance


class TestExtractExceptionNames:
    def test_finds_exception_names(self):
        text = "ValueError: x\nKeyError: y\nAssertionError"
        names = _extract_exception_names(text)
        assert "ValueError" in names
        assert "KeyError" in names
        assert "AssertionError" in names

    def test_deterministic(self):
        text = "KeyError: x\nValueError: y"
        n1 = _extract_exception_names(text)
        n2 = _extract_exception_names(text)
        assert n1 == n2


class TestExtractSymbols:
    def test_finds_symbols(self):
        text = "foo_bar baz_quux CONSTANT"
        syms = _extract_symbols(text)
        assert "foo_bar" in syms
        assert "baz_quux" in syms

    def test_filters_common_words(self):
        text = "Traceback return raise True False None"
        syms = _extract_symbols(text)
        assert len(syms) == 0


class TestContextPackDeterminism:
    def test_same_inputs_produce_same_output(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "a.py").write_text("def foo():\n    raise ValueError('x')\n", encoding="utf-8")
        (ws / "b.py").write_text("def bar():\n    return 1\n", encoding="utf-8")
        (ws / "pytest.ini").write_text("[pytest]\naddopts=-q\n", encoding="utf-8")

        ledger = tmp_path / "ledger.jsonl"

        stdout = 'E   ValueError: x\nFile "a.py", line 2, in foo\n'
        stderr = ""

        p1 = build_context_pack(
            ledger_path=str(ledger),
            workspace=str(ws),
            task_id="t1",
            pytest_stdout=stdout,
            pytest_stderr=stderr,
            focus_paths=None,
            max_files=6,
            max_total_bytes=80_000,
            max_per_file_bytes=40_000,
            max_grep_patterns=6,
        )
        p2 = build_context_pack(
            ledger_path=str(ledger),
            workspace=str(ws),
            task_id="t1",
            pytest_stdout=stdout,
            pytest_stderr=stderr,
            focus_paths=None,
            max_files=6,
            max_total_bytes=80_000,
            max_per_file_bytes=40_000,
            max_grep_patterns=6,
        )
        assert [f.path for f in p1.files] == [f.path for f in p2.files]
        assert p1.meta == p2.meta
        assert format_context_pack(p1) == format_context_pack(p2)

    def test_format_is_deterministic(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "x.py").write_text("pass\n", encoding="utf-8")

        ledger = tmp_path / "ledger.jsonl"

        p1 = build_context_pack(
            ledger_path=str(ledger),
            workspace=str(ws),
            task_id="det",
            pytest_stdout='File "x.py", line 1',
            pytest_stderr="",
            max_files=3,
            max_total_bytes=10_000,
            max_per_file_bytes=5_000,
            max_grep_patterns=3,
        )
        fmt1 = format_context_pack(p1)
        fmt2 = format_context_pack(p1)
        assert fmt1 == fmt2
        assert "=== CONTEXT PACK ===" in fmt1
