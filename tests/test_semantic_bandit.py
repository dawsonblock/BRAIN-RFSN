import pytest
from upstream_learner.contextual_bandit import ContextualThompsonBandit
from memory.vector_store import get_vector_memory
import os
import shutil

@pytest.fixture
def clean_memory():
    # Setup clean memory store for testing
    path = "test_rfsn_memory"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    memory = get_vector_memory(persist_directory=path)
    yield memory
    # Cleanup
    if os.path.exists(path):
        shutil.rmtree(path)

def test_semantic_bucket_generalization(clean_memory):
    bandit = ContextualThompsonBandit()
    arms = ["strategy_a", "strategy_b"]
    
    # Task 1: A routing error in Django
    features1 = {
        "task_description": "Fix NoReverseMatch routing error in web app urls",
        "repo": "django/django",
        "lang": "py",
        "has_trace": True
    }
    
    # Choose strategy for Task 1 (Semantic Mapping will happen)
    choice1, bucket1 = bandit.choose(arms, features1, use_semantic=True)
    
    # Update Task 1 with a big reward for strategy_a
    bandit.update(bucket1, "strategy_a", 1.0, multiplier=2.0)
    
    # Task 2: A similar routing error in Flask
    features2 = {
        "task_description": "Fix NoReverseMatch routing error in web app urls (Flask variant)",
        "repo": "pallets/flask",
        "lang": "py",
        "has_trace": True
    }
    
    # Choose for Task 2. It should find Task 1 as a neighbor and share weights.
    # Note: Vector memory needs to be populated, which happens during choose.
    choice2, bucket2 = bandit.choose(arms, features2, use_semantic=True)
    
    # Verify that the new bucket for Task 2 was initialized with Task 1's experience
    assert bucket2 in bandit.buckets
    # The alpha for strategy_a in Task 2 should be > 1.0 because it borrowed from Task 1
    assert bandit.buckets[bucket2]["strategy_a"].alpha > 1.0
    print(f"✅ Generalization Success: Task 2 inherited weights from Task 1. Bucket: {bucket2}")

if __name__ == "__main__":
    pytest.main([__file__])
