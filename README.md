# RFSN — Reinforced, Faithful, Safe, Narrow

A **deterministic safety kernel** for code repair agents.

```
┌─────────────────────────────────────────────────┐
│           UPSTREAM (Learning)                   │
│  ThompsonBandit │ OutcomesDB │ PromptBank       │
└──────────────────┬──────────────────────────────┘
                   │ arm_id
                   ▼
┌─────────────────────────────────────────────────┐
│           COMPANION (Proposer)                  │
│  proposer.py → strategies.py (6 strategies)    │
└──────────────────┬──────────────────────────────┘
                   │ Proposal(actions)
                   ▼
┌─────────────────────────────────────────────────┐
│           KERNEL (Hard Boundary)                │
│  gate.py │ controller.py │ ledger.py           │
│  patch_safety.py │ replay.py │ types.py        │
└─────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
pip install -e .[dev]

# Run tests
pytest -q

# Run an episode (no LLM)
python rfsn_run.py --workspace /path/to/repo --episodes 3 --verbose

# Run LLM agent loop
export LLM_API_KEY="..."
python rfsn_swe_agent.py --workspace /path/to/repo --attempts 6 --verbose
```

## Project Structure

```
rfsn_kernel/           # Hard boundary (gate + controller + ledger)
├── gate.py            # Deterministic allow/deny
├── controller.py      # Execute approved actions
├── ledger.py          # Hash-chained append-only log
├── patch_safety.py    # Diff parsing + path confinement
├── replay.py          # Integrity verification
└── types.py           # Core dataclasses

rfsn_companion/        # Proposer stubs (not a real planner yet)
├── proposer.py        # Dispatch by arm_id
└── strategies.py      # 6 deterministic strategies

upstream_learner/      # Learning scaffolding
├── bandit.py          # Thompson sampler + persistence
├── outcomes_db.py     # SQLite outcomes + queries
├── episode.py         # Single episode runner
└── prompt_bank.py     # Arm definitions

tests/                 # 41 tests

rfsn_run.py           # Simple runner (bandit + strategies)
rfsn_swe_agent.py     # LLM agent loop (proposer spine)
rfsn_swe_llm.py       # Stdlib OpenAI client
rfsn_cli.py           # CLI wrapper

swebench_runner.py    # Task harness (checkout, run agent, capture artifacts)
swebench_tasks.py     # Task loader (JSON/JSONL)
swebench_utils.py     # Utilities

docs/                 # Additional documentation
```

## SWE-bench Harness

Run your agent against a list of tasks:

```bash
export LLM_API_KEY="..."
export LLM_MODEL="gpt-4.1-mini"
export LLM_BASE_URL="https://api.openai.com/v1/chat/completions"

python swebench_runner.py \
  --tasks ./tasks_example.jsonl \
  --out ./swebench_runs \
  --max-tasks 10 \
  --attempts 8 \
  --timeout-s 900 \
  --verbose
```

Artifacts per task:

- `workspace/` (checked out repo)
- `ledger.jsonl` (kernel log)
- `agent_stdout.txt` / `agent_stderr.txt`
- `RESULT.json`

Summary: `swebench_runs/SUMMARY.json`

## Security Model

| Action | Constraint |
|--------|------------|
| `READ_FILE` | Realpath must be inside workspace |
| `WRITE_FILE` | 512KB/file, 2MB/proposal, realpath confined |
| `APPLY_PATCH` | All diff paths parsed + realpath confined |
| `RUN_TESTS` | Only `pytest -q [safe-nodeids...]` |

Key invariants:

- **Realpath confinement** — Symlinks inside workspace pointing outside are rejected
- **No flags after -q** — Prevents `--cov`, `-s`, etc.
- **Hash-chained ledger** — Tamper-evident audit log
- **Deterministic gate** — Same inputs → same decision (verified by replay)

## Entrypoints

| Script | Purpose |
|--------|---------|
| `rfsn_run.py` | Run episodes with bandit + strategies |
| `rfsn_swe_agent.py` | LLM-driven iterative repair loop |
| `rfsn_cli.py` | CLI wrapper |

## Requirements

- Python **3.12+**
- `git` (only for `APPLY_PATCH`)

## License

MIT
