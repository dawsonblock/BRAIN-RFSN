"""
Recursive Identity Feedback.
Manages the agent's internal monologue and self-review process.
"""
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class ThoughtRecord:
    thought_id: str
    content: str
    timestamp: float
    context: Dict
    decision: str

@dataclass
class SelfReview:
    thought_id: str
    quality_score: float
    lessons_learned: List[str]
    bias_delta: float = 0.0 # Correction for future temperatures/strictness

class RecursiveIdentityFeedback:
    def __init__(self):
        self.thought_history: List[ThoughtRecord] = []
        self.reviews: List[SelfReview] = []

    def get_self_model(self) -> Dict[str, Any]:
        """Returns the dynamic self-image."""
        return {
            "growth_areas": ["security_awareness", "code_efficiency", "metacognition"],
            "biases_identified": ["tendency_to_overoptimize", "analytical_paralysis"],
            "thought_count": len(self.thought_history)
        }

    def capture_thought(self, thought_content: str, context: Dict, decision_made: str, reasoning: str) -> ThoughtRecord:
        record = ThoughtRecord(
            thought_id=f"t_{len(self.thought_history)}",
            content=thought_content,
            timestamp=time.time(),
            context=context,
            decision=decision_made
        )
        self.thought_history.append(record)
        return record

    def self_review(self, thought: ThoughtRecord) -> SelfReview:
        """Simulates a metacognitive review of a past thought."""
        quality = 0.8
        lessons = []
        bias_delta = 0.0
        
        if "error" in str(thought.context).lower():
            quality = 0.4
            lessons.append("Analyze error source more deeply")
            bias_delta = 0.1 # Increase strictness next time
        
        if len(thought.content) > 500:
            lessons.append("Thought was too verbose, risk of confusion")
            bias_delta -= 0.05 # Lower temperature slightly to focus
        
        review = SelfReview(
            thought_id=thought.thought_id, 
            quality_score=quality, 
            lessons_learned=lessons,
            bias_delta=bias_delta
        )
        self.reviews.append(review)
        return review

    def apply_review_to_state(self) -> Dict[str, float]:
        """Calculates global cognitive offsets based on recent self-reviews."""
        if not self.reviews:
            return {"temp_offset": 0.0, "strictness_offset": 0.0}
        
        # Take the aggregate of recent bias deltas
        recent = self.reviews[-5:]
        avg_delta = sum(r.bias_delta for r in recent) / len(recent)
        
        return {
            "temp_offset": -avg_delta * 0.5,
            "strictness_offset": avg_delta
        }

    def get_meta_statistics(self) -> Dict[str, Any]:
        return {
            "total_thoughts": len(self.thought_history),
            "total_reviews_conducted": len(self.reviews),
            "average_quality": sum(r.quality_score for r in self.reviews) / len(self.reviews) if self.reviews else 1.0
        }

    def reset(self) -> None:
        """Clears thought history and reviews."""
        self.thought_history = []
        self.reviews = []
        logger.info("🧠 RecursiveIdentityFeedback reset.")

_feedback = None
def get_identity_feedback():
    global _feedback
    if _feedback is None:
        _feedback = RecursiveIdentityFeedback()
    return _feedback


