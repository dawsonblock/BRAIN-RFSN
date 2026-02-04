"""
Proactive Output Engine (The Striatum).
Generates spontaneous thoughts and curiosity signals (Dopamine).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cognitive.capsule_memory_core import get_memory_core
from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

@dataclass
class ProactiveThought:
    content: str
    source: str = "spontaneous"

class ProactiveOutputEngine:
    def __init__(self):
        self.memory_core = get_memory_core()
        self.entropy_level = 0.5 # Start with moderate entropy

    def scan_for_entropy(self) -> float:
        """
        Scans recent memory for repetitiveness to calculate entropy.
        High entropy = novel experiences. Low entropy = repetitive/boring.
        """
        recent_capsules = self.memory_core.retrieve_capsules(limit=10)
        if len(recent_capsules) < 5:
            self.entropy_level = 0.8 # Not enough data, assume high entropy
            return self.entropy_level

        # Simple entropy check: count unique content hashes
        unique_contents = {hash(c.content) for c in recent_capsules}
        repetition_ratio = 1.0 - (len(unique_contents) / len(recent_capsules))
        
        # Low repetition = high entropy
        self.entropy_level = 1.0 - repetition_ratio
        logger.debug(f"Entropy calculated: {self.entropy_level:.2f}")
        return self.entropy_level

    def generate_proactive_thought(self) -> Optional[ProactiveThought]:
        """
        Generates a spontaneous thought or question based on recent context.
        """
        if self.entropy_level > 0.6:
            return None # No need for proactive thought if entropy is high

        recent_capsules = self.memory_core.retrieve_capsules(limit=3)
        if not recent_capsules:
            return None

        context = "\n".join([f"- {c.content}" for c in recent_capsules])
        prompt = f"""
        Based on this recent activity:
        {context}
        
        What is one unexpected question I could ask to discover something new?
        Frame it as a hypothesis. Be concise.
        """
        
        response = call_deepseek(prompt, temperature=0.8)
        if "content" in response and response["content"]:
            thought_content = response["content"]
            logger.info(f"Generated proactive thought: {thought_content}")
            return ProactiveThought(content=thought_content)
        
        return None

# Singleton instance
_proactive_engine: Optional[ProactiveOutputEngine] = None

def get_proactive_engine() -> ProactiveOutputEngine:
    global _proactive_engine
    if _proactive_engine is None:
        _proactive_engine = ProactiveOutputEngine()
    return _proactive_engine
