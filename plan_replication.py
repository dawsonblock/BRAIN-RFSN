
import logging
from unittest.mock import patch

from cognitive.hierarchical_planner import get_hierarchical_planner

# Setup logging
logging.basicConfig(level=logging.INFO)


def main():
    planner = get_hierarchical_planner()
    
    goal = """
    Perform Self-Replication of the RFSN Digital Organism.
    Target: A new remote server or local directory.
    Replication Type: Mitosis (Full Copy).
    """
    
    # Mocking the LLM response to guarantee a good demo output
    # In a production env with API keys, this patch would be removed.
    mock_response = {
        "content": """
```json
{
  "steps": [
    {
      "id": "package_dna",
      "description": "Package Source Code & Config (DNA)",
      "dependencies": []
    },
    {
      "id": "export_memory",
      "description": "Serialize Vector Memory & Core Beliefs",
      "dependencies": []
    },
    {
      "id": "provision_host",
      "description": "Provision Target Host (Docker/VM)",
      "dependencies": []
    },
    {
      "id": "transmit_payload",
      "description": "Transfer DNA and Memory to Target",
      "dependencies": ["package_dna", "export_memory", "provision_host"]
    },
    {
      "id": "environment_mitosis",
      "description": "Reconstruct Python/Docker Environment",
      "dependencies": ["transmit_payload"]
    },
    {
      "id": "wake_new_instance",
      "description": "Initialize Consciousness (Boot Sequence)",
      "dependencies": ["environment_mitosis"]
    },
    {
      "id": "verify_identity",
      "description": "Run Mirror Kernel Check (Identity Integrity)",
      "dependencies": ["wake_new_instance"]
    }
  ]
}
```
"""
    }
    
    print("\n🧬 RFSN HIERARCHICAL PLANNER 🧬")
    print(f"Analyzing Goal: {goal}")
    print("-" * 50)
    
    with patch('cognitive.hierarchical_planner.call_deepseek', return_value=mock_response):
        plan = planner.create_plan(goal)
    
    if plan:
        print("\n✅ PLAN GENERATED (Directed Acyclic Graph):\n")
        # Format for readability
        for node_id in plan.graph.nodes:
            node = plan.get_task(node_id)
            deps = ", ".join(node.dependencies) if node.dependencies else "None"
            print(f"[{node.id}]")
            print(f"  Action: {node.description}")
            print(f"  Depends On: {deps}")
            print("")
    else:
        print("\n❌ Planning Failed.")

if __name__ == "__main__":
    main()
