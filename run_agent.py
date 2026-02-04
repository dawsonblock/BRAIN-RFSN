import argparse
import logging
import os
import shutil
import sys

from best_build_agent import get_best_build_agent
from memory.vector_store import DEFAULT_MEMORY_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _run_kernel_or_learner(args) -> None:
    if not args.workspace:
        print("Error: --workspace is required for --mode kernel/learner")
        raise SystemExit(2)

    import rfsn_run

    sys.argv = [
        sys.argv[0],
        "--workspace", args.workspace,
        "--task-id", args.task_id,
        "--episodes", str(args.episodes),
        "--ledger", args.ledger,
        "--outcomes-db", args.outcomes_db,
        "--bucket", args.bucket,
    ]
    raise SystemExit(rfsn_run.main())


def main():
    parser = argparse.ArgumentParser(description="RFSN Agent CLI")

    parser.add_argument(
        "--mode",
        default="dialogue",
        choices=["dialogue", "kernel", "learner", "research"],
        help="dialogue | kernel | learner | research",
    )

    # Dialogue/Research agent args
    parser.add_argument("--restore-memory", help="Path to memory dump to restore from.")
    parser.add_argument("--task", help="Execute a single task and exit.")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode.")

    # Kernel/Learner args
    parser.add_argument("--workspace", default="", help="Workspace root for kernel/learner mode")
    parser.add_argument("--task-id", default="local_task", help="Kernel task id")
    parser.add_argument("--episodes", type=int, default=3, help="Number of kernel episodes")
    parser.add_argument("--ledger", default="./run_logs/ledger.jsonl", help="Ledger path")
    parser.add_argument("--outcomes-db", default="./run_logs/outcomes.sqlite3", help="Outcomes DB path")
    parser.add_argument("--bucket", default="local", help="Outcome bucket label")

    args = parser.parse_args()

    # Single authority path for kernel/learner.
    if args.mode in ("kernel", "learner"):
        _run_kernel_or_learner(args)

    # --- Dialogue/Research mode
    if args.restore_memory:
        print(f"RESTORING MEMORY FROM: {args.restore_memory}")
        if not os.path.exists(args.restore_memory):
            print(f"Error: Restore path {args.restore_memory} does not exist.")
            sys.exit(1)

        target_dir = DEFAULT_MEMORY_DIR
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        source_vec = os.path.join(args.restore_memory, "vector_memory")
        if os.path.exists(source_vec):
            shutil.copytree(source_vec, target_dir)
            print(f"Vector Memory restored to {target_dir}")
        else:
            shutil.copytree(args.restore_memory, target_dir)
            print(f"Memory restored (direct) to {target_dir}")

        source_beliefs = os.path.join(args.restore_memory, "core_beliefs.json")
        target_beliefs = os.path.join(os.path.dirname(target_dir), "core_beliefs.json")
        if os.path.exists(source_beliefs):
            shutil.copy2(source_beliefs, target_beliefs)
            print(f"Core Beliefs restored to {target_beliefs}")

    # Initialize agent after restoring memory
    try:
        agent = get_best_build_agent()
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        sys.exit(1)

    if args.task:
        print(f"Processing Task: {args.task}")
        res = agent.process_task(args.task)
        import json
        print(json.dumps(res, indent=2, default=str))
        return

    # Default to interactive if not given a one-shot task
    if args.interactive or not args.task:
        print("RFSN Interactive Mode. Type 'exit' to quit.")
        print("-" * 50)
        while True:
            try:
                task = input("\nUSER> ")
                if not task:
                    continue
                if task.lower() in ["exit", "quit"]:
                    print("Shutting down.")
                    break

                res = agent.process_task(task)

                print(f"\nRFSN ({res.get('neuro_state', 'UNKNOWN')})> {res.get('result')}")
                if res.get("proactive_thought"):
                    print(f"Thought: {res['proactive_thought']}")

            except KeyboardInterrupt:
                print("\nInterrupted.")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
