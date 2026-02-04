"""
Global pytest configuration and fixtures.
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_llm_infrastructure():
    """
    Automatically mock the internal _get_client to prevent real API calls 
    and avoid ValueError for missing OPENAI_API_KEY.
    """
    with patch("rfsn_controller.llm_client._get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        
        # Setup a default successful response for any chat completion call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked LLM response"
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client
