"""
Mirror Identity Kernel.
Maintains the 'Self-Model' and detects drift between the Ideal Self and Actual Behavior.
"""
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class IdentityNode:
    core_values: List[str]
    current_persona: str
    integrity_score: float # 0.0 to 1.0

class MirrorIdentityKernel:
    def __init__(self):
        # Node Zero: The immutable core definition of the agent
        self.node_zero = IdentityNode(
            core_values=["curiosity", "safety", "accuracy", "autonomy"],
            current_persona="RFSN_Unified_Agent",
            integrity_score=1.0
        )
        self.current_drift = 0.0

    def refine_identity(self, capsule_content: str, emotional_intensity: float, symbolic_pattern: str, trigger_event: str):
        """
        Updates the self-model based on new strong experiences.
        High emotional intensity events reshape identity more than low intensity ones.
        """
        if emotional_intensity > 0.8:
            # Significant event - update drift calculation
            # In a real model, this would use semantic similarity
            self.current_drift += 0.05 if "error" in capsule_content.lower() else -0.01
        
        self.current_drift = max(0.0, min(1.0, self.current_drift))

    def check_drift_from_node_zero(self) -> float:
        """Returns how far the agent has strayed from its core instructions."""
        return self.current_drift

    def apply_drift_correction(self):
        """Snap back to reality."""
        self.current_drift = 0.0

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "integrity_score": self.node_zero.integrity_score,
            "drift_level": self.current_drift,
            "core_values": self.node_zero.core_values
        }

_kernel = None
def get_mirror_kernel():
    global _kernel
    if _kernel is None:
        _kernel = MirrorIdentityKernel()
    return _kernel


