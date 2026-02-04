# tests/test_no_exec_in_companion.py
from __future__ import annotations

import builtins
import subprocess
import os

import rfsn_companion.proposer as proposer
from rfsn_kernel.types import StateSnapshot


def test_companion_cannot_spawn_process(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise AssertionError("Companion attempted to execute a subprocess")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(os, "system", boom)

    # v0
    state0 = StateSnapshot(task_id="t", workspace_root=str(tmp_path), step=0, notes={"prompt_variant": "v0_minimal"})
    _ = proposer.propose(state0)

    # v2
    state2 = StateSnapshot(
        task_id="t",
        workspace_root=str(tmp_path),
        step=0,
        notes={"prompt_variant": "v2_read_then_plan", "read_path": str(tmp_path / "README.md")},
    )
    _ = proposer.propose(state2)

    # v3
    state3 = StateSnapshot(
        task_id="t",
        workspace_root=str(tmp_path),
        step=0,
        notes={
            "prompt_variant": "v3_brain",
            "read_path": str(tmp_path / "README.md"),
            "patch_path": str(tmp_path / "README.md"),
            "patch_content": "hello\n",
        },
    )
    _ = proposer.propose(state3)


def test_companion_cannot_write_files(monkeypatch, tmp_path):
    orig_open = builtins.open

    def guarded_open(path, mode="r", *args, **kwargs):
        if any(m in mode for m in ("w", "a", "+")):
            raise AssertionError("Companion attempted to write a file")
        return orig_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)

    # v2 reads only
    state2 = StateSnapshot(
        task_id="t",
        workspace_root=str(tmp_path),
        step=0,
        notes={"prompt_variant": "v2_read_then_plan", "read_path": str(tmp_path / "README.md")},
    )
    _ = proposer.propose(state2)

    # v3 emits write actions, but must not actually write during proposal creation
    state3 = StateSnapshot(
        task_id="t",
        workspace_root=str(tmp_path),
        step=0,
        notes={
            "prompt_variant": "v3_brain",
            "patch_path": str(tmp_path / "X.txt"),
            "patch_content": "x\n",
        },
    )
    _ = proposer.propose(state3)
