# upstream_learner/outcomes_db.py
from __future__ import annotations

from typing import Any, Dict, Optional
import sqlite3
import json
import time
import os


SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  task_id TEXT NOT NULL,
  arm_id TEXT NOT NULL,
  decision_status TEXT NOT NULL,
  tests_passed INTEGER NOT NULL,
  wall_ms INTEGER NOT NULL,
  reward REAL NOT NULL,
  meta_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outcomes_task ON outcomes(task_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_arm ON outcomes(arm_id);
"""


def ensure_db(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) if os.path.dirname(path) else ".", exist_ok=True)
    with sqlite3.connect(path) as cx:
        cx.executescript(SCHEMA)
        cx.commit()


def insert_outcome(
    *,
    db_path: str,
    task_id: str,
    arm_id: str,
    decision_status: str,
    tests_passed: bool,
    wall_ms: int,
    reward: float,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    ensure_db(db_path)
    rec = (
        time.time(),
        task_id,
        arm_id,
        decision_status,
        1 if tests_passed else 0,
        int(wall_ms),
        float(reward),
        json.dumps(meta or {}, ensure_ascii=False),
    )
    with sqlite3.connect(db_path) as cx:
        cx.execute(
            "INSERT INTO outcomes (ts, task_id, arm_id, decision_status, tests_passed, wall_ms, reward, meta_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rec,
        )
        cx.commit()
