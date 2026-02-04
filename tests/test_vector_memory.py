"""
Tests for Vector Memory (Semantic RAG).
"""
import pytest
import tempfile
import shutil
import uuid

# Check if ChromaDB is available
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from memory.vector_store import VectorMemory, MemoryFragment


pytestmark = pytest.mark.skipif(
    not CHROMADB_AVAILABLE,
    reason="ChromaDB not installed"
)


@pytest.fixture
def vector_memory():
    """Create a fresh in-memory vector store for each test."""
    # Use unique collection name to avoid state bleeding
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    memory = VectorMemory(persist_directory=None, collection_name=collection_name)
    yield memory


@pytest.fixture
def temp_vector_memory():
    """Create a temporary persistent vector memory for testing."""
    temp_dir = tempfile.mkdtemp()
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    memory = VectorMemory(persist_directory=temp_dir, collection_name=collection_name)
    yield memory, temp_dir, collection_name
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_vector_memory_store_and_retrieve(vector_memory):
    """Test basic store and retrieve functionality."""
    memory = vector_memory
    
    # Store some memories
    assert memory.store("The cat sat on the mat.", {"source": "test1"})
    assert memory.store("Dogs like to play fetch.", {"source": "test2"})
    assert memory.store("Computers process data.", {"source": "test3"})
    
    assert memory.count() == 3
    
    # Retrieve semantically similar
    results = memory.retrieve("feline on carpet", k=2)
    
    assert len(results) > 0
    assert isinstance(results[0], MemoryFragment)
    # The cat memory should be among top results for "feline on carpet"
    top_texts = [r.text for r in results]
    assert any("cat" in t.lower() for t in top_texts)


def test_vector_memory_semantic_similarity(vector_memory):
    """Test that semantic similarity works."""
    memory = vector_memory
    
    memory.store("Python is a programming language", {"topic": "coding"})
    memory.store("The weather is sunny today", {"topic": "weather"})
    memory.store("Cats are cute animals", {"topic": "pets"})
    
    # Query for programming topic
    results = memory.retrieve("software development and coding", k=1)
    
    assert len(results) == 1
    assert "Python" in results[0].text or "programming" in results[0].text.lower()


def test_vector_memory_relevance_score(vector_memory):
    """Test that relevance scores are computed correctly."""
    memory = vector_memory
    
    memory.store("Artificial intelligence and machine learning", {"topic": "ai"})
    memory.store("Cooking recipes and kitchen tips", {"topic": "food"})
    
    results = memory.retrieve("AI and neural networks", k=2)
    
    assert len(results) == 2
    # First result should have higher relevance (lower distance)
    assert results[0].relevance >= results[1].relevance


def test_vector_memory_persistence(temp_vector_memory):
    """Test that memories persist across instances."""
    memory, persist_dir, collection_name = temp_vector_memory
    
    # Store a memory
    memory.store("Persistent memory test", {"important": "true"})
    assert memory.count() == 1
    
    # Create new instance pointing to same directory and collection
    memory2 = VectorMemory(persist_directory=persist_dir, collection_name=collection_name)
    
    # Should find the stored memory
    assert memory2.count() == 1
    results = memory2.retrieve("persistent", k=1)
    assert len(results) == 1


def test_vector_memory_clear(vector_memory):
    """Test clearing all memories."""
    memory = vector_memory
    
    memory.store("Memory 1")
    memory.store("Memory 2")
    assert memory.count() == 2
    
    memory.clear()
    assert memory.count() == 0


def test_vector_memory_metadata(vector_memory):
    """Test that metadata is preserved."""
    memory = vector_memory
    
    memory.store("Important event happened", {
        "timestamp": "2026-02-03",
        "emotion": "happy",
        "source": "user"
    })
    
    results = memory.retrieve("event", k=1)
    assert len(results) == 1
    assert results[0].metadata["emotion"] == "happy"
    assert results[0].metadata["source"] == "user"


def test_vector_memory_empty_query(vector_memory):
    """Test querying empty memory."""
    memory = vector_memory
    
    # Fresh memory with no items
    results = memory.retrieve("anything", k=5)
    assert results == []


def test_vector_memory_no_metadata(vector_memory):
    """Test storing without explicit metadata."""
    memory = vector_memory
    
    # Should work without metadata
    assert memory.store("Just some text")
    assert memory.count() == 1
    
    results = memory.retrieve("text", k=1)
    assert len(results) == 1
