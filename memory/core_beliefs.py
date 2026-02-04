"""
Core Beliefs - Immutable survival rules derived from trauma processing.

These are read-only, high-priority principles that get injected into all agent prompts.
They represent lessons learned through the Nightmare Protocol.
"""
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CoreBelief:
    """An immutable survival principle derived from trauma."""
    principle: str          # The rule itself (e.g., "Never execute eval() on user input")
    origin_trauma: str      # What nightmare derived this (e.g., "security_breach: code injection")
    created_at: float       # Unix timestamp
    trauma_severity: float  # How severe the original incident was (0.0-1.0)
    immutable: bool = True  # Core beliefs cannot be changed
    
    def to_prompt_line(self) -> str:
        """Format for injection into LLM prompts."""
        return f"⚠️ CORE BELIEF: {self.principle}"


class CoreBeliefStore:
    """
    Manages immutable survival rules learned from Nightmare Protocol.
    These beliefs are injected into every prompt to ensure the agent
    never repeats catastrophic mistakes.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = Path(persist_path) if persist_path else Path("core_beliefs.json")
        self.beliefs: List[CoreBelief] = []
        self._load()
    
    def _load(self):
        """Load beliefs from disk."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, 'r') as f:
                    data = json.load(f)
                self.beliefs = [
                    CoreBelief(**b) for b in data.get("beliefs", [])
                ]
                logger.info(f"💎 Loaded {len(self.beliefs)} Core Beliefs")
            except Exception as e:
                logger.error(f"Failed to load Core Beliefs: {e}")
                self.beliefs = []
        else:
            logger.info("💎 No existing Core Beliefs found. Starting fresh.")
    
    def _save(self):
        """Persist beliefs to disk."""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump({
                    "beliefs": [asdict(b) for b in self.beliefs],
                    "updated_at": time.time()
                }, f, indent=2)
            logger.debug(f"💾 Saved {len(self.beliefs)} Core Beliefs to {self.persist_path}")
        except Exception as e:
            logger.error(f"Failed to persist Core Beliefs: {e}")
    
    def crystallize(self, lesson: str, trauma_context: Dict) -> CoreBelief:
        """
        Convert a nightmare-derived lesson into a permanent Core Belief.
        
        Args:
            lesson: The survival strategy/heuristic learned
            trauma_context: Context about the original incident
            
        Returns:
            The newly created CoreBelief
        """
        belief = CoreBelief(
            principle=lesson,
            origin_trauma=f"{trauma_context.get('event_type', 'unknown')}: {trauma_context.get('anomaly_type', 'unspecified')}",
            created_at=time.time(),
            trauma_severity=trauma_context.get('risk_score', 0.5),
            immutable=True
        )
        
        # Check for duplicate principles
        existing_principles = [b.principle.lower() for b in self.beliefs]
        if belief.principle.lower() not in existing_principles:
            self.beliefs.append(belief)
            self._save()
            logger.warning(f"💎 NEW CORE BELIEF CRYSTALLIZED: {belief.principle[:60]}...")
        else:
            logger.info(f"💎 Belief already exists, skipping: {belief.principle[:40]}...")
        
        return belief
    
    def get_active_beliefs(self) -> List[CoreBelief]:
        """Return all active Core Beliefs."""
        return self.beliefs.copy()
    
    def inject_into_prompt(self, base_prompt: str) -> str:
        """
        Prepend Core Beliefs to a prompt for LLM context.
        
        Args:
            base_prompt: The original prompt
            
        Returns:
            Prompt with Core Beliefs injected at the start
        """
        if not self.beliefs:
            return base_prompt
        
        belief_lines = [b.to_prompt_line() for b in self.beliefs]
        belief_section = "\n".join([
            "=== CORE BELIEFS (NEVER VIOLATE) ===",
            *belief_lines,
            "=== END CORE BELIEFS ===",
            ""
        ])
        
        return belief_section + base_prompt
    
    def count(self) -> int:
        """Return number of stored beliefs."""
        return len(self.beliefs)


# Singleton instance
_belief_store: Optional[CoreBeliefStore] = None


def get_core_belief_store(persist_path: Optional[str] = None) -> CoreBeliefStore:
    """Get or create the singleton CoreBeliefStore."""
    global _belief_store
    if _belief_store is None:
        _belief_store = CoreBeliefStore(persist_path)
    return _belief_store
