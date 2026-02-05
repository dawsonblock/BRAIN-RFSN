# RFSN Architecture

## Overview

RFSN (Recursive Foundational Safety Network) implements a **hardware-boundary approach** to AI agent safety. The core principle: safety logic lives in a minimal, auditable kernel that cannot be bypassed by upstream learning.

```
┌─────────────────────────────────────────────────────────────┐
│                     Upstream Learning                        │
│  (Thompson Sampling Bandit, Policy Arms, Strategy Layer)    │
└─────────────────────────┬───────────────────────────────────┘
                          │ Proposals
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     SAFETY KERNEL                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    GATE     │→ │ CONTROLLER  │→ │  APPEND-ONLY LEDGER │  │
│  │ (Validator) │  │ (Executor)  │  │   (Hash-Chained)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Safety Kernel (`rfsn_kernel/`)

The kernel is the trusted computing base. It cannot be influenced by learning.

| File | Purpose |
|------|---------|
| `types.py` | Immutable dataclasses (Action, Proposal, Decision, StateSnapshot) |
| `gate.py` | Deterministic validation: allow/deny decisions with cryptographic signatures |
| `controller.py` | Executes approved actions within strict byte/time caps |
| `ledger.py` | Append-only JSONL ledger with SHA-256 hash chaining |
| `replay.py` | Verifies determinism and ledger integrity during replay |
| `patch_safety.py` | Parses unified diff headers, enforces path confinement |

**Key invariant**: The gate decides independently. No learning, prompts, or external state influences gate decisions.

### 2. Strategy Layer (`rfsn_companion/`)

Generates proposals that the kernel evaluates.

| File | Purpose |
|------|---------|
| `strategies.py` | 8 Policy Arms with different repair strategies |
| `proposers/__init__.py` | Stub proposer for SWE-bench integration |

**Policy Arms:**

1. `traceback_minimal` - Fix exact traceback location
2. `traceback_grep_standard` - Traceback + grep context
3. `traceback_grep_defensive` - Defensive error handling
4. `deep_grep_minimal` - Deep symbol search
5. `deep_grep_edge_case` - Edge case handling
6. `imports_minimal` - Import-aware fixes
7. `minimal_fast` - Minimal token usage
8. `grep_assertion` - Assertion hardening

### 3. Learning Layer (`upstream_learner/`)

Thompson Sampling bandit that learns which policy arms succeed.

| File | Purpose |
|------|---------|
| `bandit.py` | Beta-Bernoulli Thompson Sampling implementation |
| `policy_arms.py` | Arm definitions with prompts and context builders |
| `episode.py` | Episode management and outcome tracking |
| `outcomes_db.py` | SQLite persistence for learning data |
| `prompt_bank.py` | LLM prompt templates |

### 4. Execution Layer

| File | Purpose |
|------|---------|
| `rfsn_swe_agent.py` | Main agent loop: test → propose → gate → execute |
| `context_builder.py` | Deterministic context assembly from workspace |
| `docker_runner.py` | Sandboxed execution in Docker containers |
| `swebench_runner.py` | SWE-bench harness integration |

## Security Model

### Gate Authority

```python
# Only the gate can create valid Decisions
decision = gate(state, proposal)
assert verify_decision_sig(decision)  # Cryptographic proof
```

The controller **refuses** to execute any action without a valid gate signature.

### Path Confinement

All file operations are confined to the workspace:

- Realpath resolution prevents symlink escapes
- Null byte injection blocked
- Path length limits enforced
- Dangerous file patterns blocked

### Ledger Integrity

Every action is logged with a hash chain:

```json
{"entry_id": 3, "prev_hash": "abc123...", "hash": "def456...", ...}
```

Replay verification detects any tampering.

## Data Flow

```
1. Agent receives failing tests
2. Context Builder assembles workspace snapshot
3. Bandit selects Policy Arm
4. Proposer generates Proposal (actions + patch)
5. Gate validates Proposal → Decision (allow/deny)
6. Controller executes approved actions
7. Ledger records everything
8. Outcome feeds back to Bandit
```

## UI Architecture

### Backend (`ui/backend/`)

FastAPI server with:

- Run management (create, start, stop)  
- SSE log streaming
- Ledger parsing and timeline visualization
- Artifact browsing with path confinement
- Security headers (CSP, X-Frame-Options, etc.)

### Frontend (`ui/frontend/`)

React + Vite + TypeScript:

- Real-time log viewer
- Hash-verified ledger timeline
- Artifact file browser
- Settings management

## Design Principles

1. **Minimal TCB** - The kernel is ~1000 lines of Python
2. **No learning in gate** - Gate decisions are deterministic
3. **Append-only logs** - Every action is recorded
4. **Cryptographic binding** - Decisions are signed
5. **Defense in depth** - Multiple confinement layers
