"""
Dream Reality Sync (DRS).
Manages the offline processing 'REM cycles' for memory consolidation,
self-repair, and trauma processing (nightmares).
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

# Import sub-components
from consciousness.memory_pruner import MemoryPruner
from consciousness.nightmare_protocol import NightmareProtocol
from learning.knowledge_base import get_knowledge_base
from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

@dataclass
class DreamReport:
    """Summary of what happened during the REM cycle."""
    lessons_learned: List[str]
    memories_pruned: int
    hypotheticals_simulated: List[str]
    restoration_score: float 
    mode: str = "NORMAL"

class DreamRealitySync:
    def __init__(self, neuro_modulator=None, injection_shield=None):
        self.wakefulness_battery = 100.0 # Starts fully awake
        self.max_battery = 100.0
        self.decay_rate = 5.0 # Battery drain per task
        
        self.knowledge_base = get_knowledge_base()
        self.pruner = MemoryPruner()
        self.nightmare_engine = NightmareProtocol(
            self.knowledge_base, 
            neuro_modulator=neuro_modulator,
            injection_shield=injection_shield
        )
        
    def mark_activity(self, effort_level: float = 1.0):
        """Drains the battery based on cognitive load."""
        drain = self.decay_rate * effort_level
        self.wakefulness_battery = max(0.0, self.wakefulness_battery - drain)
        logger.debug(f"🔋 WAKEFULNESS: {self.wakefulness_battery:.1f}%")

    def should_sleep(self) -> bool:
        """Check if the agent needs a REM cycle."""
        return self.wakefulness_battery < 20.0

    def enter_rem_cycle(self, recent_failures: List[Dict], security_incidents: List[Dict] = None) -> DreamReport:
        """
        Triggers the Dreaming State.
        This is an offline LLM process that reviews history and heals.
        """
        logger.info("💤 ENTERING REM CYCLE... (Offline Optimization)")
        security_incidents = security_incidents or []
        
        # 1. CHECK FOR TRAUMA (Nightmare Protocol)
        critical_incidents = [
            inc for inc in security_incidents 
            if inc.get('risk_score', 0) > 0.8 or inc.get('is_anomalous')
        ]
        
        if critical_incidents:
            logger.warning("⚠️ TRAUMA DETECTED. PRIORITIZING NIGHTMARE PROTOCOL.")
            nightmare_results = []
            for incident in critical_incidents:
                result = self.nightmare_engine.enter_trauma_loop(incident)
                if result:
                    nightmare_results.append(result)
            
            # Waking up exhausted but safe
            self.wakefulness_battery = 50.0  
            return DreamReport(
                lessons_learned=nightmare_results,
                memories_pruned=0, 
                hypotheticals_simulated=[],
                restoration_score=0.5,
                mode="NIGHTMARE_RECOVERY"
            )

        # 2. NORMAL HIPPOCAMPAL REPLAY (Review Failures)
        lessons = []
        for failure in recent_failures[-3:]: 
            # Extract emotion profile from failure context if available
            emotion_info = failure.get('emotion_profile', {})
            intensity = sum(emotion_info.values()) if emotion_info else 0.5
            
            lesson = self._dream_about_failure(failure, emotion_info)
            if lesson:
                lessons.append(lesson)
                # Boost confidence if the emotional intensity was high
                conf = min(0.99, 0.8 + (intensity * 0.2))
                self.knowledge_base.add_knowledge(
                    category="heuristic",
                    title=f"Dream Insight: {failure.get('task_description', 'unknown')}",
                    content=lesson,
                    tags=["dream_generated", "self_correction", "emotional_anchor"],
                    confidence=conf
                )
        # 3. SYNAPTIC PRUNING (Database Hygiene)
        pruning_stats = self.pruner.execute_rem_cycle()
        logger.info(f"🗑️ PRUNED: {pruning_stats.deleted_episodes} stale memories.")

        # 4. RESTORATION (Reset)
        self.wakefulness_battery = self.max_battery
        
        logger.info(f"✨ WAKING UP. Learned: {len(lessons)} new heuristics.")
        return DreamReport(
            lessons_learned=lessons,
            memories_pruned=pruning_stats.deleted_episodes,
            hypotheticals_simulated=[f"Simulated fix for {f.get('task_description')}" for f in recent_failures],
            restoration_score=1.0,
            mode="RESTED"
        )

    def _dream_about_failure(self, failure_context: Dict, emotions: Optional[Dict] = None) -> Optional[str]:
        """Uses the LLM to 'hallucinate' a solution to a past problem, hued by emotion."""
        emotion_context = f"Emotional State: {emotions}" if emotions else ""
        
        prompt = f"""
        [DREAM MODE ACTIVE]
        You are replaying a recent memory of a failure. 
        {emotion_context}
        
        Task: {failure_context.get('task_description')}
        Error: {failure_context.get('error')}
        
        Analyze this objectively. What is the ONE fundamental principle 
        we ignored? Answer in a single sentence heuristic.
        """
        try:
            resp = call_deepseek(prompt, temperature=0.1) 
            return resp.get('content', '').strip() if isinstance(resp, dict) else str(resp)
        except Exception:
            return None

# Singleton instance
_dream_sync: Optional[DreamRealitySync] = None

def get_dream_sync_clock(nm=None, shield=None) -> DreamRealitySync:
    global _dream_sync
    if _dream_sync is None:
        _dream_sync = DreamRealitySync(neuro_modulator=nm, injection_shield=shield)
    return _dream_sync
