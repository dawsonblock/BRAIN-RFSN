# rfsn_cli.py
from __future__ import annotations

import argparse
import os

from rfsn_kernel.types import StateSnapshot
from rfsn_companion.proposer import propose
from upstream_learner.bandit import ThompsonBandit
from upstream_learner.prompt_bank import default_prompt_bank
from upstream_learner.episode_runner import run_episode, run_two_phase_episode
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism


def cmd_run(args: argparse.Namespace) -> int:
    ws = os.path.abspath(args.workspace)
    ledger_path = os.path.abspath(args.ledger)

    prompt_bank = default_prompt_bank()
    variant_ids = [p.variant_id for p in prompt_bank]
    bandit = ThompsonBandit(seed=args.seed)

    for ep in range(args.episodes):
        # Use forced variant or bandit choice
        if args.variant:
            variant = args.variant
        else:
            variant = bandit.choose(variant_ids)

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
            budget_actions_remaining=args.budget_actions,
            budget_wall_ms_remaining=args.budget_wall_ms,
            notes=notes,
        )

        # Use two-phase mode for v4_trace_read or if --two-phase flag is set
        if args.two_phase or variant == "v4_trace_read":
            outcome = run_two_phase_episode(
                ledger_path=ledger_path,
                state=state,
                proposer_fn=propose,
                max_candidates=args.max_candidates,
            )
            phase_info = f" phases={outcome.phase_count}"
        else:
            proposal = propose(state)
            outcome = run_episode(ledger_path=ledger_path, state=state, proposal=proposal)
            phase_info = ""

        bandit.update(variant, outcome.reward)
        print(
            f"[ep={ep}] variant={variant} status={outcome.decision_status} "
            f"tests_passed={outcome.tests_passed} reward={outcome.reward:.3f}{phase_info}"
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


def cmd_replay(args: argparse.Namespace) -> int:
    ledger_path = os.path.abspath(args.ledger)

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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="rfsn_cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--workspace", required=True)
    run.add_argument("--task-id", default="local_task")
    run.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    run.add_argument("--episodes", type=int, default=3)
    run.add_argument("--seed", type=int, default=1337)
    run.add_argument("--budget-actions", type=int, default=20)
    run.add_argument("--budget-wall-ms", type=int, default=300_000)
    run.add_argument("--read-path", default="")
    run.add_argument("--patch-path", default="")
    run.add_argument("--patch-content", default="")
    run.add_argument("--variant", default="", help="Force a specific proposer variant (e.g., v4_trace_read)")
    run.add_argument("--two-phase", action="store_true", help="Use two-phase episode (auto if variant=v4_trace_read)")
    run.add_argument("--max-candidates", type=int, default=3, help="Max candidate files from trace (for two-phase)")
    run.set_defaults(fn=cmd_run)

    rep = sub.add_parser("replay")
    rep.add_argument("--ledger", required=True)
    rep.set_defaults(fn=cmd_replay)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
