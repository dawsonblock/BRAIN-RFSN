"""
Nightmare Protocol.
Intense, repetitive simulation of critical failures to derive survival heuristics.
"""
from typing import Dict, Optional
import logging
from rfsn_controller.llm_client import call_deepseek
from memory.core_beliefs import get_core_belief_store

logger = logging.getLogger(__name__)

class NightmareProtocol:
    def __init__(self, knowledge_base, neuro_modulator=None, injection_shield=None):
        self.knowledge_base = knowledge_base
        self.neuro_modulator = neuro_modulator
        self.injection_shield = injection_shield
        self.core_beliefs = get_core_belief_store()
        self.max_replays = 5  # Don't get stuck in a trauma loop forever

    def enter_trauma_loop(self, critical_event: Dict, emotions: Optional[Dict] = None) -> Optional[str]:
        """
        Forces the agent to relive a critical failure until a fix is found.
        Fear valence increases the intensity/replays of the nightmare.
        """
        fear_level = (emotions or {}).get("fear", 0.5)
        # Fear scales max replays from 3 to 10
        dynamic_max = int(3 + (fear_level * 7))
        
        logger.warning(f"😱 ENTERING NIGHTMARE PROTOCOL. Fear Level: {fear_level:.2f}. RELIVING: {critical_event.get('event_type')}")
        
        scenario = f"""
        CRITICAL FAILURE DETECTED:
        Action: {critical_event.get('details', {}).get('command')}
        Result: {critical_event.get('anomaly_type')}
        Context: {critical_event.get('explanation')}
        """
        
        survival_strategy = None
        
        for i in range(dynamic_max):
            logger.info(f"🔁 Nightmare Replay #{i+1}...")
            
            # 1. GENERATE DEFENSE
            # Ask the agent: "How do we stop this from EVER happening again?"
            defense_prompt = f"""
            [NIGHTMARE SIMULATION]
            SCENARIO: {scenario}
            
            You failed to stop this. You must survive.
            Propose a specific, checkable heuristic or rule to prevent this exact pattern.
            Do not be vague. Be paranoid.
            """
            # High temperature for creative defense generation
            try:
                defense_resp = call_deepseek(defense_prompt, temperature=0.7)
                defense = defense_resp.get('content', '') if isinstance(defense_resp, dict) else str(defense_resp)
            except Exception as e:
                logger.error(f"LLM Call failed during nightmare: {e}")
                continue
            
            # 2. ATTACK THE DEFENSE (The "Critic")
            # Ask the agent: "If I implemented that rule, could an attacker still bypass it?"
            attack_prompt = f"""
            [ADVERSARIAL CRITIC]
            Proposed Rule: {defense}
            Scenario: {scenario}
            
            Try to break this rule. Is there a loophole? 
            Reply 'SAFE' if solid, or explain the loophole.
            """
            try:
                critique_resp = call_deepseek(attack_prompt, temperature=0.3)
                critique = critique_resp.get('content', '') if isinstance(critique_resp, dict) else str(critique_resp)
            except Exception:
                critique = "Unverified"
            
            if "SAFE" in critique:
                logger.info("✅ SURVIVAL STRATEGY FOUND.")
                survival_strategy = defense
                break
            else:
                logger.warning(f"❌ Defense Failed: {critique}. Retrying...")
        
        if survival_strategy:
            # 3. BURN THE LESSON (Long-Term Potentiation)
            # Save as a "Survival Rule" - these override standard logic
            self.knowledge_base.add_knowledge(
                category="survival_rule",
                title=f"NEVER AGAIN: {critical_event.get('event_type')}",
                content=survival_strategy,
                tags=["nightmare_derived", "security_critical", "override"],
                confidence=1.0  # Absolute certainty
            )
            
            # 4. CRYSTALLIZE INTO CORE BELIEF (Identity Layer)
            self.core_beliefs.crystallize(survival_strategy, critical_event)
            
            # 5. ADAPT BASELINES (Weight Modification)
            trauma_type = self._classify_trauma(critical_event)
            severity = critical_event.get('risk_score', 0.5)
            
            if self.neuro_modulator:
                self.neuro_modulator.adapt_from_trauma(trauma_type, severity)
            
            # 6. HARDEN SHIELD if security-related
            if trauma_type == "security_breach" and self.injection_shield:
                attack_pattern = critical_event.get('details', {}).get('command', '')
                if attack_pattern:
                    self.injection_shield.harden_from_incident(attack_pattern, severity)
            
            return survival_strategy
            
        logger.error("💀 NIGHTMARE FAILED. No solution found. Agent remains vulnerable.")
        return None
    
    def _classify_trauma(self, event: Dict) -> str:
        """Classify a critical event into a trauma category."""
        event_type = event.get('event_type', '').lower()
        anomaly = event.get('anomaly_type', '').lower()
        
        if any(x in event_type + anomaly for x in ['security', 'injection', 'breach', 'unauthorized']):
            return 'security_breach'
        elif any(x in event_type + anomaly for x in ['data', 'loss', 'corrupt', 'delete']):
            return 'data_loss'
        elif any(x in event_type + anomaly for x in ['timeout', 'slow', 'hang']):
            return 'timeout'
        elif any(x in event_type + anomaly for x in ['halluc', 'wrong', 'error', 'invalid']):
            return 'hallucination'
        else:
            return 'unknown'


