
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
        MockExecutor.load.return_value = executor
        
        # Mock bandit
        executor.bandit = MagicMock()
        
        # Mock select_arm
        executor.select_arm.return_value = "mock_arm"
        
        # Mock get_execution_plan
        mock_plan = MagicMock()
        mock_plan.context_config.max_files = 10
        mock_plan.context_config.max_total_bytes = 10000
        mock_plan.context_config.max_grep_patterns = 0
        mock_plan.context_config.include_traceback_files = False
        mock_plan.context_config.include_imports = False
        mock_plan.context_config.include_grep_expansion = False
        mock_plan.context_config.deep_grep = False
        mock_plan.context_config.minimal_mode = False
        mock_plan.model_config.model = "gpt-4-test"
        mock_plan.model_config.temperature = 0.5
        mock_plan.model_config.max_tokens = 100
        mock_plan.prompt_suffix = "Test Suffix"
        executor.get_execution_plan.return_value = mock_plan
        
        yield executor

@pytest.fixture
def mock_llm():
    with patch("rfsn_swe_agent.LLMClient") as MockLLM:
        client = MockLLM.return_value
        # Mock complete to return a diff
        client.complete.return_value = "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        yield client

@pytest.fixture
def mock_run_step():
    with patch("rfsn_swe_agent.run_step") as m:
        # Return a step with successful decision
        step = MagicMock()
        step.decision.allowed = True
        res = MagicMock(ok=True, output={"stdout": "Ok", "stderr": ""})
        res.action.type = "RUN_TESTS"
        step.results = (res,)
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
            "--task-id", "smoke_task",
            "--ledger", ledger,
            "--bandit-path", bandit_path,
            "--attempts", "1",
            "--candidates", "1",
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
                print(f"DEBUG: ret={ret}, call_count={mock_out.call_count}")

    assert ret == 0
    
    # Verification
    # 1. executor initialized and used
    mock_executor.select_arm.assert_called()
    mock_executor.get_execution_plan.assert_called_with("mock_arm")
    
    # 2. LLM called with plan config
    mock_llm.complete.assert_called()
    call_kwargs = mock_llm.complete.call_args[1]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 100
    assert "Test Suffix" in call_kwargs["prompt"]
    
    # 3. Outcome recorded
    mock_executor.record_outcome.assert_called_with("mock_arm", reward=1.0)
    
    # 4. Bandit saved
    mock_executor.save.assert_called_with(bandit_path)
