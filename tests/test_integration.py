"""
Integration tests for RFSN components.
"""
from consciousness.neuro_modulator import NeuroModulator, BrainState
from consciousness.dream_reality_sync import get_dream_sync_clock


def test_neuro_modulation_panic():
    """Test that high cortisol triggers PANIC mode."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.9, dopamine=0.5, acetylcholine=0.5)
    
    assert isinstance(state, BrainState)
    assert state.mode == "PANIC"
    assert state.temperature == 0.0
    assert state.gate_strictness == 1.0


def test_neuro_modulation_flow():
    """Test that high dopamine and acetylcholine trigger FLOW mode."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.1, dopamine=0.8, acetylcholine=0.8)
    
    assert isinstance(state, BrainState)
    assert state.mode == "FLOW"
    assert state.temperature > 0.5


def test_neuro_modulation_focused():
    """Test FOCUSED mode with moderate chemicals."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.2, dopamine=0.3, acetylcholine=0.7)
    
    assert isinstance(state, BrainState)
    assert state.mode == "FOCUSED"


def test_neuro_modulation_confusion():
    """Test CONFUSION mode with low acetylcholine."""
    modulator = NeuroModulator()
    state = modulator.regulate_state(cortisol=0.3, dopamine=0.4, acetylcholine=0.3)
    
    assert isinstance(state, BrainState)
    assert state.mode == "CONFUSION"
    assert state.search_depth == 20  # Frantic searching


def test_neuro_modulation_reset():
    """Test that reset returns to baseline."""
    modulator = NeuroModulator()
    
    # First, enter PANIC mode
    modulator.regulate_state(cortisol=0.9, dopamine=0.0, acetylcholine=0.5)
    
    # Then reset
    modulator.reset_baseline()
    
    assert modulator.current_state.mode == "FOCUSED"
    assert modulator.current_state.temperature == 0.2


def test_dream_cycle_trigger():
    """Test that the dream cycle is triggered when battery is low."""
    dream_sync = get_dream_sync_clock()
    dream_sync.wakefulness_battery = 10.0
    
    assert dream_sync.should_sleep() is True


def test_dream_cycle_no_trigger():
    """Test that the dream cycle is not triggered when battery is high."""
    dream_sync = get_dream_sync_clock()
    dream_sync.wakefulness_battery = 80.0
    
    assert dream_sync.should_sleep() is False


def test_dream_cycle_battery_drain():
    """Test that activity drains the battery."""
    dream_sync = get_dream_sync_clock()
    initial_battery = dream_sync.wakefulness_battery
    
    dream_sync.mark_activity(effort_level=1.0)
    
    assert dream_sync.wakefulness_battery < initial_battery


def test_dream_cycle_panic_drain():
    """Test that panic mode drains battery faster."""
    dream_sync = get_dream_sync_clock()
    initial_battery = dream_sync.wakefulness_battery
    
    dream_sync.mark_activity(effort_level=3.0)  # Panic mode
    
    drain = initial_battery - dream_sync.wakefulness_battery
    assert drain > 10.0  # Should drain significantly


def test_chemical_to_behavior_pipeline():
    """Test the full pipeline from chemicals to behavior."""
    modulator = NeuroModulator()
    
    # Simulate high-risk scenario
    cortisol = 0.9
    dopamine = 0.2
    acetylcholine = 0.6
    
    state = modulator.regulate_state(cortisol, dopamine, acetylcholine)
    
    # Should be in PANIC mode with zero creativity
    assert state.mode == "PANIC"
    assert state.temperature == 0.0
    
    # This state would lock down the sandbox
    assert state.gate_strictness == 1.0
