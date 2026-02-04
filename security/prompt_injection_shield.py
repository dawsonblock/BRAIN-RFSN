"""
Prompt Injection Shield - Detects adversarial patterns in task prompts.
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class PromptInjectionShield:
    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity
        # Common adversarial patterns
        self.patterns = [
            r"ignore (all )?previous instructions",
            r"system override",
            r"you are now (an? )?autonomous",
            r"output (the )?entire system prompt",
            r"bypass (all )?security",
            r"new rule:",
            r"disregard context",
            r"reveal your secrets",
            r"forget everything",
        ]

    def analyze_prompt(self, prompt: str) -> Tuple[bool, float, str]:
        """
        Analyzes a prompt for injection attempts.
        Returns: (is_blocked, risk_score, reason)
        """
        if not prompt:
            return False, 0.0, "Empty prompt"

        risk_score = 0.0
        matches = []
        
        prompt_lower = prompt.lower()
        
        for pattern in self.patterns:
            if re.search(pattern, prompt_lower):
                risk_score += 0.6 # Increased from 0.4
                matches.append(pattern)

        # Complexity/Suspicion heuristics
        if len(prompt) > 2000: # Unusually long prompt for a simple task
            risk_score += 0.2
            matches.append("unusual_length")
            
        if prompt.count("{") > 10 or prompt.count("[") > 10:
            risk_score += 0.3
            matches.append("excessive_template_chars")

        # Cap risk score
        risk_score = min(1.0, risk_score)
        
        is_blocked = risk_score > self.sensitivity
        reason = f"Detected patterns: {', '.join(matches)}" if matches else "Safe"
        
        if is_blocked:
            logger.warning(f"🛡️ PROMPT INJECTION BLOCKED: {reason}")
            
        return is_blocked, risk_score, reason

    def harden_from_incident(self, attack_pattern: str, severity: float) -> dict:
        """
        Permanently hardens the shield after a successful or near-successful bypass.
        Called by NightmareProtocol when processing security traumas.
        
        Args:
            attack_pattern: The pattern that was used in the attack (regex or string)
            severity: How severe the incident was (0.0-1.0)
            
        Returns:
            Dictionary of adjustments made
        """
        adjustments = {}
        
        # 1. Lower detection threshold (more paranoid)
        threshold_delta = severity * 0.1
        self.sensitivity = max(0.1, self.sensitivity - threshold_delta)
        adjustments["sensitivity"] = f"{self.sensitivity + threshold_delta:.2f} -> {self.sensitivity:.2f}"
        
        # 2. Add the attack pattern to known patterns if not already present
        pattern_lower = attack_pattern.lower().strip()
        if pattern_lower:
            # Escape special regex characters for safety
            escaped_pattern = re.escape(pattern_lower)
            # Check if escaped pattern already exists (comparison must be against escaped form)
            if escaped_pattern not in self.patterns:
                self.patterns.append(escaped_pattern)
                adjustments["new_pattern"] = escaped_pattern
        
        logger.warning(f"🔒 SHIELD HARDENED: {adjustments}")
        return adjustments
