# rfsn_run.py
"""
Main RFSN runner with upgraded bandit and memory features.
"""
from __future__ import annotations

import argparse
import os

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposer import propose
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism

from upstream_learner.bandit import ThompsonBandit, warm_start_from_outcomes
from upstream_learner.prompt_bank import default_prompt_bank
from upstream_learner.episode import run_episode
from upstream_learner.outcomes_db import insert_outcome, get_summary, get_arm_stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--task-id", default="local_task")
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--decay", type=float, default=0.995, help="Bandit decay factor (1.0=none)")
    ap.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    ap.add_argument("--db-path", default="./outcomes.sqlite")
    ap.add_argument("--bandit-path", default="./run_logs/bandit.json")
    ap.add_argument("--warm-start", action="store_true", help="Warm-start bandit from outcomes DB")
    ap.add_argument("--method", default="thompson", choices=["thompson", "ucb", "greedy", "random"])
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    bank = default_prompt_bank()

    # Load or create bandit with persistence
    bandit = ThompsonBandit.load_or_create(args.bandit_path, seed=args.seed, decay=args.decay)

    # Ensure all arms exist
    for arm_id in bank.arms.keys():
        bandit.ensure(arm_id)

    # Warm-start from historical outcomes if requested
    if args.warm_start and os.path.exists(args.db_path):
        n = warm_start_from_outcomes(bandit, args.db_path, max_rows=500)
        if args.verbose:
            print(f"[bandit] warm-started from {n} historical outcomes")

    if args.verbose:
        print(f"[bandit] loaded {len(bandit.arms)} arms, total pulls: {bandit.total_pulls}")

    for ep in range(args.episodes):
        arm_id = bandit.choose(method=args.method)

        if args.verbose:
            print(f"[episode {ep+1}/{args.episodes}] arm={arm_id}")

        state = StateSnapshot(
            workspace=args.workspace,
            notes={"arm_id": arm_id, "task_id": args.task_id, "episode": ep},
        )

        proposal = propose(state)

        # determinism checks (cheap, strict)
        verify_gate_determinism(state, proposal, trials=5)

        out = run_episode(ledger_path=args.ledger, state=state, proposal=proposal)

        insert_outcome(
            db_path=args.db_path,
            task_id=args.task_id,
            arm_id=arm_id,
            decision_status=out.decision_status,
            tests_passed=out.tests_passed,
            wall_ms=out.wall_ms,
            reward=out.reward,
            meta={"arm_label": bank.arms.get(arm_id, ""), "episode": ep},
        )

        bandit.update(arm_id, out.reward)
        bandit.bump_seed()

        if args.verbose:
            print(f"  result: {out.decision_status}, reward={out.reward}, wall={out.wall_ms}ms")

    # Save bandit state
    bandit.save(args.bandit_path)
    if args.verbose:
        print(f"[bandit] saved to {args.bandit_path}")

    # Verify ledger
    verify_ledger_chain(args.ledger)

    # Print summary
    if args.verbose:
        print("\n=== Arm Statistics ===")
        for stat in bandit.arm_stats()[:6]:
            print(f"  {stat['arm_id']}: mean={stat['mean']}, pulls={stat['pulls']}")

        summary = get_summary(args.db_path)
        if summary.get("total", 0) > 0:
            print(f"\n=== DB Summary ===")
            print(f"  total outcomes: {summary['total']}")
            print(f"  pass rate: {summary['pass_rate']:.1%}")
            print(f"  avg reward: {summary['avg_reward']:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
