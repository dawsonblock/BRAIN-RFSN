# tests/test_episodic_memory.py
"""Tests for episodic memory and consolidation."""
from __future__ import annotations


from cognitive.episodic_memory import Episode, EpisodicMemory, EpisodeQuery
from cognitive.memory_consolidation import MemoryConsolidator


def test_episodic_memory_store_and_retrieve(tmp_path):
    """Store and retrieve episodes."""
    store_path = str(tmp_path / "episodes")
    memory = EpisodicMemory(store_path)

    episode = Episode(
        episode_id="ep1",
        timestamp="2026-02-03T12:00:00",
        goal="Fix failing tests",
        actions=[
            {"step_id": 1, "action": "RUN_TESTS", "success": True},
            {"step_id": 2, "action": "APPLY_PATCH", "success": True},
        ],
        outcome="success",
        reward=1.0,
        lessons=["Run tests first to identify failures"],
    )

    memory.store(episode)

    # Retrieve
    results = memory.retrieve(EpisodeQuery(outcome="success"), k=5)
    assert len(results) == 1
    assert results[0].episode_id == "ep1"
    assert results[0].goal == "Fix failing tests"


def test_episodic_memory_filters_by_outcome(tmp_path):
    """Filter episodes by outcome."""
    store_path = str(tmp_path / "episodes")
    memory = EpisodicMemory(store_path)

    memory.store(Episode(
        episode_id="ep1", timestamp="2026-02-03T12:00:00",
        goal="Goal 1", actions=[], outcome="success", reward=1.0,
    ))
    memory.store(Episode(
        episode_id="ep2", timestamp="2026-02-03T12:01:00",
        goal="Goal 2", actions=[], outcome="failure", reward=0.0,
    ))

    successes = memory.retrieve(EpisodeQuery(outcome="success"), k=5)
    assert len(successes) == 1
    assert successes[0].outcome == "success"

    failures = memory.retrieve(EpisodeQuery(outcome="failure"), k=5)
    assert len(failures) == 1
    assert failures[0].outcome == "failure"


def test_episodic_memory_stats(tmp_path):
    """Track memory statistics."""
    store_path = str(tmp_path / "episodes")
    memory = EpisodicMemory(store_path)

    memory.store(Episode(
        episode_id="ep1", timestamp="t", goal="g", actions=[], outcome="success", reward=1.0,
    ))
    memory.store(Episode(
        episode_id="ep2", timestamp="t", goal="g", actions=[], outcome="failure", reward=0.0,
    ))

    stats = memory.get_stats()
    assert stats["total"] == 2
    assert stats["successes"] == 1
    assert stats["failures"] == 1


def test_memory_consolidation_extracts_patterns(tmp_path):
    """Consolidation extracts patterns from episodes."""
    ep_path = str(tmp_path / "episodes")
    sem_path = str(tmp_path / "semantic")

    episodic = EpisodicMemory(ep_path)

    # Store multiple similar successful episodes
    for i in range(3):
        episodic.store(Episode(
            episode_id=f"ep{i}",
            timestamp=f"2026-02-03T12:0{i}:00",
            goal=f"Fix test {i}",
            actions=[
                {"action": "RUN_TESTS", "success": True},
                {"action": "APPLY_PATCH", "success": True},
            ],
            outcome="success",
            reward=1.0,
            lessons=["Always run tests first"],
        ))

    consolidator = MemoryConsolidator(episodic, sem_path)
    knowledge = consolidator.consolidate(min_episodes=2)

    assert len(knowledge) >= 1
    # Should find the RUN_TESTS -> APPLY_PATCH pattern
    topics = [k.topic for k in knowledge]
    assert any("successful_sequence" in t or "lessons" in t for t in topics)


def test_memory_consolidation_query(tmp_path):
    """Query consolidated knowledge."""
    ep_path = str(tmp_path / "episodes")
    sem_path = str(tmp_path / "semantic")

    episodic = EpisodicMemory(ep_path)
    for i in range(3):
        episodic.store(Episode(
            episode_id=f"ep{i}",
            timestamp=f"2026-02-03T12:0{i}:00",
            goal="Test goal",
            actions=[{"action": "WEB_SEARCH", "success": True}],
            outcome="success",
            reward=0.9,
        ))

    consolidator = MemoryConsolidator(episodic, sem_path)
    consolidator.consolidate(min_episodes=2)

    results = consolidator.query_knowledge("successful", k=3)
    # Should find something
    assert isinstance(results, list)
