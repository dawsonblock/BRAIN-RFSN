"""
Reasoning Engine (The Cortex).
Handles primary problem-solving and planning.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

@dataclass
class Context:
    problem_statement: str
    code_files: Dict[str, str] = field(default_factory=dict)
    test_outputs: List[str] = field(default_factory=list)
    past_memories: List[str] = field(default_factory=list)
    core_beliefs: List[str] = field(default_factory=list)

@dataclass
class ReasoningResult:
    understanding: str
    suggested_approach: str
    confidence: float

class ReasoningEngine:
    def __init__(self):
        pass

    def build_context(self, problem_statement: str, 
                      code_files: Optional[Dict[str, str]] = None, 
                      test_outputs: Optional[List[str]] = None,
                      past_memories: Optional[List[str]] = None,
                      core_beliefs: Optional[List[str]] = None) -> Context:
        """Constructs a structured context object."""
        return Context(
            problem_statement=problem_statement,
            code_files=code_files or {},
            test_outputs=test_outputs or [],
            past_memories=past_memories or [],
            core_beliefs=core_beliefs or []
        )

    def refine_prompt(self, original_prompt: str, brain_state_summary: str) -> str:
        """P2P Refinement: Use the LLM to 'sharpen' the reasoning prompt before execution."""
        try:
            # Quick call using deepseek-chat (cheaper) to optimize the prompt
            resp = call_deepseek(original_prompt, temperature=0.2)
            if isinstance(resp, dict) and "content" in resp:
                return resp["content"]
            return original_prompt
        except Exception:
            return original_prompt

    def reason(self, context: Context, temperature: float = 0.2, model: Optional[str] = None) -> ReasoningResult:
        """
        Uses the LLM to reason about the provided context and generate a plan.
        Includes P2P Refinement and Identity (Core Belief) bias.
        """
        code_context = "\n".join([f"--- {path} ---\n{content}" for path, content in context.code_files.items()])
        test_context = "\n".join(context.test_outputs)

        prompt = f"""
        **Problem Statement:**
        {context.problem_statement}

        **Relevant Code Files:**
        {code_context if code_context else 'None'}

        **Recent Test Outputs/Errors:**
        {test_context if test_context else 'None'}
        """

        if context.past_memories:
            prompt += "\n\n### Lessons from Past Experiences (Memory)\n"
            for i, mem in enumerate(context.past_memories):
                prompt += f"Memory {i+1}: {mem}\n"

        if context.core_beliefs:
            prompt += "\n\n### Core Identity Alignment (Core Beliefs)\n"
            for belief in context.core_beliefs:
                principle = belief.principle if hasattr(belief, "principle") else str(belief)
                prompt += f"- {principle}\n"
        
        # Inject Emotional Resonance (Neuro-Dynamic Bias)
        if temperature > 0.6:
            prompt += "\n\n### Affective Tone: HIGH CREATIVITY\nExplore novel approaches."
        elif temperature < 0.2:
            prompt += "\n\n### Affective Tone: HIGH ANALYTICAL RIGOR\nFocus on deterministic, proven fixes."

        prompt += """
        --- 
        **Your Task:**
        1.  **Understand:** In one sentence, what is the core problem?
        2.  **Approach:** In a few sentences, what is the most logical next step to solve this?
        3.  **Confidence:** On a scale of 0.0 to 1.0, how confident are you?

        Format your response as a JSON object with keys "understanding", "approach", and "confidence".
        """

        # P2P: Refine the prompt (Optional: could be gated by dopamine/complexity)
        # For now, we'll just use the prompt as is but we could call self.refine_prompt
        # if complexity warrants.
        response = call_deepseek(prompt, temperature=temperature, model=model)
        
        if isinstance(response, dict) and "content" in response and response["content"]:
            try:
                import json
                result_json = json.loads(response["content"])
                return ReasoningResult(
                    understanding=result_json.get("understanding", ""),
                    suggested_approach=result_json.get("approach", ""),
                    confidence=float(result_json.get("confidence", 0.5))
                )
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"Failed to parse reasoning response: {e}")
                # Fallback to simple parsing if JSON fails
                return ReasoningResult(
                    understanding="Could not parse LLM response.",
                    suggested_approach=response["content"],
                    confidence=0.3
                )
        
        return ReasoningResult(
            understanding="Failed to get a response from the reasoning core.",
            suggested_approach="",
            confidence=0.0
        )

# Singleton instance
_reasoning_engine: Optional[ReasoningEngine] = None

def get_reasoning_engine() -> ReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine
