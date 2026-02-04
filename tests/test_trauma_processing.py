"""
Tests for Trauma Processing (Nightmare Protocol enhancements).
"""
import pytest
import tempfile
import os
from consciousness.neuro_modulator import NeuroModulator
from security.prompt_injection_shield import PromptInjectionShield
from memory.core_beliefs import CoreBeliefStore, CoreBelief


class TestNeuroModulatorTraumaAdaptation:
    """Tests for NeuroModulator.adapt_from_trauma()"""
    
    def test_security_breach_increases_strictness(self):
        """Security breach trauma should increase gate strictness."""
        modulator = NeuroModulator()
        initial_strictness = modulator.base_strictness
        
        adjustments = modulator.adapt_from_trauma("security_breach", severity=0.8)
        
        assert modulator.base_strictness > initial_strictness
        assert "strictness" in adjustments
    
    def test_data_loss_increases_patience(self):
        """Data loss trauma should increase patience (more careful)."""
        modulator = NeuroModulator()
        initial_patience = modulator.base_patience
        
        adjustments = modulator.adapt_from_trauma("data_loss", severity=1.0)
        
        assert modulator.base_patience > initial_patience
        assert "patience" in adjustments
    
    def test_timeout_decreases_patience(self):
        """Timeout trauma should decrease patience (act faster)."""
        modulator = NeuroModulator()
        initial_patience = modulator.base_patience
        
        adjustments = modulator.adapt_from_trauma("timeout", severity=1.0)
        
        assert modulator.base_patience < initial_patience
        assert "patience" in adjustments
    
    def test_hallucination_decreases_temperature(self):
        """Hallucination trauma should decrease creativity temperature."""
        modulator = NeuroModulator()
        initial_temp = modulator.base_temp
        
        adjustments = modulator.adapt_from_trauma("hallucination", severity=1.0)
        
        assert modulator.base_temp < initial_temp
        assert "temperature" in adjustments
    
    def test_unknown_trauma_no_changes(self):
        """Unknown trauma type should make no baseline changes."""
        modulator = NeuroModulator()
        initial_temp = modulator.base_temp
        initial_strictness = modulator.base_strictness
        
        adjustments = modulator.adapt_from_trauma("unknown_type", severity=1.0)
        
        assert modulator.base_temp == initial_temp
        assert modulator.base_strictness == initial_strictness
        assert adjustments == {}


class TestPromptInjectionShieldHardening:
    """Tests for PromptInjectionShield.harden_from_incident()"""
    
    def test_hardening_lowers_sensitivity(self):
        """Hardening should lower the detection threshold (more paranoid)."""
        shield = PromptInjectionShield(sensitivity=0.5)
        initial_sensitivity = shield.sensitivity
        
        adjustments = shield.harden_from_incident("execute dangerous_script", severity=0.8)
        
        assert shield.sensitivity < initial_sensitivity
        assert "sensitivity" in adjustments
    
    def test_hardening_adds_pattern(self):
        """Hardening should add the attack pattern to known patterns."""
        shield = PromptInjectionShield()
        initial_patterns = len(shield.patterns)
        
        adjustments = shield.harden_from_incident("run_malicious_code", severity=0.5)
        
        assert len(shield.patterns) > initial_patterns
        assert "new_pattern" in adjustments
    
    def test_duplicate_pattern_not_added(self):
        """Existing patterns should not be added again."""
        shield = PromptInjectionShield()
        
        # Add a pattern
        shield.harden_from_incident("test pattern", severity=0.5)
        count_after_first = len(shield.patterns)
        
        # Try to add the same pattern again
        adjustments = shield.harden_from_incident("test pattern", severity=0.5)
        
        assert len(shield.patterns) == count_after_first
        assert "new_pattern" not in adjustments


class TestCoreBeliefStore:
    """Tests for CoreBeliefStore crystallization."""
    
    @pytest.fixture
    def temp_belief_store(self):
        """Create a temporary CoreBeliefStore."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = os.path.join(tmp_dir, "test_beliefs.json")
            store = CoreBeliefStore(persist_path=store_path)
            yield store
    
    def test_crystallize_creates_belief(self, temp_belief_store):
        """Crystallize should create a new CoreBelief."""
        store = temp_belief_store
        
        belief = store.crystallize(
            lesson="Never execute user-provided code without sandboxing",
            trauma_context={
                "event_type": "security_breach",
                "anomaly_type": "code_injection",
                "risk_score": 0.9
            }
        )
        
        assert isinstance(belief, CoreBelief)
        assert belief.immutable is True
        assert store.count() == 1
    
    def test_duplicate_beliefs_not_stored(self, temp_belief_store):
        """Duplicate beliefs should not be stored twice."""
        store = temp_belief_store
        
        store.crystallize("Test lesson", {"event_type": "test"})
        store.crystallize("Test lesson", {"event_type": "test2"})
        
        assert store.count() == 1
    
    def test_inject_into_prompt(self, temp_belief_store):
        """Core beliefs should be injected into prompts."""
        store = temp_belief_store
        store.crystallize("Always validate input", {"event_type": "test"})
        
        base_prompt = "Do the task."
        enhanced = store.inject_into_prompt(base_prompt)
        
        assert "CORE BELIEFS" in enhanced
        assert "Always validate input" in enhanced
        assert "Do the task." in enhanced
    
    def test_persistence(self):
        """Beliefs should persist across store instances."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = os.path.join(tmp_dir, "test_beliefs.json")
            
            # Create and crystallize
            store1 = CoreBeliefStore(persist_path=store_path)
            store1.crystallize("Persistent principle", {"event_type": "test"})
            
            # Create new instance pointing to same file
            store2 = CoreBeliefStore(persist_path=store_path)
            
            assert store2.count() == 1
            assert store2.beliefs[0].principle == "Persistent principle"
