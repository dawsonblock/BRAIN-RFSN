# tests/test_self_improvement.py
"""Tests for self-improvement system."""
from __future__ import annotations


from cognitive.episodic_memory import Episode, EpisodicMemory
from cognitive.self_improvement import SelfImprover, ImprovementProposal


def test_analyze_failures_finds_patterns(tmp_path):
    """Failure analysis should find recurring patterns."""
    ep_path = str(tmp_path / "episodes")
    imp_path = str(tmp_path / "improvements")

    episodic = EpisodicMemory(ep_path)

    # Create episodes with repeated failures
    for i in range(5):
        episodic.store(Episode(
            episode_id=f"ep{i}",
            timestamp=f"2026-02-03T12:0{i}:00",
            goal="Test goal",
            actions=[
                {"action": "WEB_SEARCH", "success": False, "error": "Network timeout"},
            ],
            outcome="failure",
            reward=0.0,
        ))

    improver = SelfImprover(episodic, imp_path)
    analyses = improver.analyze_failures(min_failures=2)

    assert len(analyses) >= 1
    assert analyses[0].failure_type == "WEB_SEARCH"
    assert analyses[0].frequency >= 5
    assert "timeout" in analyses[0].root_causes[0].lower()


def test_propose_improvement_from_analysis(tmp_path):
    """Should generate improvement proposal from failure analysis."""
    ep_path = str(tmp_path / "episodes")
    imp_path = str(tmp_path / "improvements")

    episodic = EpisodicMemory(ep_path)
    for i in range(3):
        episodic.store(Episode(
            episode_id=f"ep{i}",
            timestamp=f"2026-02-03T12:0{i}:00",
            goal="Test goal",
            actions=[
                {"action": "BROWSE_URL", "success": False, "error": "Connection refused"},
            ],
            outcome="failure",
            reward=0.0,
        ))

    improver = SelfImprover(episodic, imp_path)
    analyses = improver.analyze_failures(min_failures=2)

    assert len(analyses) >= 1

    proposal = improver.propose_improvement(analyses[0])
    assert isinstance(proposal, ImprovementProposal)
    assert proposal.proposal_id
    assert proposal.target in ["prompts", "strategies", "tools", "config"]


def test_apply_improvement_requires_gate(tmp_path):
    """Applying improvement should require gate approval."""
    ep_path = str(tmp_path / "episodes")
    imp_path = str(tmp_path / "improvements")

    episodic = EpisodicMemory(ep_path)
    improver = SelfImprover(episodic, imp_path)

    proposal = ImprovementProposal(
        proposal_id="test_proposal",
        target="config",
        description="Test improvement",
        rationale="Test rationale",
        changes=[{"type": "increase_timeout", "action": "TEST", "current": 30, "proposed": 60}],
        expected_impact="Reduce failures",
        risk_level="low",
        confidence=0.8,
    )

    # Without gate approval
    result = improver.apply_improvement(proposal, gate_approved=False)
    assert result["success"] is False
    assert "Gate approval required" in result["error"]

    # With gate approval
    result = improver.apply_improvement(proposal, gate_approved=True)
    assert result["success"] is True
    assert len(result["applied"]) > 0


def test_high_risk_improvements_blocked(tmp_path):
    """High-risk improvements should be blocked even with gate approval."""
    ep_path = str(tmp_path / "episodes")
    imp_path = str(tmp_path / "improvements")

    episodic = EpisodicMemory(ep_path)
    improver = SelfImprover(episodic, imp_path)

    proposal = ImprovementProposal(
        proposal_id="high_risk",
        target="code",
        description="High risk change",
        rationale="Risky",
        changes=[{"type": "modify_gate", "action": "REMOVE_SAFETY"}],
        expected_impact="Unknown",
        risk_level="high",
        confidence=0.5,
    )

    result = improver.apply_improvement(proposal, gate_approved=True)
    assert result["success"] is False
    assert "human review" in result["error"].lower()


def test_improvement_stats_tracking(tmp_path):
    """Should track improvement statistics."""
    ep_path = str(tmp_path / "episodes")
    imp_path = str(tmp_path / "improvements")

    episodic = EpisodicMemory(ep_path)
    for i in range(3):
        episodic.store(Episode(
            episode_id=f"ep{i}",
            timestamp=f"2026-02-03T12:0{i}:00",
            goal="Test",
            actions=[{"action": "TEST", "success": False, "error": "Error"}],
            outcome="failure",
            reward=0.0,
        ))

    improver = SelfImprover(episodic, imp_path)
    improver.analyze_failures(min_failures=2)

    stats = improver.get_improvement_stats()
    assert "analyses_performed" in stats
    assert stats["analyses_performed"] >= 1
