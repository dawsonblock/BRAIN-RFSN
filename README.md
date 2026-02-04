# BRAIN-RFSN (minimal kernel scaffold)

This repository contains a **deterministic safety kernel** with:

- `gate(state, proposal) -> decision` (allow/deny)
- controller execution for approved actions
- an append-only JSONL ledger with a hash chain
- replay checks: ledger integrity + gate determinism

It also includes:

- a deterministic proposer stub (always runs allowlisted tests)
- a minimal "upstream learner" skeleton (Thompson bandit + SQLite outcome logging)

This repo **does not** include:

- LLM integrations
- retrieval or memory systems
- SWE-bench search / multi-attempt strategies
- "digital organism" modules (panic/sleep/neurochemistry/etc.)

## Requirements

- Python **3.12+** (see `pyproject.toml`)
- `git` (only needed if you use `APPLY_PATCH`)

## Install

```bash
pip install -e .[dev]
```

## Run

```bash
python -m rfsn_cli run --workspace /path/to/your/repo --episodes 1
```

Artifacts:

- `run_logs/ledger.jsonl`
- `outcomes.sqlite`

## Security boundary

The gate only approves:

- `READ_FILE` / `WRITE_FILE` within workspace
- `APPLY_PATCH` only if diff paths are parseable + confined
- `RUN_TESTS` only if argv starts with:
  - `pytest -q`
  - `python -m pytest -q`
