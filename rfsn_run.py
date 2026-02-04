# rfsn_run.py
from __future__ import annotations

import argparse

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposer import propose
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism

from upstream_learner.bandit import ThompsonBandit
from upstream_learner.prompt_bank import default_prompt_bank
from upstream_learner.episode import run_episode
from upstream_learner.outcomes_db import insert_outcome


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--task-id", default="local_task")
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    ap.add_argument("--db-path", default="./outcomes.sqlite")
    args = ap.parse_args(argv)

    bank = default_prompt_bank()
    bandit = ThompsonBandit(seed=args.seed)
    for arm_id in bank.arms.keys():
        bandit.ensure(arm_id)

    for _ in range(args.episodes):
        arm_id = bandit.choose()

        state = StateSnapshot(
            workspace=args.workspace,
            notes={"arm_id": arm_id},
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
            meta={"arm_label": bank.arms.get(arm_id, "")},
        )

        bandit.update(arm_id, out.reward)
        bandit.bump_seed()

    verify_ledger_chain(args.ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
