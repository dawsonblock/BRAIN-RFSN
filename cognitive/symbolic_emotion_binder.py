"""
Symbolic Emotion Binder.
Translates semantic content into emotional valence and symbolic representations.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Symbol:
    glyph: str
    meaning: str

@dataclass
class EmotionProfile:
    fear: float
    curiosity: float
    confidence: float
    frustration: float = 0.0
    bonding: float = 0.0
    
    def to_dict(self):
        return {
            "fear": self.fear, 
            "curiosity": self.curiosity, 
            "confidence": self.confidence,
            "frustration": self.frustration,
            "bonding": self.bonding
        }

class SymbolicEmotionBinder:
    def profile_emotion(self, text: str) -> EmotionProfile:
        """
        Heuristic analysis of text to determine emotional response.
        """
        text_lower = text.lower()
        
        # Risk detection
        fear = 0.1
        if any(w in text_lower for w in ["critical", "failure", "security", "breach", "fatal", "attack"]):
            fear = 0.8
            
        # Novelty/Interest detection (Bonding)
        bonding = 0.2
        if any(w in text_lower for w in ["sync", "identity", "remember", "past", "history", "together"]):
            bonding = 0.7
            
        # Novelty detection
        curiosity = 0.3
        if any(w in text_lower for w in ["explore", "new", "unknown", "hypothesis", "research", "potential"]):
            curiosity = 0.9

        # Frustration detection (Repetitive structure or negative qualifiers)
        frustration = 0.1
        if any(w in text_lower for w in ["again", "still", "not working", "stuck", "retry", "loop"]):
            frustration = 0.6
            
        return EmotionProfile(
            fear=fear, 
            curiosity=curiosity, 
            confidence=0.5, 
            frustration=frustration, 
            bonding=bonding
        )

    def compress_narrative(self, text: str, max_symbols: int = 3) -> List[Symbol]:
        """Compresses complex text into abstract symbols for the Mirror Kernel."""
        # Simple placeholder logic
        symbols = []
        if "security" in text.lower():
            symbols.append(Symbol("🛡️", "defense"))
        if "bug" in text.lower():
            symbols.append(Symbol("🐞", "correction"))
        if not symbols:
            symbols.append(Symbol("⚙️", "processing"))
        return symbols

    def get_symbol_statistics(self) -> Dict:
        return {"vocabulary_size": 128} # Placeholder

_binder = None
def get_symbolic_binder():
    global _binder
    if _binder is None:
        _binder = SymbolicEmotionBinder()
    return _binder


