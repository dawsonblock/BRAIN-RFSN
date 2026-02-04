"""
Tests for Extended Neuro-Chemistry and Cognitive Additions.
"""
from best_build_agent import BestBuildAgent
from consciousness.neuro_modulator import NeuroModulator

def test_extended_chemicals_presence():
    nm = NeuroModulator()
    state = nm.regulate_state(
        cortisol=0.1, 
        dopamine=0.5, 
        acetylcholine=0.8,
        serotonin=0.9,
        oxytocin=0.9
    )
    
    assert hasattr(state, "patience")
    assert hasattr(state, "cooperation")
    # High serotonin should boost patience
    assert state.patience > 0.5

def test_agent_cognitive_feedback_loop():
    agent = BestBuildAgent()
    
    # 1. Process a complex task to trigger emotion profiles
    task = "I'm still stuck on this challenging bug again." # 'critical' triggers panic
    result = agent.process_task(task)
    
    # Verify chemical influence
    assert result["neuro_state"] in ["FLOW", "FOCUSED", "CONFUSION"]
    
    # 2. Verify self-review was conducted
    stats = agent.identity_feedback.get_meta_statistics()
    assert stats["total_thoughts"] > 0
    assert stats["total_reviews_conducted"] > 0
    
    # 3. Verify offsets are being calculated
    offsets = agent.identity_feedback.apply_review_to_state()
    assert "temp_offset" in offsets
    assert "strictness_offset" in offsets

def test_frustration_detection():
    agent = BestBuildAgent()
    task = "Still not working, failed again. Stuck."
    
    # We can't easily check internal profile without mocking or returning it,
    # but we can verify it doesn't crash and influences the thought recording
    result = agent.process_task(task)
    assert "neuro_state" in result
