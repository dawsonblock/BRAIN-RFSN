# cognitive/self_improvement.py
"""
Self-Improvement: Analyzes failures and proposes improvements to the system.
The recursive self-improvement loop with safety controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json
import os
import hashlib

from .episodic_memory import EpisodicMemory, Episode, EpisodeQuery


@dataclass
class ImprovementProposal:
    """A proposed improvement to the system."""
    proposal_id: str
    target: str  # prompts, strategies, tools, code
    description: str
    rationale: str
    changes: List[Dict[str, Any]]
    expected_impact: str
    risk_level: str  # low, medium, high
    confidence: float


@dataclass
class FailureAnalysis:
    """Analysis of a failure pattern."""
    pattern_id: str
    failure_type: str
    frequency: int
    root_causes: List[str]
    affected_episodes: List[str]
    suggested_fixes: List[str]


class SelfImprover:
    """
    Self-improvement engine that:
    1. Analyzes failure patterns from episodic memory
    2. Proposes improvements (prompts, strategies, code)
    3. Validates improvements through gate
    4. Tracks improvement outcomes
    """

    def __init__(
        self,
        episodic_store: EpisodicMemory,
        improvement_store_path: str,
        api_key: Optional[str] = None,
    ):
        self.episodic = episodic_store
        self.store_path = improvement_store_path
        os.makedirs(improvement_store_path, exist_ok=True)
        self.api_key = api_key
        self.index_path = os.path.join(improvement_store_path, "improvements_index.json")
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
            with open(self.index_path, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {
                "proposals": [],
                "applied": [],
                "rejected": [],
                "analyses": [],
            }

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def analyze_failures(self, min_failures: int = 2) -> List[FailureAnalysis]:
        """Analyze failure patterns from episodic memory."""
        failures = self.episodic.retrieve(
            EpisodeQuery(outcome="failure"),
            k=50
        )

        if len(failures) < min_failures:
            return []

        # Group failures by action type
        action_failures: Dict[str, List[Episode]] = {}
        for ep in failures:
            for action in ep.actions:
                if not action.get("success", True):
                    name = action["action"]
                    if name not in action_failures:
                        action_failures[name] = []
                    action_failures[name].append(ep)

        analyses = []
        for action, eps in action_failures.items():
            if len(eps) >= min_failures:
                # Extract error patterns
                errors = []
                for ep in eps:
                    for a in ep.actions:
                        if a["action"] == action and not a.get("success"):
                            errors.append(a.get("error", "unknown"))

                # Deduplicate and count errors
                error_counts: Dict[str, int] = {}
                for e in errors:
                    key = e[:50] if e else "unknown"
                    error_counts[key] = error_counts.get(key, 0) + 1

                top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]

                analysis = FailureAnalysis(
                    pattern_id=f"fa_{hashlib.sha256(action.encode()).hexdigest()[:8]}",
                    failure_type=action,
                    frequency=len(eps),
                    root_causes=[e[0] for e in top_errors],
                    affected_episodes=[ep.episode_id for ep in eps],
                    suggested_fixes=self._suggest_fixes(action, top_errors),
                )
                analyses.append(analysis)

                # Store analysis
                self.index["analyses"].append({
                    "pattern_id": analysis.pattern_id,
                    "failure_type": analysis.failure_type,
                    "frequency": analysis.frequency,
                    "timestamp": datetime.utcnow().isoformat(),
                })

        self._save_index()
        return analyses

    def _suggest_fixes(
        self,
        action: str,
        errors: List[Tuple[str, int]],
    ) -> List[str]:
        """Suggest fixes based on failure patterns."""
        suggestions = []

        for error, count in errors:
            error_lower = error.lower()

            # Common error patterns and fixes
            if "timeout" in error_lower:
                suggestions.append(f"Increase timeout for {action}")
            elif "not found" in error_lower or "no such file" in error_lower:
                suggestions.append(f"Add file existence check before {action}")
            elif "permission" in error_lower:
                suggestions.append(f"Check permissions before {action}")
            elif "network" in error_lower or "connection" in error_lower:
                suggestions.append(f"Add retry logic for {action}")
            elif "parse" in error_lower or "json" in error_lower:
                suggestions.append(f"Add input validation for {action}")
            else:
                suggestions.append(f"Review {action} implementation for: {error[:30]}")

        return suggestions[:3]

    def propose_improvement(
        self,
        analysis: FailureAnalysis,
    ) -> ImprovementProposal:
        """Generate an improvement proposal from a failure analysis."""
        proposal_id = f"imp_{hashlib.sha256(analysis.pattern_id.encode()).hexdigest()[:8]}"

        # Determine target and changes
        target = "strategies"
        changes = []
        risk = "low"

        if "timeout" in " ".join(analysis.root_causes).lower():
            target = "config"
            changes.append({
                "type": "increase_timeout",
                "action": analysis.failure_type,
                "current": 30,
                "proposed": 60,
            })
            risk = "low"

        elif "retry" in " ".join(analysis.suggested_fixes).lower():
            target = "tools"
            changes.append({
                "type": "add_retry",
                "action": analysis.failure_type,
                "max_retries": 3,
            })
            risk = "medium"

        else:
            target = "prompts"
            changes.append({
                "type": "add_guidance",
                "action": analysis.failure_type,
                "guidance": f"Avoid {analysis.failure_type} when: {'; '.join(analysis.root_causes[:2])}",
            })
            risk = "low"

        proposal = ImprovementProposal(
            proposal_id=proposal_id,
            target=target,
            description=f"Fix recurring {analysis.failure_type} failures ({analysis.frequency} occurrences)",
            rationale=f"Root causes: {'; '.join(analysis.root_causes[:2])}",
            changes=changes,
            expected_impact=f"Reduce {analysis.failure_type} failures by ~{min(80, analysis.frequency * 10)}%",
            risk_level=risk,
            confidence=min(0.9, 0.3 + 0.1 * analysis.frequency),
        )

        # Store proposal
        self.index["proposals"].append({
            "proposal_id": proposal.proposal_id,
            "target": proposal.target,
            "risk_level": proposal.risk_level,
            "confidence": proposal.confidence,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save_index()

        return proposal

    def apply_improvement(
        self,
        proposal: ImprovementProposal,
        gate_approved: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply an approved improvement.
        
        NOTE: This requires gate approval for safety.
        High-risk changes require human review.
        """
        if not gate_approved:
            return {
                "success": False,
                "error": "Gate approval required",
                "proposal": proposal,
            }

        if proposal.risk_level == "high":
            return {
                "success": False,
                "error": "High-risk improvement requires human review",
                "proposal": proposal,
            }

        # Apply changes based on target
        result = {"success": True, "applied": [], "proposal": proposal}

        for change in proposal.changes:
            if change["type"] == "increase_timeout":
                # This would modify config (placeholder)
                result["applied"].append(f"Would increase {change['action']} timeout to {change['proposed']}s")

            elif change["type"] == "add_retry":
                # This would modify tool code (placeholder)
                result["applied"].append(f"Would add retry logic to {change['action']}")

            elif change["type"] == "add_guidance":
                # This would modify prompts (placeholder)
                result["applied"].append(f"Would add guidance: {change['guidance'][:50]}...")

        # Track applied improvement
        self.index["applied"].append({
            "proposal_id": proposal.proposal_id,
            "timestamp": datetime.utcnow().isoformat(),
            "changes": result["applied"],
        })
        self._save_index()

        return result

    def get_improvement_stats(self) -> Dict[str, Any]:
        """Get self-improvement statistics."""
        return {
            "proposals_generated": len(self.index["proposals"]),
            "improvements_applied": len(self.index["applied"]),
            "improvements_rejected": len(self.index["rejected"]),
            "analyses_performed": len(self.index["analyses"]),
        }
