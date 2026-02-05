# Quickstart Guide

## Prerequisites

- Python 3.12+
- Docker (optional, for sandboxed execution)
- Node.js 18+ (for UI)

## Installation

```bash
# Clone the repository
git clone https://github.com/dawsonblock/BRAIN-RFSN.git
cd BRAIN-RFSN

# Install core package
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install UI dependencies (optional)
pip install -e ".[ui]"
```

## Running the Agent

### Single Repository Mode

Fix bugs in a local repository:

```bash
python rfsn_swe_agent.py \
    --workspace /path/to/repo \
    --task-id my-fix \
    --attempts 6 \
    --verbose
```

### SWE-bench Mode

Run against SWE-bench tasks:

```bash
# Set up LLM credentials
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4.1-mini"

# Run single task
python swebench_runner.py --task astropy__astropy-12907

# Run batch evaluation
python swebench_runner.py --tasks-file tasks.jsonl --output results/
```

## Using the UI

### Start Backend

```bash
cd ui/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Start Frontend

```bash
cd ui/frontend
npm install
npm run dev
```

Open <http://localhost:5173> to view the Control Center.

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gate_determinism.py

# Run with coverage
pytest --cov=rfsn_kernel
```

## Verify Installation

```bash
# Check kernel imports
python -c "from rfsn_kernel import gate, controller, ledger; print('✓ Kernel OK')"

# Check learning imports
python -c "from upstream_learner import ThompsonBandit; print('✓ Learning OK')"

# Run minimal test
pytest tests/test_ledger_chain.py -v
```

## Configuration

### LLM Settings

Set via environment variables:

```bash
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4.1-mini"
export LLM_BASE_URL="https://api.openai.com/v1/chat/completions"
```

Or configure in the UI Settings page.

### Docker Sandbox

Build the sandbox image:

```bash
docker build -f Dockerfile.sandbox -t rfsn-sandbox .
```

## Next Steps

- Read [Architecture](ARCHITECTURE.md) to understand the system design
- Review [Testing Guide](TESTING_GUIDE.md) for test coverage
- Check [Build Guide](BUILD_GUIDE.md) for development workflow
