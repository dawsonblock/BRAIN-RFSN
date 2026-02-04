import os
import shutil
import tarfile
import logging
from memory.vector_store import DEFAULT_MEMORY_DIR

logger = logging.getLogger(__name__)

class ReplicationManager:
    def __init__(self, workspace_root: str):
        self.root = os.path.abspath(workspace_root)
        self.dist_dir = os.path.join(self.root, "dist")
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)
        
    def package_dna(self) -> str:
        """Create a compressed archive of the codebase (DNA)."""
        logger.info("🧬 PACKAGING DNA...")
        archive_name = os.path.join(self.dist_dir, "rfsn_dna.tar.gz")
        
        with tarfile.open(archive_name, "w:gz") as tar:
            # Add root recursively but exclude items
            def filter_func(tarinfo):
                name = tarinfo.name
                if ".venv" in name or "__pycache__" in name or ".git" in name or "dist" in name or "rfsn_dna.tar.gz" in name:
                    return None
                return tarinfo
                
            tar.add(self.root, arcname="rfsn", filter=filter_func)
            
        logger.info(f"✅ DNA Packaged: {archive_name}")
        return archive_name
        
    def export_memory(self, memory_dir: str = DEFAULT_MEMORY_DIR, beliefs_file: str = "memory/core_beliefs.json") -> str:
        """Serialize consciousness state."""
        logger.info(f"🧠 EXPORTING MEMORY (Source: {memory_dir})...")
        archive_name = os.path.join(self.dist_dir, "consciousness_state.tar.gz")
        
        mem_full_path = os.path.join(self.root, memory_dir)
        beliefs_full_path = os.path.join(self.root, beliefs_file)
        
        with tarfile.open(archive_name, "w:gz") as tar:
            # Add Vector DB
            if os.path.exists(mem_full_path):
                tar.add(mem_full_path, arcname="vector_memory")
            else:
                logger.warning(f"⚠️ Vector Memory dir not found at {mem_full_path}")
            
            # Add Beliefs
            if os.path.exists(beliefs_full_path):
                tar.add(beliefs_full_path, arcname="core_beliefs.json")
            else:
                logger.warning(f"⚠️ Core Beliefs file not found at {beliefs_full_path}")
                
        logger.info(f"✅ Consciousness Exported: {archive_name}")
        return archive_name
        
    def replicate_locally(self, target_path: str):
        """Execute Mitosis to a local directory."""
        target_path = os.path.abspath(target_path)
        logger.info(f"🔄 INITIATING MITOSIS -> {target_path}")
        
        if os.path.exists(target_path):
             logger.warning(f"Target path {target_path} exists. Cleaning it up first for clean install.")
             shutil.rmtree(target_path)
        os.makedirs(target_path)
        
        # 1. Package
        dna_path = self.package_dna()
        mem_path = self.export_memory()
        
        # 2. Extract DNA
        logger.info("📂 Unpacking DNA in target...")
        with tarfile.open(dna_path, "r:gz") as tar:
            tar.extractall(path=target_path)
            
        # 3. Extract Memory
        logger.info("🧠 Injecting Memory in target...")
        memory_dump_path = os.path.join(target_path, "rfsn", "init_memory")
        if not os.path.exists(memory_dump_path):
             os.makedirs(memory_dump_path)

        with tarfile.open(mem_path, "r:gz") as tar:
            tar.extractall(path=memory_dump_path)
            
        # 4. Generate Boot Script
        self._write_boot_script(target_path)
        
        logger.info(f"✨ MITOSIS COMPLETE. New instance ready at {target_path}")
        return True
        
    def _write_boot_script(self, target_path: str):
         boot_path = os.path.join(target_path, "rfsn", "wake_up.sh")
         rfsn_path = os.path.join(target_path, "rfsn")
         
         with open(boot_path, "w") as f:
             f.write(f"""#!/bin/bash
cd {rfsn_path}
echo "⚡ Waking Updated RFSN Clone..."
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python run_agent.py --restore-memory init_memory
""")
         os.chmod(boot_path, 0o755)
