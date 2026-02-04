# tests/test_bandit_memory.py
"""Tests for upgraded bandit and memory systems."""
from __future__ import annotations

import json

from upstream_learner.bandit import ThompsonBandit, BetaArm, warm_start_from_outcomes
from upstream_learner.outcomes_db import (
    insert_outcome,
    query_outcomes,
    get_arm_stats,
    get_summary,
    get_recent_performance,
)


class TestBetaArm:
    def test_update_with_decay(self):
        arm = BetaArm(alpha=5.0, beta=5.0)
        arm.update(1.0, decay=0.9)
        # decay shrinks prior: 1 + (5-1)*0.9 = 4.6, then +1 = 5.6
        assert arm.alpha > 5.0
        assert arm.pulls == 1

    def test_mean_and_variance(self):
        arm = BetaArm(alpha=10.0, beta=10.0)
        assert abs(arm.mean - 0.5) < 0.01
        assert arm.variance > 0

    def test_ucb(self):
        arm = BetaArm(alpha=5.0, beta=5.0, pulls=10)
        ucb = arm.ucb(total_pulls=100)
        assert ucb > arm.mean  # exploration bonus


class TestThompsonBandit:
    def test_choose_methods(self):
        bandit = ThompsonBandit(seed=42)
        bandit.ensure("a")
        bandit.ensure("b")
        bandit.arms["a"].update(1.0)
        bandit.arms["a"].update(1.0)
        bandit.arms["b"].update(0.0)

        # greedy should pick 'a' (higher mean)
        assert bandit.choose(method="greedy") == "a"

        # thompson/ucb/random should return valid arm
        assert bandit.choose(method="thompson") in ["a", "b"]
        assert bandit.choose(method="ucb") in ["a", "b"]
        assert bandit.choose(method="random") in ["a", "b"]

    def test_persistence(self, tmp_path):
        path = tmp_path / "bandit.json"

        b1 = ThompsonBandit(seed=123, decay=0.99)
        b1.ensure("x")
        b1.update("x", 1.0)
        b1.save(str(path))

        b2 = ThompsonBandit.load(str(path))
        assert b2.seed == 123
        assert b2.decay == 0.99
        assert "x" in b2.arms
        assert b2.arms["x"].pulls == 1

    def test_load_or_create(self, tmp_path):
        path = tmp_path / "bandit.json"

        # create new
        b1 = ThompsonBandit.load_or_create(str(path), seed=999)
        assert b1.seed == 999

        b1.ensure("z")
        b1.save(str(path))

        # load existing
        b2 = ThompsonBandit.load_or_create(str(path))
        assert "z" in b2.arms

    def test_arm_stats(self):
        bandit = ThompsonBandit()
        bandit.ensure("a")
        bandit.ensure("b")
        bandit.update("a", 1.0)
        bandit.update("a", 0.5)
        bandit.update("b", 0.0)

        stats = bandit.arm_stats()
        assert len(stats) == 2
        assert stats[0]["mean"] > stats[1]["mean"]


class TestOutcomesDB:
    def test_insert_and_query(self, tmp_path):
        db = tmp_path / "test.db"

        insert_outcome(
            db_path=str(db),
            task_id="task1",
            arm_id="arm_a",
            decision_status="ALLOW",
            tests_passed=True,
            wall_ms=100,
            reward=1.0,
        )

        rows = query_outcomes(str(db), arm_id="arm_a")
        assert len(rows) == 1
        assert rows[0].tests_passed is True
        assert rows[0].reward == 1.0

    def test_get_arm_stats(self, tmp_path):
        db = tmp_path / "test.db"

        for _ in range(3):
            insert_outcome(
                db_path=str(db),
                task_id="t",
                arm_id="good",
                decision_status="ALLOW",
                tests_passed=True,
                wall_ms=50,
                reward=1.0,
            )
        insert_outcome(
            db_path=str(db),
            task_id="t",
            arm_id="bad",
            decision_status="ALLOW",
            tests_passed=False,
            wall_ms=100,
            reward=0.0,
        )

        stats = get_arm_stats(str(db))
        assert len(stats) == 2
        # 'good' should be first (higher avg_reward)
        assert stats[0].arm_id == "good"
        assert stats[0].win_rate == 1.0
        assert stats[1].arm_id == "bad"
        assert stats[1].win_rate == 0.0

    def test_get_summary(self, tmp_path):
        db = tmp_path / "test.db"

        for i in range(5):
            insert_outcome(
                db_path=str(db),
                task_id=f"task_{i}",
                arm_id="arm",
                decision_status="ALLOW",
                tests_passed=i % 2 == 0,
                wall_ms=100,
                reward=float(i % 2 == 0),
            )

        summary = get_summary(str(db))
        assert summary["total"] == 5
        assert summary["unique_tasks"] == 5
        assert summary["total_passes"] == 3  # indices 0, 2, 4

    def test_recent_performance(self, tmp_path):
        db = tmp_path / "test.db"

        for i in range(10):
            insert_outcome(
                db_path=str(db),
                task_id="t",
                arm_id=f"arm_{i % 3}",
                decision_status="ALLOW",
                tests_passed=True,
                wall_ms=100,
                reward=1.0,
            )

        perf = get_recent_performance(str(db), window=10)
        assert perf["count"] == 10
        assert perf["wins"] == 10
        assert "arm_distribution" in perf


class TestWarmStart:
    def test_warm_start_from_outcomes(self, tmp_path):
        db = tmp_path / "outcomes.db"

        # Insert some outcomes
        for _ in range(5):
            insert_outcome(
                db_path=str(db),
                task_id="t",
                arm_id="winner",
                decision_status="ALLOW",
                tests_passed=True,
                wall_ms=50,
                reward=1.0,
            )
        for _ in range(5):
            insert_outcome(
                db_path=str(db),
                task_id="t",
                arm_id="loser",
                decision_status="ALLOW",
                tests_passed=False,
                wall_ms=50,
                reward=0.0,
            )

        bandit = ThompsonBandit()
        n = warm_start_from_outcomes(bandit, str(db))
        assert n == 10
        assert "winner" in bandit.arms
        assert "loser" in bandit.arms
        assert bandit.arms["winner"].mean > bandit.arms["loser"].mean
