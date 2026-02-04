"""
Neuro-Modulation Engine (NME).
Translates system state metrics into global chemical modulators.
"""
from dataclasses import dataclass
import logging
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class BrainState:
    temperature: float      # LLM Creativity (0.0 - 1.0)
    gate_strictness: float  # Security Paranoia (0.0 - 1.0)
    search_depth: int       # Retrieval context limit
    patience: float         # Persistence/Retries (0.0 - 1.0)
    cooperation: float      # Weight of user feedback (0.0 - 1.0)
    mode: str               # "FLOW", "PANIC", "CONFUSION", "FOCUSED", "NIGHTMARE"

class NeuroModulator:
    def __init__(self):
        # Baseline "Resting" State
        self.base_temp = 0.2
        self.base_strictness = 0.5
        self.base_patience = 0.5
        self.base_cooperation = 0.5
        self.current_state: Optional[BrainState] = None
        self.reset_baseline()
        
    def regulate_state(self, cortisol: float, dopamine: float, acetylcholine: float, 
                      serotonin: float = 0.5, oxytocin: float = 0.5,
                      identity_offsets: Optional[dict] = None) -> BrainState:
        """
        Adjust cognitive parameters based on chemical levels.
        
        Args:
            cortisol (0.0-1.0): "Stress" from BehavioralMonitor risk scores.
            dopamine (0.0-1.0): "Curiosity" from ProactiveOutputEngine entropy.
            acetylcholine (0.0-1.0): "Focus" from recent task success rates.
            serotonin (0.0-1.0): "Stability" from history of successful sleep/cycles.
            oxytocin (0.0-1.0): "Bonding" from memory relevance/past identity sync.
        """
        # 1. Cortisol Effect (The "Fear" Response)
        if cortisol > 0.7:
            target_temp = 0.0
            target_strictness = 1.0
            mode = "PANIC"
            search_depth = 2
            target_patience = 0.1 # Impatient, frantic
            target_cooperation = 0.1 # Self-preservation mode
            
        else:
            # 2. Dopamine Effect (The "Flow" Response - Creativity/Entropy)
            target_temp = self.base_temp + (dopamine * 0.6)
            
            # 3. Serotonin (The "Stability" Modulator - Patience/Error Resilience)
            # High serotonin -> High patience, lower creative noise
            target_patience = self.base_patience + (serotonin * 0.4)
            target_temp -= (serotonin * 0.1) 
            
            # 4. Oxytocin (The "Cooperation" Modulator - Social/Identity Sync)
            # High oxytocin -> High cooperation, alignment with user
            target_cooperation = self.base_cooperation + (oxytocin * 0.4)
            target_strictness = self.base_strictness - (oxytocin * 0.2)
            
            # 5. Acetylcholine Effect (The "Focus" Response - Success Rate)
            if acetylcholine > 0.6:
                mode = "FLOW" if dopamine > 0.5 else "FOCUSED"
                search_depth = 10 
            else:
                mode = "CONFUSION"
                search_depth = 20
                target_temp += 0.1
                target_strictness += 0.2
        
        # 6. Apply Identity Feedback Offsets
        if identity_offsets:
            target_temp += identity_offsets.get("temp_offset", 0.0)
            target_strictness += identity_offsets.get("strictness_offset", 0.0)
        
        # Clamp values
        target_temp = max(0.0, min(1.0, target_temp))
        target_strictness = max(0.0, min(1.0, target_strictness))
        target_patience = max(0.0, min(1.0, target_patience))
        target_cooperation = max(0.0, min(1.0, target_cooperation))
        
        self.current_state = BrainState(
            temperature=target_temp,
            gate_strictness=target_strictness,
            search_depth=search_depth,
            patience=target_patience,
            cooperation=target_cooperation,
            mode=mode
        )
        
        logger.info(f"🧠 NEURO-STATE: {mode} | Temp: {target_temp:.2f} | Patience: {target_patience:.2f}")
        return self.current_state

    def reset_baseline(self):
        """Resets the brain to a calm state (usually after sleep)."""
        logger.info("🧪 Chemicals neutralized. Resetting to baseline.")
        self.current_state = BrainState(
            temperature=self.base_temp,
            gate_strictness=self.base_strictness,
            search_depth=5,
            patience=self.base_patience,
            cooperation=self.base_cooperation,
            mode="FOCUSED"
        )

    def adapt_from_trauma(self, trauma_type: str, severity: float) -> dict:
        """
        Permanently shifts baseline parameters based on nightmare lessons.
        Called after NightmareProtocol successfully derives a survival strategy.
        
        Args:
            trauma_type: Category of trauma (e.g., "security_breach", "data_loss", "timeout")
            severity: How severe the incident was (0.0-1.0)
            
        Returns:
            Dictionary of baseline adjustments made
        """
        adjustments = {}
        
        if trauma_type == "security_breach":
            # Increase paranoia permanently
            delta = severity * 0.1
            self.base_strictness = min(1.0, self.base_strictness + delta)
            adjustments["strictness"] = f"+{delta:.2f} -> {self.base_strictness:.2f}"
            
        elif trauma_type == "data_loss":
            # Increase patience (slower, more careful)
            delta = severity * 0.05
            self.base_patience = min(1.0, self.base_patience + delta)
            adjustments["patience"] = f"+{delta:.2f} -> {self.base_patience:.2f}"
            
        elif trauma_type == "timeout":
            # Reduce patience (act faster next time)
            delta = severity * 0.03
            self.base_patience = max(0.0, self.base_patience - delta)
            adjustments["patience"] = f"-{delta:.2f} -> {self.base_patience:.2f}"
            
        elif trauma_type == "hallucination":
            # Lower creativity baseline
            delta = severity * 0.05
            self.base_temp = max(0.0, self.base_temp - delta)
            adjustments["temperature"] = f"-{delta:.2f} -> {self.base_temp:.2f}"
        
        if adjustments:
            logger.warning(f"🧬 TRAUMA ADAPTATION: {trauma_type} | Adjustments: {adjustments}")
        
        return adjustments
