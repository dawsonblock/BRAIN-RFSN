"""
Unit tests for Capsule Memory Core.
"""
import pytest
import os
from cognitive.capsule_memory_core import MemoryCapsule


@pytest.fixture
def test_db_path():
    """Provide a test database path."""
    path = "/tmp/test_memory_core.db"
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


def test_memory_capsule_creation(test_db_path):
    """Test that memory capsules can be created."""
    from cognitive.capsule_memory_core import CapsuleMemoryCore
    memory_core = CapsuleMemoryCore(db_path=test_db_path)
    
    capsule = memory_core.create_capsule(
        content="Test memory",
        context={"test": True, "value": 42},
        emotion_profile={"fear": 0.1, "curiosity": 0.9, "confidence": 0.5},
        tags=["test", "unit_test"],
        self_relevance=0.8
    )
    
    assert isinstance(capsule, MemoryCapsule)
    assert capsule.id is not None
    assert capsule.content == "Test memory"
    assert capsule.self_relevance == 0.8
    assert "test" in capsule.tags


def test_memory_capsule_retrieval(test_db_path):
    """Test that memory capsules can be retrieved."""
    from cognitive.capsule_memory_core import CapsuleMemoryCore
    memory_core = CapsuleMemoryCore(db_path=test_db_path)
    
    # Create multiple capsules
    memory_core.create_capsule(
        content="High relevance memory",
        context={},
        emotion_profile={"fear": 0.0, "curiosity": 1.0, "confidence": 1.0},
        tags=["important"],
        self_relevance=0.9
    )
    
    memory_core.create_capsule(
        content="Low relevance memory",
        context={},
        emotion_profile={"fear": 0.0, "curiosity": 0.0, "confidence": 0.0},
        tags=["unimportant"],
        self_relevance=0.2
    )
    
    # Retrieve high-relevance capsules
    retrieved = memory_core.retrieve_capsules(min_self_relevance=0.5, limit=10)
    assert len(retrieved) >= 1
    assert all(c.self_relevance >= 0.5 for c in retrieved)


def test_memory_statistics(test_db_path):
    """Test that memory statistics are calculated correctly."""
    from cognitive.capsule_memory_core import CapsuleMemoryCore
    memory_core = CapsuleMemoryCore(db_path=test_db_path)
    
    # Create some capsules
    for i in range(5):
        memory_core.create_capsule(
            content=f"Memory {i}",
            context={},
            emotion_profile={"fear": 0.0, "curiosity": 0.0, "confidence": 0.0},
            tags=[],
            self_relevance=0.5
        )
    
    stats = memory_core.get_statistics()
    assert stats["total_capsules"] == 5
    assert stats["storage_type"] == "sqlite"


def test_memory_emotion_profile(test_db_path):
    """Test that emotion profiles are stored and retrieved correctly."""
    from cognitive.capsule_memory_core import CapsuleMemoryCore
    memory_core = CapsuleMemoryCore(db_path=test_db_path)
    
    emotion = {"fear": 0.8, "curiosity": 0.2, "confidence": 0.3}
    capsule = memory_core.create_capsule(
        content="Scary memory",
        context={},
        emotion_profile=emotion,
        tags=["fear"],
        self_relevance=0.9
    )
    
    retrieved = memory_core.retrieve_capsules(min_self_relevance=0.5, limit=1)
    assert len(retrieved) > 0
    assert retrieved[0].emotion_profile["fear"] == 0.8
