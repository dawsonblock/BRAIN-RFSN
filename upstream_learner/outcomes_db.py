# upstream_learner/outcomes_db.py
"""
Outcomes database with:
- Insert outcomes
- Query by arm/task/time range
- Aggregation statistics
- Recent performance tracking
- Arm leaderboard
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
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
CREATE INDEX IF NOT EXISTS idx_outcomes_ts ON outcomes(ts);
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
) -> int:
    """Insert outcome and return row id."""
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
        cur = cx.execute(
            "INSERT INTO outcomes (ts, task_id, arm_id, decision_status, tests_passed, wall_ms, reward, meta_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rec,
        )
        cx.commit()
        return cur.lastrowid or 0


# === Query Functions ===


@dataclass
class OutcomeRow:
    id: int
    ts: float
    task_id: str
    arm_id: str
    decision_status: str
    tests_passed: bool
    wall_ms: int
    reward: float
    meta: Dict[str, Any]


def _row_to_outcome(row: sqlite3.Row) -> OutcomeRow:
    return OutcomeRow(
        id=row["id"],
        ts=row["ts"],
        task_id=row["task_id"],
        arm_id=row["arm_id"],
        decision_status=row["decision_status"],
        tests_passed=bool(row["tests_passed"]),
        wall_ms=row["wall_ms"],
        reward=row["reward"],
        meta=json.loads(row["meta_json"]) if row["meta_json"] else {},
    )


def query_outcomes(
    db_path: str,
    *,
    arm_id: Optional[str] = None,
    task_id: Optional[str] = None,
    since_ts: Optional[float] = None,
    limit: int = 100,
) -> List[OutcomeRow]:
    """Query outcomes with optional filters."""
    if not os.path.exists(db_path):
        return []

    clauses = []
    params: List[Any] = []

    if arm_id:
        clauses.append("arm_id = ?")
        params.append(arm_id)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if since_ts:
        clauses.append("ts >= ?")
        params.append(since_ts)

    where = " AND ".join(clauses) if clauses else "1=1"
    params.append(limit)

    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            f"SELECT * FROM outcomes WHERE {where} ORDER BY ts DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_outcome(r) for r in rows]


def get_recent(db_path: str, n: int = 10) -> List[OutcomeRow]:
    """Get n most recent outcomes."""
    return query_outcomes(db_path, limit=n)


# === Aggregation Functions ===


@dataclass
class ArmStats:
    arm_id: str
    count: int
    wins: int
    total_reward: float
    avg_reward: float
    avg_wall_ms: float
    win_rate: float
    last_ts: float


def get_arm_stats(db_path: str) -> List[ArmStats]:
    """Get aggregated statistics per arm, sorted by win rate."""
    if not os.path.exists(db_path):
        return []

    with sqlite3.connect(db_path) as cx:
        rows = cx.execute("""
            SELECT 
                arm_id,
                COUNT(*) as count,
                SUM(tests_passed) as wins,
                SUM(reward) as total_reward,
                AVG(reward) as avg_reward,
                AVG(wall_ms) as avg_wall_ms,
                MAX(ts) as last_ts
            FROM outcomes
            GROUP BY arm_id
            ORDER BY avg_reward DESC
        """).fetchall()

        stats = []
        for r in rows:
            count = r[1]
            wins = r[2] or 0
            stats.append(ArmStats(
                arm_id=r[0],
                count=count,
                wins=wins,
                total_reward=r[3] or 0.0,
                avg_reward=r[4] or 0.0,
                avg_wall_ms=r[5] or 0.0,
                win_rate=wins / count if count > 0 else 0.0,
                last_ts=r[6] or 0.0,
            ))
        return stats


def get_task_stats(db_path: str, task_id: str) -> Dict[str, Any]:
    """Get statistics for a specific task."""
    if not os.path.exists(db_path):
        return {}

    with sqlite3.connect(db_path) as cx:
        row = cx.execute("""
            SELECT 
                COUNT(*) as attempts,
                SUM(tests_passed) as passes,
                SUM(reward) as total_reward,
                AVG(reward) as avg_reward,
                MIN(ts) as first_ts,
                MAX(ts) as last_ts
            FROM outcomes
            WHERE task_id = ?
        """, (task_id,)).fetchone()

        if not row or row[0] == 0:
            return {}

        return {
            "task_id": task_id,
            "attempts": row[0],
            "passes": row[1] or 0,
            "total_reward": row[2] or 0.0,
            "avg_reward": row[3] or 0.0,
            "pass_rate": (row[1] or 0) / row[0] if row[0] else 0.0,
            "first_ts": row[4],
            "last_ts": row[5],
        }


def get_summary(db_path: str) -> Dict[str, Any]:
    """Get overall database summary."""
    if not os.path.exists(db_path):
        return {"total": 0}

    with sqlite3.connect(db_path) as cx:
        row = cx.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT arm_id) as unique_arms,
                COUNT(DISTINCT task_id) as unique_tasks,
                SUM(tests_passed) as total_passes,
                AVG(reward) as avg_reward,
                AVG(wall_ms) as avg_wall_ms,
                MIN(ts) as first_ts,
                MAX(ts) as last_ts
            FROM outcomes
        """).fetchone()

        if not row or row[0] == 0:
            return {"total": 0}

        return {
            "total": row[0],
            "unique_arms": row[1],
            "unique_tasks": row[2],
            "total_passes": row[3] or 0,
            "pass_rate": (row[3] or 0) / row[0] if row[0] else 0.0,
            "avg_reward": round(row[4] or 0.0, 4),
            "avg_wall_ms": round(row[5] or 0.0, 1),
            "first_ts": row[6],
            "last_ts": row[7],
        }


# === Recent Performance ===


def get_recent_performance(
    db_path: str,
    window: int = 20,
) -> Dict[str, Any]:
    """Get performance metrics over last N outcomes."""
    recent = query_outcomes(db_path, limit=window)
    if not recent:
        return {"window": window, "count": 0}

    wins = sum(1 for o in recent if o.tests_passed)
    total_reward = sum(o.reward for o in recent)
    avg_wall = sum(o.wall_ms for o in recent) / len(recent)

    # Arm distribution
    arm_counts: Dict[str, int] = {}
    for o in recent:
        arm_counts[o.arm_id] = arm_counts.get(o.arm_id, 0) + 1

    return {
        "window": window,
        "count": len(recent),
        "wins": wins,
        "win_rate": wins / len(recent),
        "total_reward": round(total_reward, 2),
        "avg_reward": round(total_reward / len(recent), 4),
        "avg_wall_ms": round(avg_wall, 1),
        "arm_distribution": arm_counts,
    }


def get_arm_trend(
    db_path: str,
    arm_id: str,
    window: int = 10,
) -> List[float]:
    """Get recent reward trend for a specific arm (newest first)."""
    outcomes = query_outcomes(db_path, arm_id=arm_id, limit=window)
    return [o.reward for o in outcomes]
