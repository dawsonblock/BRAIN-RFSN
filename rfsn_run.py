# rfsn_run.py
from __future__ import annotations

import os
import argparse
import time

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposer import propose
from upstream_learner.bandit import ThompsonBandit
from upstream_learner.prompt_bank import default_prompt_bank
from upstream_learner.episode_runner import run_episode
from upstream_learner.outcomes_db import insert_outcome
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="Path to repo/workspace root")
    ap.add_argument("--task-id", default="local_task")
    ap.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    ap.add_argument("--outcomes-db", default="./run_logs/outcomes.sqlite3")
    ap.add_argument("--bucket", default="local")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--dopamine", type=float, default=0.5)
    ap.add_argument("--read-path", default="", help="Optional: file path to READ_FILE for variants")
    ap.add_argument("--patch-path", default="", help="Optional: file path to APPLY_PATCH for variants")
    ap.add_argument("--patch-content", default="", help="Optional: content to write for APPLY_PATCH")
    args = ap.parse_args()

    ws = os.path.abspath(args.workspace)
    ledger_path = os.path.abspath(args.ledger)
    outcomes_db = os.path.abspath(args.outcomes_db)

    prompt_bank = default_prompt_bank()
    bandit = ThompsonBandit(seed=1337)
    variant_ids = [p.variant_id for p in prompt_bank]

    for ep in range(args.episodes):
        variant = bandit.choose(variant_ids, dopamine=float(args.dopamine))

        notes = {"prompt_variant": variant}
        if args.read_path:
            notes["read_path"] = args.read_path
        if args.patch_path:
            notes["patch_path"] = args.patch_path
        if args.patch_content:
            notes["patch_content"] = args.patch_content

        state = StateSnapshot(
            task_id=args.task_id,
            workspace_root=ws,
            step=ep,
            budget_actions_remaining=20,
            budget_wall_ms_remaining=300_000,
            notes=notes,
        )

        proposal = propose(state)
        outcome = run_episode(ledger_path=ledger_path, state=state, proposal=proposal)

        bandit.update(variant, outcome.reward)

        insert_outcome(
            outcomes_db,
            task_id=args.task_id,
            repo=ws,
            bucket=str(args.bucket),
            arm_id=str(variant),
            decision_status=str(outcome.decision_status),
            tests_passed=bool(outcome.tests_passed),
            wall_ms=int(outcome.wall_ms),
            reward=float(outcome.reward),
            meta={"episode": ep, "timestamp": time.time()},
        )
        print(
            f"[ep={ep}] variant={variant} status={outcome.decision_status} "
            f"tests_passed={outcome.tests_passed} reward={outcome.reward:.3f}"
        )

    ok_chain, errs_chain = verify_ledger_chain(ledger_path)
    ok_gate, errs_gate = verify_gate_determinism(ledger_path)
    if not ok_chain:
        print("LEDGER_CHAIN_FAIL:", errs_chain)
        return 2
    if not ok_gate:
        print("GATE_DETERMINISM_FAIL:", errs_gate)
        return 3
    print("REPLAY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
