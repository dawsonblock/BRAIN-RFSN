# tests/conftest.py
"""
Shared pytest fixtures for RFSN test suite.

This file is automatically loaded by pytest and makes fixtures
available to all test files in the tests/ directory.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """
    Create a temporary workspace directory with sample files.

    This workspace includes:
    - src/main.py - Sample Python source file
    - tests/test_sample.py - Sample test file
    - README.md - Project readme

    Returns:
        Path to the temporary workspace
    """
    # Create directories
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create sample files
    (tmp_path / "src/main.py").write_text(
        '"""Main module."""\n\ndef greet(name: str) -> str:\n    return f"Hello, {name}!"\n'
    )
    (tmp_path / "tests/test_sample.py").write_text(
        'from src.main import greet\n\ndef test_greet():\n    assert greet("World") == "Hello, World!"\n'
    )
    (tmp_path / "README.md").write_text("# Test Project\n\nA sample project for testing.\n")

    return tmp_path


@pytest.fixture
def sample_ledger_entries() -> list:
    """
    Create sample ledger entries for testing.

    Returns:
        List of ledger entry dictionaries
    """
    return [
        {
            "entry_id": 0,
            "prev_hash": "0" * 64,
            "action_type": "READ_FILE",
            "payload": {"path": "src/main.py"},
            "allowed": True,
        },
        {
            "entry_id": 1,
            "action_type": "WRITE_FILE",
            "payload": {"path": "src/main.py", "content": "# updated"},
            "allowed": True,
        },
    ]


@pytest.fixture
def mock_state():
    """
    Create a mock StateSnapshot for testing.

    Returns:
        StateSnapshot instance
    """
    from rfsn_kernel.types import StateSnapshot
    return StateSnapshot(workspace="/tmp/test_workspace", notes={})


@pytest.fixture
def mock_action():
    """
    Create a mock Action for testing.

    Returns:
        Action instance for READ_FILE
    """
    from rfsn_kernel.types import Action
    return Action(type="READ_FILE", payload={"path": "src/main.py"})


@pytest.fixture
def mock_proposal(mock_action):
    """
    Create a mock Proposal for testing.

    Args:
        mock_action: Injected mock_action fixture

    Returns:
        Proposal instance with one action
    """
    from rfsn_kernel.types import Proposal
    return Proposal(actions=(mock_action,), meta={})


@pytest.fixture(scope="session")
def project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path to the project root
    """
    return Path(__file__).parent.parent


@pytest.fixture
def clean_env(monkeypatch):
    """
    Clean environment by unsetting sensitive variables.

    Useful for tests that need to verify behavior without
    environment variables set.
    """
    vars_to_clear = ["LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"]
    for var in vars_to_clear:
        monkeypatch.delenv(var, raising=False)
