"""
Behavioral Monitor (The Amygdala).
Detects threats and generates risk signals (Cortisol).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class EventResult:
    risk_score: float = 0.0
    is_anomalous: bool = False
    explanation: str = ""

@dataclass
class SecurityReport:
    risk_percentage: float = 0.0
    recent_anomalies: List[Dict] = field(default_factory=list)

class BehavioralMonitor:
    def __init__(self):
        self.recent_events: List[Dict] = []
        self.risk_level: float = 0.0
        # Simple rule-based threat detection
        self.dangerous_patterns = [
            "rm -rf", "| bash", "> /dev/null", "/etc/shadow", "wget http", "curl http"
        ]

    def record_event(self, event_type: str, details: Dict[str, Any]) -> EventResult:
        """
        Records and analyzes an event for potential threats.
        """
        command = details.get("command", "")
        risk_score = 0.0
        is_anomalous = False
        explanation = ""

        for pattern in self.dangerous_patterns:
            if pattern in command:
                risk_score = 0.9
                is_anomalous = True
                explanation = f"Detected dangerous pattern: '{pattern}'"
                break
        
        if "sudo" in command and risk_score < 0.8:
            risk_score = 0.6
            explanation = "Use of sudo requires caution."

        self.risk_level = (self.risk_level * 0.5) + (risk_score * 0.5) # Decay risk over time
        
        event_log = {"type": event_type, "details": details, "risk": risk_score}
        self.recent_events.append(event_log)
        if len(self.recent_events) > 100:
            self.recent_events.pop(0)
            
        logger.debug(f"Event recorded: {event_type}, Risk: {risk_score:.2f}")
        return EventResult(risk_score=risk_score, is_anomalous=is_anomalous, explanation=explanation)

    def reset(self) -> None:
        """Resets the monitor to a safe state."""
        self.risk_level = 0.0
        self.recent_events = []
        logger.info("🛡️ BehavioralMonitor reset to baseline.")

    def get_security_report(self) -> Dict[str, Any]:
        """
        Returns a summary of the current security state.
        """
        report = {
            "risk_percentage": self.risk_level * 100,
            "total_events": len(self.recent_events)
        }
        return report

# Singleton instance
_monitor: Optional[BehavioralMonitor] = None

def get_monitor() -> BehavioralMonitor:
    global _monitor
    if _monitor is None:
        _monitor = BehavioralMonitor()
    return _monitor
