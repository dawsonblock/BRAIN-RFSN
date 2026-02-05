# Testing Guide

## Test Organization

Tests are organized by component in the `tests/` directory:

| File | Coverage |
|------|----------|
| `test_gate_determinism.py` | Gate produces consistent decisions |
| `test_gate_nodeids.py` | Test command validation |
| `test_ledger_chain.py` | Hash chain integrity |
| `test_patch_confinement.py` | Patch path safety |
| `test_security_hardening.py` | Kernel security boundaries |
| `test_policy_arms.py` | Strategy generation |
| `test_strategies_generate_proposals.py` | Proposal creation |
| `test_context_builder_determinism.py` | Context reproducibility |
| `test_grep_policy.py` | GREP action handling |
| `test_git_diff_options.py` | Diff generation options |
| `test_new_actions.py` | Extended action set |
| `test_bandit_memory.py` | Learning persistence |
| `test_ui_backend.py` | API endpoints |
| `test_ui_security.py` | UI security features |

## Running Tests

### All Tests

```bash
# Standard run
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run in parallel
pytest -n auto
```

### Specific Components

```bash
# Kernel only
pytest tests/test_gate*.py tests/test_ledger*.py tests/test_patch*.py

# Learning only
pytest tests/test_bandit*.py tests/test_policy*.py

# Security only
pytest tests/test_security*.py tests/test_ui_security.py
```

### Coverage Report

```bash
# Generate coverage
pytest --cov=rfsn_kernel --cov=upstream_learner --cov-report=html

# View report
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Fast, isolated tests for individual functions:

```python
def test_gate_allows_read_file():
    decision = gate(state, proposal_with_read)
    assert decision.allowed
```

### Integration Tests

Tests that verify component interactions:

```python
def test_ledger_integrity_after_execution():
    # Execute action
    result = execute_decision(state, decision)
    # Verify ledger
    assert verify_ledger_chain(entries)
```

### Security Tests

Tests that verify security boundaries:

```python
def test_path_traversal_blocked():
    assert not is_path_confined("/base", "../../../etc/passwd")

def test_null_byte_injection_blocked():
    assert not is_path_confined("/base", "file\x00.txt")
```

## Writing Tests

### Test Structure

```python
import pytest
from rfsn_kernel.gate import gate
from rfsn_kernel.types import Action, Proposal, StateSnapshot

class TestGateDecisions:
    def test_allows_valid_read(self):
        # Arrange
        state = StateSnapshot(workspace="/tmp/test", notes={})
        action = Action(type="READ_FILE", payload={"path": "src/main.py"})
        proposal = Proposal(actions=(action,), meta={})
        
        # Act
        decision = gate(state, proposal)
        
        # Assert
        assert decision.allowed
        assert len(decision.approved_actions) == 1
```

### Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with sample files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    return tmp_path
```

## Pre-commit Hooks

Tests run automatically on commit:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Continuous Integration

GitHub Actions runs tests on every push:

- Python 3.12
- All pytest tests
- Mypy type checking
- Ruff linting

See `.github/workflows/` for configuration.

## Performance Testing

For benchmarking critical paths:

```bash
# Profile test execution
pytest --durations=10

# Memory profiling
pytest --memray
```

## Debugging Failed Tests

```bash
# Show print output
pytest -s

# Drop into debugger on failure
pytest --pdb

# Run specific test
pytest tests/test_gate_determinism.py::test_gate_is_deterministic -v
```
