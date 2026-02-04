"""
Global pytest configuration and fixtures.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_llm_infrastructure():
    """
    Automatically mock the LLM client to prevent real API calls 
    and avoid ValueError for missing API keys.
    """
    # Mock the active LLM path (rfsn_companion)
    with patch("rfsn_companion.llm.deepseek_client.call_deepseek") as mock_call:
        mock_call.return_value = "Mocked LLM response"
        yield mock_call
