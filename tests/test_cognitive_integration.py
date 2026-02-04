# tests/test_cognitive_integration.py
import pytest
from unittest.mock import patch
from best_build_agent import get_best_build_agent
from cognitive.episodic_memory import Episode, get_episodic_memory
import os
import shutil
import json

@pytest.fixture(autouse=True)
def cleanup():
    # Cleanup memory store before tests
    path = "rfsn_memory_store/test_episodes"
    if os.path.exists(path):
        shutil.rmtree(path)
    yield
    if os.path.exists(path):
        shutil.rmtree(path)

@patch("rfsn_controller.llm_client.call_deepseek")
@patch("cognitive.reasoning_engine.call_deepseek")
def test_memory_recall_and_correction(mock_local, mock_source):
    # Mock LLM response
    mock_local.return_value = mock_source.return_value = {
        "content": json.dumps({
            "understanding": "Core problem identified.",
            "approach": "Logical next step.",
            "confidence": 0.8
        })
    }

    # 1. Initialize agent with a test memory store
    memory = get_episodic_memory("rfsn_memory_store/test_episodes")
    agent = get_best_build_agent()
    agent.episodic_memory = memory
    
    # 2. Seed a "failure" memory
    failure_episode = Episode(
        episode_id="test_fail_1",
        timestamp="2026-02-01T12:00:00",
        goal="Fix the math_add function",
        actions=[{"action": "reason", "success": False}],
        outcome="failure",
        reward=0.0,
        lessons=["Using subtraction (-) instead of addition (+) fails math_add tests."]
    )
    memory.store(failure_episode)
    
    # 3. Process a similar task
    result = agent.process_task("Fix the math_add function")
    
    assert "memories_recalled" in result
    assert result["memories_recalled"] > 0
    assert result["neuro_state"] in ["FOCUSED", "FLOW", "CALM"]
    
@patch("rfsn_controller.llm_client.call_deepseek")
@patch("cognitive.reasoning_engine.call_deepseek")
def test_self_correction_loop_trigger(mock_local, mock_source):
    # First call: Low confidence to trigger loop
    # Second call (recursive): High confidence to terminate loop
    mock_local.side_effect = mock_source.side_effect = [
        {"content": json.dumps({"understanding": "Initial fail", "approach": "Bad", "confidence": 0.4})},
        {"content": json.dumps({"understanding": "Corrected", "approach": "Good", "confidence": 0.9})}
    ]

    agent = get_best_build_agent()
    
    # Trigger self-correction loop (recursion)
    result = agent.process_task(
        "Complex task with errors", 
        test_outputs=["Error: math_ops.py line 5: expected 5 but got 3"]
    )
    
    assert result["confidence"] == 0.9
    assert result["neuro_state"] in ["FOCUSED", "FLOW", "CALM"]

if __name__ == "__main__":
    pytest.main([__file__])
