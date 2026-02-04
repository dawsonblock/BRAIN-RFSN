# upstream_learner/outcomes_db.py
"""
SQLite outcomes database for learning signal.
Tracks task outcomes, rewards, and metadata for offline analysis.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import os
import json
import sqlite3
import time


SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  task_id TEXT NOT NULL,
  repo TEXT,
  bucket TEXT,
  arm_id TEXT NOT NULL,
  decision_status TEXT NOT NULL,
  tests_passed INTEGER NOT NULL,
  wall_ms INTEGER NOT NULL,
  reward REAL NOT NULL,
  meta_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outcomes_task ON outcomes(task_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_arm ON outcomes(arm_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_bucket ON outcomes(bucket);
"""


def init_db(path: str) -> None:
    """Initialize database with schema."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript(SCHEMA)


def insert_outcome(
    db_path: str,
    *,
    task_id: str,
    repo: str,
    bucket: str,
    arm_id: str,
    decision_status: str,
    tests_passed: bool,
    wall_ms: int,
    reward: float,
    meta: Optional[Dict[str, Any]] = None,
) -> int:
    """Insert outcome and return row ID."""
    init_db(db_path)
    meta_json = json.dumps(meta or {}, sort_keys=True, ensure_ascii=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "INSERT INTO outcomes(ts, task_id, repo, bucket, arm_id, decision_status, tests_passed, wall_ms, reward, meta_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                time.time(),
                task_id,
                repo,
                bucket,
                arm_id,
                decision_status,
                1 if tests_passed else 0,
                int(wall_ms),
                float(reward),
                meta_json,
            ),
        )
        con.commit()
        return cur.lastrowid or 0


def get_stats(db_path: str) -> Dict[str, Any]:
    """Get aggregate statistics from outcomes."""
    if not os.path.exists(db_path):
        return {"total": 0, "passed": 0, "pass_rate": 0.0}

    with sqlite3.connect(db_path) as con:
        cur = con.execute("SELECT COUNT(*), SUM(tests_passed) FROM outcomes")
        row = cur.fetchone()
        total = row[0] or 0
        passed = row[1] or 0
        return {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total > 0 else 0.0,
        }


def get_arm_stats(db_path: str) -> Dict[str, Dict[str, Any]]:
    """Get per-arm statistics."""
    if not os.path.exists(db_path):
        return {}

    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "SELECT arm_id, COUNT(*), SUM(tests_passed), AVG(reward) FROM outcomes GROUP BY arm_id"
        )
        stats = {}
        for row in cur.fetchall():
            arm_id, total, passed, avg_reward = row
            stats[arm_id] = {
                "total": total,
                "passed": passed or 0,
                "pass_rate": (passed or 0) / total if total > 0 else 0.0,
                "avg_reward": avg_reward or 0.0,
            }
        return stats


def compute_reward(
    tests_passed: bool,
    fewer_failures: bool = False,
    token_cost: int = 0,
) -> float:
    """
    Compute reward signal.
    Binary only = plateau. Need gradient.
    """
    import math

    base = 1.0 if tests_passed else (0.3 if fewer_failures else 0.0)
    cost_penalty = 0.01 * math.log(max(1, token_cost)) if token_cost > 0 else 0.0
    return max(0.0, base - cost_penalty)
