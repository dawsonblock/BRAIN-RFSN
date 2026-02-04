#!/usr/bin/env python3
"""
RFSN Runner Wrapper - kernel + companion + learner only.
No cognitive/consciousness/memory layers.
"""
from __future__ import annotations

import argparse
import sys


def cmd_run(args: argparse.Namespace) -> int:
    """Run learning episodes (SWE-bench style loop)."""
    from rfsn_run import main as rfsn_run_main

    argv = [
        "--workspace", args.workspace,
        "--task-id", args.task_id,
        "--episodes", str(args.episodes),
        "--seed", str(args.seed),
    ]
    if args.variant is not None:
        argv += ["--variant", args.variant]
    if args.db_path is not None:
        argv += ["--db-path", args.db_path]
    if args.max_steps is not None:
        argv += ["--max-steps", str(args.max_steps)]
    if args.panic_on_deny:
        argv += ["--panic-on-deny"]
    if args.replay_verify:
        argv += ["--replay-verify"]
    if args.verbose:
        argv += ["--verbose"]
    return rfsn_run_main(argv)


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay a ledger and verify chain + gate determinism."""
    from rfsn_replay import main as rfsn_replay_main
    argv = ["--ledger", args.ledger]
    if args.verbose:
        argv += ["--verbose"]
    return rfsn_replay_main(argv)


def cmd_cli(args: argparse.Namespace) -> int:
    """Interactive CLI for the kernel workspace."""
    from rfsn_cli import main as rfsn_cli_main
    argv = ["run", "--workspace", args.workspace]
    if args.verbose:
        argv += ["--verbose"]
    return rfsn_cli_main(argv)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_agent.py",
        description="RFSN runner wrapper (kernel + companion + learner only)."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # run subcommand
    pr = sub.add_parser("run", help="Run learning episodes (SWE-bench style loop).")
    pr.add_argument("--workspace", required=True, help="Workspace root for the target repo.")
    pr.add_argument("--task-id", required=True, help="Task identifier (e.g. SWE-bench instance id).")
    pr.add_argument("--episodes", type=int, default=5)
    pr.add_argument("--seed", type=int, default=1337)
    pr.add_argument("--variant", default=None, help="Force proposer variant id (optional).")
    pr.add_argument("--db-path", default=None, help="SQLite outcomes DB path.")
    pr.add_argument("--max-steps", type=int, default=None, help="Max steps per episode (trajectory length).")
    pr.add_argument("--panic-on-deny", action="store_true", help="Enter PANIC mode after first gate deny.")
    pr.add_argument("--replay-verify", action="store_true", help="Verify determinism via replay after each episode.")
    pr.add_argument("--verbose", action="store_true")
    pr.set_defaults(fn=cmd_run)

    # replay subcommand
    pp = sub.add_parser("replay", help="Replay a ledger and verify chain + gate determinism.")
    pp.add_argument("--ledger", required=True, help="Path to ledger JSONL.")
    pp.add_argument("--verbose", action="store_true")
    pp.set_defaults(fn=cmd_replay)

    # cli subcommand
    pc = sub.add_parser("cli", help="Interactive CLI for the kernel workspace.")
    pc.add_argument("--workspace", required=True)
    pc.add_argument("--verbose", action="store_true")
    pc.set_defaults(fn=cmd_cli)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
