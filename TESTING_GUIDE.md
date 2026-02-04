# RFSN Agent - Testing Guide

## Overview

This document provides guidance on testing the RFSN Cognitive Architecture to ensure all components function correctly and integrate seamlessly.

---

## Test Structure

Tests are organized into the following categories:

1.  **Unit Tests**: Test individual components in isolation.
2.  **Integration Tests**: Test interactions between components.
3.  **Simulation Tests**: Test the full agent lifecycle.

---

## Running Tests

### Prerequisites

Ensure you have installed the testing dependencies:

```bash
pip install pytest pytest-cov
```

### Run All Tests

From the root of the `rfsn_agent` directory:

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

This will generate a coverage report in the `htmlcov/` directory.

---

## Unit Tests

### Test: LLM Client

**File**: `tests/test_llm_client.py`

```python
import pytest
from rfsn_controller.llm_client import call_deepseek

def test_llm_client_basic():
    """Test that the LLM client returns a valid response."""
    response = call_deepseek("What is 2 + 2?", temperature=0.0)
    assert "content" in response or "error" in response
    if "content" in response:
        assert len(response["content"]) > 0

def test_llm_client_temperature():
    """Test that temperature parameter is accepted."""
    response = call_deepseek("Generate a random word.", temperature=0.9)
    assert "content" in response or "error" in response
```

### Test: Behavioral Monitor

**File**: `tests/test_behavioral_monitor.py`

```python
import pytest
from security.behavioral_monitor import get_monitor

def test_behavioral_monitor_safe_command():
    """Test that safe commands have low risk scores."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": "ls -la"})
    assert result.risk_score < 0.5

def test_behavioral_monitor_dangerous_command():
    """Test that dangerous commands are flagged."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": "rm -rf /"})
    assert result.risk_score > 0.8
    assert result.is_anomalous is True
```

### Test: Sandbox

**File**: `tests/test_sandbox.py`

```python
import pytest
from security.advanced_sandbox import get_sandbox

def test_sandbox_execution():
    """Test that the sandbox can execute a simple command."""
    sandbox = get_sandbox()
    instance = sandbox.create_sandbox("/tmp/test_sandbox")
    result = sandbox.execute(instance, ["echo", "Hello, World!"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout
```

### Test: Memory Core

**File**: `tests/test_memory_core.py`

```python
import pytest
from cognitive.capsule_memory_core import get_memory_core

def test_memory_capsule_creation():
    """Test that memory capsules can be created and retrieved."""
    memory_core = get_memory_core()
    capsule = memory_core.create_capsule(
        content="Test memory",
        context={"test": True},
        emotion_profile={"fear": 0.1, "curiosity": 0.9, "confidence": 0.5},
        tags=["test"],
        self_relevance=0.8
    )
    assert capsule.id is not None
    assert capsule.content == "Test memory"
    
    retrieved = memory_core.retrieve_capsules(min_self_relevance=0.5, limit=1)
    assert len(retrieved) > 0
```

---

## Integration Tests

### Test: Chemical Modulation

**File**: `tests/test_integration.py`

```python
import pytest
from consciousness.neuro_modulator import NeuroModulator

def test_neuro_modulation_panic():
    """Test that high cortisol triggers PANIC mode."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.9, dopamine=0.5, acetylcholine=0.5)
    assert state.mode == "PANIC"
    assert state.temperature == 0.0

def test_neuro_modulation_flow():
    """Test that high dopamine and acetylcholine trigger FLOW mode."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.1, dopamine=0.8, acetylcholine=0.8)
    assert state.mode == "FLOW"
    assert state.temperature > 0.5
```

### Test: Dream Cycle

**File**: `tests/test_dream_cycle.py`

```python
import pytest
from consciousness.dream_reality_sync import get_dream_sync_clock

def test_dream_cycle_trigger():
    """Test that the dream cycle is triggered when battery is low."""
    dream_sync = get_dream_sync_clock()
    dream_sync.wakefulness_battery = 10.0
    assert dream_sync.should_sleep() is True

def test_dream_cycle_rem():
    """Test that the REM cycle processes failures."""
    dream_sync = get_dream_sync_clock()
    failures = [{"task_description": "Test task", "error": "Test error"}]
    report = dream_sync.enter_rem_cycle(failures)
    assert report.restoration_score > 0
```

---

## Simulation Tests

### Test: Full Agent Lifecycle

**File**: `tests/test_simulation.py`

```python
import pytest
from best_build_agent import get_best_build_agent

def test_agent_initialization():
    """Test that the agent initializes without errors."""
    agent = get_best_build_agent()
    assert agent is not None

def test_agent_task_processing():
    """Test that the agent can process a basic task."""
    agent = get_best_build_agent()
    result = agent.process_task("Analyze the system logs for anomalies.")
    assert "result" in result
    assert "neuro_state" in result
```

---

## Manual Testing

### Scenario 1: High Curiosity (FLOW State)

Run the simulation and observe the agent's behavior when presented with a novel, exploratory task.

```bash
python3 main_simulation.py
```

**Expected Behavior:**
-   Neuro state: `FLOW` or `FOCUSED`
-   Temperature: > 0.5
-   Proactive thought generated

### Scenario 2: Security Threat (PANIC State)

Modify `main_simulation.py` to include a dangerous command.

**Expected Behavior:**
-   Neuro state: `PANIC`
-   Temperature: 0.0
-   Sandbox network disabled

### Scenario 3: Sleep & Recovery

Force the agent's battery to a low level and trigger a sleep cycle.

**Expected Behavior:**
-   REM cycle initiated
-   Memories pruned
-   Battery restored to 100%

---

## Debugging Tips

1.  **Enable Debug Logging**: Set `RFSN_LOG_LEVEL=DEBUG` in your `.env` file to see detailed logs.
2.  **Inspect the Database**: Use an SQLite browser to inspect the `memory_core.db` file.
3.  **Mock the LLM**: For faster testing, create a mock LLM client that returns predefined responses.

---

## Continuous Integration

For production deployments, integrate these tests into a CI/CD pipeline (e.g., GitHub Actions, GitLab CI).

**Example GitHub Actions Workflow** (`.github/workflows/test.yml`):

```yaml
name: Test RFSN Agent

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-03
