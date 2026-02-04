# BRAIN-RFSN (Kernel + Companion + Upstream Learner)

This repo is a true RFSN skeleton:

- Companion produces proposals only (no execution)
- Kernel gates proposals deterministically
- Controller executes only approved actions
- Ledger is append-only, hash-chained
- Replay verifies chain integrity + gate determinism
- Upstream learner (bandit) selects proposer variants and updates outside kernel

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UPSTREAM LEARNER                          │
│  (Thompson Bandit • Prompt Variants • Feature Extraction)    │
└─────────────────────────────────────────────────────────────┘
                              │ selects variant
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RFSN COMPANION                            │
│  CAN: Call LLM, reason, plan, use memory                     │
│  CANNOT: Execute subprocess, write files, modify state       │
│  OUTPUT: Proposal(actions=[...])                             │
└─────────────────────────────────────────────────────────────┘
                              │ proposal
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RFSN KERNEL (Deterministic)               │
│  GATE → CONTROLLER → LEDGER                                  │
└─────────────────────────────────────────────────────────────┘
```

## Run

```bash
# Run episodes
python rfsn_cli.py run --workspace /path/to/target/repo --episodes 3

# Replay verify
python rfsn_cli.py replay --ledger ./run_logs/ledger.jsonl
```

## Tests

```bash
python -m pytest
```

## Structure

```
rfsn_kernel/       # Deterministic, no LLM, replayable
rfsn_companion/    # Proposal-only, can use LLM
upstream_learner/  # Outside kernel, learns from outcomes
tests/             # Boundary + determinism tests
```
