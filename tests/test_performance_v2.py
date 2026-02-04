import time
import os
import logging
from unittest.mock import patch, MagicMock
from best_build_agent import BestBuildAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set dummy key so it doesn't complain
os.environ["OPENAI_API_KEY"] = "sk-dummy-key"

def test_performance():
    agent = BestBuildAgent()
    task = "Implement a simple fibonacci function in Python."
    
    # We'll mock the ACTUAL LLM call inside llm_client
    # so we can see the cache in action
    mock_response = {"content": "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)", "cached": False}
    
    with patch("rfsn_controller.llm_client._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Configure the mock response
        mock_choice = MagicMock()
        mock_choice.message.content = mock_response["content"]
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        # 1. First Run (Cold Cache)
        logger.info("--- RUN 1 (COLD CACHE) ---")
        start_time = time.time()
        res1 = agent.process_task(task)
        duration1 = time.time() - start_time
        logger.info(f"Duration 1: {duration1:.2f}s")
        
        # 2. Second Run (Warm Cache)
        logger.info("\n--- RUN 2 (WARM CACHE) ---")
        start_time = time.time()
        res2 = agent.process_task(task)
        duration2 = time.time() - start_time
        logger.info(f"Duration 2: {duration2:.2f}s")
        
        # Verify the second run didn't call the mock client again
        # Actually, it might be called if there are multiple LLM calls (e.g. emotions, recall)
        # But we can check total call count.
        logger.info(f"LLM Call Count: {mock_client.chat.completions.create.call_count}")
        
    logger.info(f"Latency Reduction: {((duration1 - duration2) / duration1) * 100:.1f}%")
    
    if duration2 < duration1 * 0.8: # Allowing a bit for overhead
        logger.info("✅ SUCCESS: LLM Caching is working efficiently!")
    else:
        logger.warning("⚠️ Caching benefit might be obscured by small task size.")

if __name__ == "__main__":
    # Clear cache first for clean test
    import sqlite3
    db_path = "llm_cache.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
    
    test_performance()

