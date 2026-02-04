# modes.py
"""
RFSN Mode Configuration System

Three operational modes:
- KERNEL: Auditable safety core (gate, ledger, policy)
- LEARNER: SWE-bench training (bandit, proposers, outcomes)
- RESEARCH: AGI exploration (cognition, consciousness, benchmarks)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict


class RFSNMode(Enum):
    """Operational modes for RFSN system."""
    DIALOGUE = "dialogue"  # 💬 Direct Interaction
    KERNEL = "kernel"      # 🔒 Auditable safety core
    LEARNER = "learner"    # 📈 SWE-bench training
    RESEARCH = "research"  # 🧪 AGI exploration


@dataclass
class ModeConfig:
    """Configuration for a specific mode."""
    mode: RFSNMode
    display_name: str
    icon: str
    description: str
    tabs: List[str]
    components: List[str]  # Module paths to lazy load


# Mode configurations
MODE_CONFIGS: Dict[RFSNMode, ModeConfig] = {
    RFSNMode.DIALOGUE: ModeConfig(
        mode=RFSNMode.DIALOGUE,
        display_name="Dialogue",
        icon="💬",
        description="Direct interaction terminal: chat, commands",
        tabs=["Mission Control"],
        components=["consciousness", "cognitive"],
    ),
    RFSNMode.KERNEL: ModeConfig(
        mode=RFSNMode.KERNEL,
        display_name="Kernel",
        icon="🔒",
        description="Auditable safety core: gate, ledger, policy",
        tabs=["Gate Stats", "Ledger View", "Replay"],
        components=["rfsn_kernel"],
    ),
    RFSNMode.LEARNER: ModeConfig(
        mode=RFSNMode.LEARNER,
        display_name="Learner",
        icon="📈",
        description="SWE-bench training: bandit, proposers, outcomes",
        tabs=["Bandit Dashboard", "Outcomes", "SWE-bench Runner"],
        components=["upstream_learner", "rfsn_companion"],
    ),
    RFSNMode.RESEARCH: ModeConfig(
        mode=RFSNMode.RESEARCH,
        display_name="Research",
        icon="🧪",
        description="AGI exploration: cognition, consciousness, benchmarks",
        tabs=["Mission Control", "Brain MRI", "Memory Bank"],
        components=["cognitive", "consciousness", "benchmarks"],
    ),
}


def get_mode_config(mode: RFSNMode) -> ModeConfig:
    """Get configuration for a mode."""
    return MODE_CONFIGS[mode]


def get_mode_options() -> List[str]:
    """Get list of mode display names with icons for UI selector."""
    return [f"{c.icon} {c.display_name}" for c in MODE_CONFIGS.values()]


def parse_mode_selection(selection: str) -> RFSNMode:
    """Parse UI selection string back to mode enum."""
    for mode, config in MODE_CONFIGS.items():
        if f"{config.icon} {config.display_name}" == selection:
            return mode
    return RFSNMode.RESEARCH  # Default
