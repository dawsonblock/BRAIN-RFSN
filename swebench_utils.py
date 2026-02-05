from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional


def utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_empty_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: List[str], cwd: Optional[str]) -> None:
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        out = proc.stdout.decode("utf-8", errors="replace")[-40_000:]
        err = proc.stderr.decode("utf-8", errors="replace")[-40_000:]
        raise RuntimeError(f"Command failed: {cmd}\nstdout_tail:\n{out}\nstderr_tail:\n{err}")
