
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from rfsn_swe_agent import main
from upstream_learner.policy_executor import ExecutionPlan, ContextConfig, ModelConfig
from upstream_learner.policy_arms import PolicyArm, ContextPolicy, PatchPolicy, ModelPolicy

@pytest.fixture
def mock_executor():
    with patch("rfsn_swe_agent.PolicyExecutor") as MockExecutor:
        executor = MockExecutor.return_value
        
        # Mock bandit
        executor.bandit = MagicMock()
        
        # Mock select_arm
        executor.select_arm.return_value = "mock_arm"
        
        # Mock get_execution_plan
        mock_plan = ExecutionPlan(
            arm=PolicyArm("mock_arm", ContextPolicy.TRACEBACK_GREP, PatchPolicy.MINIMAL_FIX, ModelPolicy.STANDARD, 
                         max_files=5, max_total_bytes=10000, description="mock"),
            context_config=ContextConfig(
                max_files=5,
                max_total_bytes=10000,
                max_grep_patterns=3,
                include_traceback_files=True,
                include_imports=False,
                include_grep_expansion=True,
            ),
            model_config=ModelConfig(
                temperature=0.5,
                max_tokens=2048,
                model_tier="fast"
            ),
            prompt_suffix="Mock instruction."
        )
        executor.get_execution_plan.return_value = mock_plan
        
        yield executor

@pytest.fixture
def mock_llm():
    with patch("rfsn_swe_agent.LLMClient") as MockLLM:
        client = MockLLM.from_env.return_value
        # Mock complete to return a diff
        client.complete.return_value = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        yield client

@pytest.fixture
def mock_run_step():
    with patch("rfsn_swe_agent.run_step") as m:
        # Return a step with successful decision
        step = MagicMock()
        step.decision.allowed = True
        step.results = (MagicMock(ok=True, output={"stdout": "Ok", "stderr": ""}),)
        m.return_value = step
        yield m

def test_agent_loop_integration(mock_executor, mock_llm, mock_run_step):
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "ledger.jsonl")
        bandit_path = os.path.join(tmpdir, "bandit.json")
        workspace = os.path.join(tmpdir, "ws")
        os.makedirs(workspace)
        
        # Run main
        argv = [
            "--workspace", workspace,
            "--ledger", ledger,
            "--bandit-path", bandit_path,
            "--attempts", "1",
            "--verbose"
        ]
        
        # Since main calls run_tests which mocks, we also need to mock _last_run_tests_output
        with patch("rfsn_swe_agent._last_run_tests_output") as mock_out:
            # First call (baseline) -> False (so we enter loop)
            # Second call (after patch) -> True (so we break loop and succeed)
            mock_out.side_effect = [("out", "err", False), ("out", "err", True)]
            
            # We also need to mock verify_ledger_chain or it might fail on empty file if run_step mocks don't write
            with patch("rfsn_swe_agent.verify_ledger_chain"):
                ret = main(argv)
        
    assert ret == 0
    
    # Verification
    # 1. executor initialized and used
    mock_executor.select_arm.assert_called()
    mock_executor.get_execution_plan.assert_called_with("mock_arm")
    
    # 2. LLM called with plan config
    mock_llm.complete.assert_called()
    call_kwargs = mock_llm.complete.call_args[1]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 2048
    assert "Mock instruction." in call_kwargs["prompt"]
    
    # 3. Outcome recorded
    mock_executor.record_outcome.assert_called_with("mock_arm", 1.0)
    
    # 4. Bandit saved
    mock_executor.bandit.save.assert_called_with(bandit_path)
