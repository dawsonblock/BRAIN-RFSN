"""
Unit tests for LLM Client.
"""
import pytest
openai = pytest.importorskip("openai")
from rfsn_controller.llm_client import call_deepseek


def test_llm_client_basic(mock_llm_infrastructure):
    """Test that the LLM client returns a valid response."""
    # mock_llm_infrastructure is the MagicMock for the OpenAI client
    response = call_deepseek("What is 2 + 2?", temperature=0.0)
    
    assert isinstance(response, dict)
    assert response["content"] == "Mocked LLM response"
    mock_llm_infrastructure.chat.completions.create.assert_called_once()


def test_llm_client_temperature(mock_llm_infrastructure):
    """Test that temperature parameter is accepted."""
    call_deepseek("Generate a random word.", temperature=0.9)
    _, kwargs = mock_llm_infrastructure.chat.completions.create.call_args
    assert kwargs['temperature'] == 0.9


def test_llm_client_error_handling(mock_llm_infrastructure):
    """Test that the client handles errors gracefully."""
    # Force an exception in the mock client
    mock_llm_infrastructure.chat.completions.create.side_effect = Exception("API Error")
    
    response = call_deepseek("", temperature=0.5)
    assert "error" in response
    assert "error" in response # The catch-all prints "An unexpected error occurred."
    assert "An unexpected error occurred" in response["error"]


@pytest.mark.parametrize("temp", [0.0, 0.5, 1.0])
def test_llm_client_temperature_range(mock_llm_infrastructure, temp):
    """Test various temperature values."""
    call_deepseek("Test prompt", temperature=temp)
    _, kwargs = mock_llm_infrastructure.chat.completions.create.call_args
    assert kwargs['temperature'] == temp
