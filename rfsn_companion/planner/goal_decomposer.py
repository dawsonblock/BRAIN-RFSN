# rfsn_companion/planner/goal_decomposer.py
"""LLM-based goal decomposition into executable plan steps."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class Goal:
    description: str
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    step_id: int
    action_name: str
    action_args: Dict[str, Any]
    description: str
    depends_on: List[int] = field(default_factory=list)
    fallback_action: Optional[str] = None


@dataclass
class Plan:
    goal: Goal
    steps: List[PlanStep]
    metadata: Dict[str, Any] = field(default_factory=dict)


def decompose_goal(
    goal: Goal,
    api_key: Optional[str] = None,
    workspace_root: str = ".",
) -> Plan:
    """
    Decompose a high-level goal into executable plan steps.
    Uses LLM if api_key provided, otherwise uses rule-based fallback.
    """
    if api_key:
        return _llm_decompose(goal, api_key, workspace_root)
    else:
        return _rule_based_decompose(goal, workspace_root)


def _llm_decompose(goal: Goal, api_key: str, workspace_root: str) -> Plan:
    """Use DeepSeek to decompose goal into steps."""
    try:
        from rfsn_companion.llm.deepseek_client import call_deepseek
    except ImportError:
        return _rule_based_decompose(goal, workspace_root)

    system = """You are a planning agent. Given a goal, decompose it into executable steps.

Output a JSON array of steps. Each step has:
- step_id: integer starting from 1
- action_name: one of [READ_FILE, WRITE_FILE, APPLY_PATCH, RUN_TESTS, WEB_SEARCH, BROWSE_URL, SHELL_EXEC, REMEMBER, RECALL]
- action_args: dict of arguments for the action
- description: brief description of what this step does
- depends_on: list of step_ids that must complete first (empty for first steps)

Example output:
[
  {"step_id": 1, "action_name": "WEB_SEARCH", "action_args": {"query": "..."}, "description": "Search for info", "depends_on": []},
  {"step_id": 2, "action_name": "BROWSE_URL", "action_args": {"url": "..."}, "description": "Read the page", "depends_on": [1]}
]

Output ONLY valid JSON, no markdown or explanation."""

    user = f"""Goal: {goal.description}

Constraints: {goal.constraints}
Context: {json.dumps(goal.context)}

Decompose into steps:"""

    try:
        resp = call_deepseek(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_key=api_key,
            temperature=0.0,
            max_tokens=4096,
        )

        content = resp.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            content = "\n".join(lines)

        steps_data = json.loads(content)
        steps = []

        for s in steps_data:
            steps.append(PlanStep(
                step_id=int(s.get("step_id", len(steps) + 1)),
                action_name=str(s.get("action_name", "READ_FILE")),
                action_args=dict(s.get("action_args", {})),
                description=str(s.get("description", "")),
                depends_on=list(s.get("depends_on", [])),
            ))

        return Plan(goal=goal, steps=steps, metadata={"source": "llm"})

    except Exception:
        # Fallback on error
        return _rule_based_decompose(goal, workspace_root)


def _rule_based_decompose(goal: Goal, workspace_root: str) -> Plan:
    """Simple rule-based decomposition for common patterns."""
    desc = goal.description.lower()
    steps = []

    # Pattern: "research X" or "find X"
    if any(kw in desc for kw in ["research", "find", "search", "learn about"]):
        topic = goal.description.split(maxsplit=1)[-1] if " " in goal.description else goal.description
        steps = [
            PlanStep(1, "WEB_SEARCH", {"query": topic, "num_results": 5}, f"Search for {topic}", []),
            PlanStep(2, "REMEMBER", {"content": f"Research on: {topic}"}, "Store research context", [1]),
        ]

    # Pattern: "fix X" or "debug X"
    elif any(kw in desc for kw in ["fix", "debug", "repair"]):
        steps = [
            PlanStep(1, "RUN_TESTS", {"argv": ["python", "-m", "pytest", "-q"]}, "Run tests to identify failures", []),
            PlanStep(2, "RECALL", {"query": "error"}, "Check memory for similar issues", [1]),
        ]

    # Pattern: "create X" or "write X"
    elif any(kw in desc for kw in ["create", "write", "build", "make"]):
        steps = [
            PlanStep(1, "RECALL", {"query": goal.description}, "Check for existing patterns", []),
            PlanStep(2, "REMEMBER", {"content": f"Creating: {goal.description}"}, "Store intent", []),
        ]

    # Default: just run tests
    else:
        steps = [
            PlanStep(1, "RUN_TESTS", {"argv": ["python", "-m", "pytest", "-q"]}, "Run tests", []),
        ]

    return Plan(goal=goal, steps=steps, metadata={"source": "rules"})
