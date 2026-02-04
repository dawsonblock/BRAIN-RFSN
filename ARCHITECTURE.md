# Architecture (what exists in this repo)

## Kernel (`rfsn_kernel/`)

Authoritative boundary:

- `types.py`: immutable dataclasses + canonical hashing helpers
- `gate.py`: deterministic validation (allow/deny)
- `controller.py`: executes approved actions
- `ledger.py`: append-only JSONL ledger with hash chaining
- `replay.py`: verifies determinism + ledger integrity
- `patch_safety.py`: parses diff headers and enforces patch path confinement

Kernel design rule: **no learning inside the gate**.

## Proposer stub (`rfsn_companion/`)

This is a deterministic placeholder:

- returns a proposal that runs allowlisted tests

It is not a planner and does not do retrieval.

## Upstream learner skeleton (`upstream_learner/`)

Implements:

- Thompson sampling bandit (Beta-Bernoulli)
- SQLite outcomes table
- a minimal episode runner that logs reward = 1 if tests pass else 0

There is no multi-arm planner pool in this repo yet, so the bandit is mostly inert.
