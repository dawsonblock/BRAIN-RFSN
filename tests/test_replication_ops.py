
import os
import pytest
import tarfile
from operations.replication_manager import ReplicationManager

@pytest.fixture
def workspace_root(tmp_path):
    # Setup mock workspace
    root = tmp_path / "workspace"
    root.mkdir()
    
    # Create dummy files
    (root / "best_build_agent.py").write_text("print('hello')")
    (root / "memory").mkdir()
    (root / "memory" / "core_beliefs.json").write_text("{}")
    
    # Create dummy vector store
    (root / "rfsn_memory_store").mkdir()
    (root / "rfsn_memory_store" / "index.bin").write_text("data")
    
    return str(root)

def test_package_dna(workspace_root):
    manager = ReplicationManager(workspace_root)
    archive = manager.package_dna()
    
    assert os.path.exists(archive)
    assert archive.endswith("rfsn_dna.tar.gz")
    
    # Verify contents
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "rfsn/best_build_agent.py" in names

def test_replication_flow(workspace_root, tmp_path):
    manager = ReplicationManager(workspace_root)
    target_path = str(tmp_path / "replica")
    
    # Run Mitosis
    manager.replicate_locally(target_path)
    
    # Verify Structure
    assert os.path.exists(os.path.join(target_path, "rfsn", "best_build_agent.py"))
    assert os.path.exists(os.path.join(target_path, "rfsn", "wake_up.sh"))
    
    # Verify Memory Injection
    # path: rfsn/init_memory/vector_memory/index.bin
    expected_mem = os.path.join(target_path, "rfsn", "init_memory", "vector_memory", "index.bin")
    assert os.path.exists(expected_mem)
