"""
Hierarchical Planner (Prefrontal Cortex).
Decomposes high-level goals into executable Task Graphs (DAGs).
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from cognitive.task_graph import TaskGraph
from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

class HierarchicalPlanner:
    def __init__(self):
        self.max_subtasks = 10
        self.current_plan: Optional[TaskGraph] = None
        
    def create_plan(self, goal: str, context: Dict[str, Any] = None) -> Optional[TaskGraph]:
        """
        Decomposes a complex goal into a Task Graph using LLM.
        """
        logger.info(f"🧠 PLANNING: Analyzing goal: '{goal}'")
        
        prompt = self._construct_planning_prompt(goal, context)
        response = call_deepseek(prompt, temperature=0.3, max_tokens=2000)
        
        if "error" in response:
            logger.error(f"Planning failed: {response['error']}")
            return None
            
        content = response.get("content", "")
        plan_data = self._parse_llm_json(content)
        
        if not plan_data:
            logger.error("Failed to parse plan JSON from LLM response.")
            return None
            
        return self._build_graph(plan_data, goal)

    def _construct_planning_prompt(self, goal: str, context: Dict) -> str:
        ctx_str = json.dumps(context, indent=2) if context else "{}"
        return f"""
You are the Prefrontal Cortex of a Digital Organism.
Your task is to decompose a complex goal into a directed acyclic graph (DAG) of executable sub-tasks.

GOAL: "{goal}"

CONTEXT:
{ctx_str}

REQUIREMENTS:
1. Break the goal down into 2-10 logical steps.
2. Identify dependencies (which tasks must finish before others start).
3. Output MUST be valid JSON in the following format:
{{
  "steps": [
    {{
      "id": "step_1",
      "description": "Precise action description",
      "dependencies": []
    }},
    {{
      "id": "step_2",
      "description": "Dependent action",
      "dependencies": ["step_1"]
    }}
  ]
}}

4. Do NOT output markdown code blocks. Just the raw JSON.
"""

    def _parse_llm_json(self, content: str) -> Optional[Dict]:
        """Robustly parse JSON from LLM output."""
        try:
            # Strip code blocks if present
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e} | Content: {content[:100]}...")
            return None
            
    def _build_graph(self, plan_data: Dict, goal: str) -> TaskGraph:
        graph = TaskGraph()
        steps = plan_data.get("steps", [])
        
        # First pass: Add all nodes
        for step in steps:
            graph.add_task(
                task_id=step["id"],
                description=step["description"],
                dependencies=step.get("dependencies", [])
            )
            
        logger.info(f"🗓️ PLAN CREATED: {len(steps)} steps for '{goal}'")
        return graph

# Singleton
_planner = None
def get_hierarchical_planner():
    global _planner
    if _planner is None:
        _planner = HierarchicalPlanner()
    return _planner
