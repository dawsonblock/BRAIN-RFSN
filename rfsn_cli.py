# rfsn_cli.py
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rfsn")
    sub = ap.add_subparsers(dest="cmd", required=True)

    runp = sub.add_parser("run", help="Run episodes")
    runp.add_argument("--workspace", required=True)
    runp.add_argument("--task-id", default="local_task")
    runp.add_argument("--episodes", type=int, default=1)
    runp.add_argument("--seed", type=int, default=1337)
    runp.add_argument("--ledger", default="./run_logs/ledger.jsonl")
    runp.add_argument("--db-path", default="./outcomes.sqlite")

    args = ap.parse_args(argv)

    if args.cmd == "run":
        from rfsn_run import main as run_main
        return run_main(
            [
                "--workspace", args.workspace,
                "--task-id", args.task_id,
                "--episodes", str(args.episodes),
                "--seed", str(args.seed),
                "--ledger", args.ledger,
                "--db-path", args.db_path,
            ]
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
