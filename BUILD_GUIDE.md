# Build / Run Guide

## Requirements

- Python 3.12+
- `git` (only required for `APPLY_PATCH`)

## Install

```bash
pip install -e .[dev]
```

## Run an episode

```bash
python -m rfsn_cli run --workspace /path/to/your/repo --episodes 1
```

Outputs:

- `run_logs/ledger.jsonl`
- `outcomes.sqlite`

## Tests

```bash
pytest -q
```

## Notes

`RUN_TESTS` is intentionally allowlisted to:

- `pytest -q`
- `python -m pytest -q`

If you expand the allowlist, do it deliberately. This is the only place command execution is permitted.
