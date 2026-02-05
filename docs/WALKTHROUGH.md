# Walkthrough (one episode)

1. Build a `StateSnapshot(workspace=..., notes=...)`
2. Proposer emits a `Proposal(actions=(...), meta=...)`
3. `gate(state, proposal)` returns a `Decision(allowed, reason, approved_actions)`
4. If allowed, controller executes each approved action and returns `ExecResult` tuples
5. Ledger appends a JSONL entry with `(idx, prev_hash, entry_hash, payload)`
6. Replay verifies:
   - ledger hash chain
   - gate determinism on identical inputs
