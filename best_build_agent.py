"""Best Build Agent - The Fully Integrated Digital Organism.

Integrates RFSN Cognitive Architecture:
1. Cortex (Reasoning/LLM)
2. Amygdala (Behavioral Monitor)
3. Striatum (Proactive Engine)
4. Neuro-Modulation (Chemicals)
5. Dream Cycle (Offline Processing)
"""

from __future__ import annotations

import os
import time
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Security Layer (Amygdala)
from security.advanced_sandbox import get_sandbox
from security.behavioral_monitor import get_monitor
from security.prompt_injection_shield import PromptInjectionShield

# Cognitive Layer (Cortex + Striatum)
from cognitive.reasoning_engine import get_reasoning_engine
from cognitive.capsule_memory_core import get_memory_core
from cognitive.recursive_identity_feedback import get_identity_feedback
from cognitive.symbolic_emotion_binder import get_symbolic_binder
from cognitive.proactive_output_engine import get_proactive_engine

# Consciousness Layer (Neuro-chem + Dreams)
from consciousness.mirror_identity_kernel import get_mirror_kernel
from consciousness.dream_reality_sync import get_dream_sync_clock
from consciousness.neuro_modulator import NeuroModulator

# Learning Layer
from learning.knowledge_base import get_knowledge_base
from memory.vector_store import get_vector_memory
from cognitive.hierarchical_planner import get_hierarchical_planner
from cognitive.task_graph import TaskStatus

from cognitive.episodic_memory import get_episodic_memory, Episode
from cognitive.self_improvement import SelfImprover

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Current state of the agent."""
    active_task: Optional[str] = None
    current_context: Dict[str, Any] = field(default_factory=dict)
    consciousness_level: float = 0.5
    entropy_level: float = 0.0
    mode: str = "FOCUSED"
    temperature: float = 0.2
    budget_remaining: int = 100 # Added budget_remaining

class BestBuildAgent:
    """
    The Unified RFSN Agent.
    Operates on a biological 'Sense -> Modulate -> Act -> Sleep' cycle.
    """
    
    def __init__(self, enable_consciousness: bool = True):
        # 1. Initialize Subsystems
        self.sandbox = get_sandbox()
        self.monitor = get_monitor()
        self.reasoning_engine = get_reasoning_engine()
        self.memory_core = get_memory_core()
        self.vector_memory = get_vector_memory()
        self.identity_feedback = get_identity_feedback()
        self.symbolic_binder = get_symbolic_binder()
        self.proactive_engine = get_proactive_engine()
        self.knowledge_base = get_knowledge_base()
        self.planner = get_hierarchical_planner()
        
        # 2. Initialize Consciousness Layers
        self.mirror_kernel = get_mirror_kernel()
        self.dream_sync = get_dream_sync_clock()
        self.neuro_modulator = NeuroModulator()
        self.injection_shield = PromptInjectionShield()
        self.episodic_memory = get_episodic_memory()
        self.improver = SelfImprover(self.episodic_memory, "rfsn_memory_store/improvements")
        
        # 3. State Buffers
        self.state = AgentState(current_context={})
        self.recent_failures: List[Dict[str, Any]] = []
        self.security_incidents: List[Dict[str, Any]] = []
        
        # Initialize strategy bandit
        from upstream_learner.bandit import ThompsonBandit
        self.strategy_bandit = ThompsonBandit()
        self.last_strategy: Optional[str] = None
        self.last_snapshot: Optional[Any] = None
        self.last_chemicals: Dict[str, float] = {}
        
        logger.info("⚡ RFSN 'Digital Organism' Initialized.")
    
    def process_task(
        self,
        task_description: str,
        code_files: Optional[Dict[str, str]] = None,
        test_outputs: Optional[List[str]] = None,
        depth: int = 0
    ) -> Dict[str, Any]:
        """
        Process a task with full neuro-cognitive modulation.
        """
        logger.info(f"Processing task: {task_description[:100]}...")
        
        # --- PHASE 0: PRE-SENSE SECURITY ---
        is_blocked, risk_score, reason = self.injection_shield.analyze_prompt(task_description)
        if is_blocked:
            logger.error(f"🛡️ SECURITY ALERT: Prompt Injection Attempt! {reason}")
            # Increase cortisol for next pulse (if applicable) or trigger immediate stress
            # Note: We don't have a direct chemical set here that persists easily without mutate_chemicals,
            # but we can simulate the impact for the next run if we had a persistent state.
            return {
                "error": "Security Restriction: Adversarial prompt detected.",
                "risk_reason": reason,
                "neuro_state": "BLOCK"
            }

        # --- PHASE 1: SENSE & MODULATE ---
        
        # Parallel Sensing: Launch concurrent checks to save time
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_security = executor.submit(self.monitor.get_security_report)
            future_dopamine = executor.submit(self.proactive_engine.scan_for_entropy)
            future_kb = executor.submit(self.knowledge_base.get_statistics)
            
            # Wait for results
            security_report = future_security.result()
            current_dopamine = future_dopamine.result()
            kb_stats = future_kb.result()

        # Cortisol = Risk level (Amygdala)
        current_cortisol = security_report.get("risk_percentage", 0) / 100.0
        
        # Acetylcholine = Success Rate (Knowledge Base)
        current_acetylcholine = kb_stats["recent_success_rate"] 

        # Serotonin = "Stability" (absence of recent trauma/failures)
        serotonin = max(0.0, 1.0 - (len(self.recent_failures) * 0.2))
        
        # Oxytocin = "Bonding" (relevance of retrieved memories/past identity)
        # Placeholder for memory relevance average
        oxytocin = 0.6 

        # 2. Update Neuro-Modulation (Chemical state)
        identity_offsets = self.identity_feedback.apply_review_to_state()
        brain_state = self.neuro_modulator.regulate_state(
            cortisol=current_cortisol, 
            dopamine=current_dopamine, 
            acetylcholine=current_acetylcholine,
            serotonin=serotonin,
            oxytocin=oxytocin,
            identity_offsets=identity_offsets
        )
        
        # 2.5 Knowledge Injection (Upstream Intelligence)
        self.state.current_context["kb_success_rate"] = kb_stats["recent_success_rate"]
        self.state.current_context["survival_rules"] = kb_stats["survival_rules"]

        # Fetch Core Beliefs for context injection
        from memory.core_beliefs import get_core_belief_store
        core_beliefs = get_core_belief_store().get_active_beliefs()[:3]
        self.state.current_context["core_beliefs"] = core_beliefs
        
        # Store for UI display
        self.last_chemicals = {
            "cortisol": current_cortisol,
            "dopamine": current_dopamine,
            "acetylcholine": current_acetylcholine,
            "serotonin": serotonin,
            "oxytocin": oxytocin
        }
        
        # 3. Apply Metacognitive Offsets (Self-Review feedback)
        review_offsets = self.identity_feedback.apply_review_to_state()
        brain_state.temperature += review_offsets.get("temp_offset", 0.0)
        brain_state.gate_strictness += review_offsets.get("strictness_offset", 0.0)

        # Re-clamp after offsets
        brain_state.temperature = max(0.0, min(1.0, brain_state.temperature))
        brain_state.gate_strictness = max(0.0, min(1.0, brain_state.gate_strictness))
        
        from rfsn_kernel.types import StateSnapshot, Action, Proposal
        from rfsn_kernel.gate import gate
        
        # 3. PLAN & ACT (Cognitive Phase)
        # Choose a strategy using the Thompson Bandit (Adaptive Exploration)
        dopamine = self.last_chemicals.get("dopamine", 0.5)
        self.last_strategy = self.strategy_bandit.choose(["Standard", "Aggressive", "Cautious"], dopamine=dopamine)
        
        # Prepare Kernel Decision Inputs (Force lockdown if in PANIC)
        snapshot = StateSnapshot(
            task_id=f"task_{int(time.time())}",
            workspace_root=os.getcwd(),
            budget_actions_remaining=self.state.budget_remaining,
            notes={"mode": brain_state.mode}
        )
        self.last_snapshot = snapshot # Store for later terminal checks if needed
        
        # Verify State via Kernel (Reflexive Safety Check)
        # We use a dummy proposal just to see if the kernel allows operations in this mode
        dummy_proposal = Proposal(proposal_id="health_check", actions=(Action(name="READ_FILE", args={"path": "os.py"}),))
        decision = gate(snapshot, dummy_proposal, brain_state=brain_state)
        
        if decision.status == "DENY":
            logger.error(f"🛑 KERNEL LOCKDOWN: {decision.reasons}")
            return {
                "error": "Kernel Restriction: System in Lockdown.",
                "reasons": decision.reasons,
                "neuro_state": brain_state.mode
            }

        # 3. Modulate Sandbox (The "Fear" Response)
        if brain_state.mode == "PANIC":
             logger.warning("⚠️ CORTISOL SPIKE: Locking down sandbox configuration.")
             self.sandbox.config.network_enabled = False 
             # Could assume stricter timeouts or syscalls here
        
        # --- PHASE 2: COGNITION & ACTION ---
        
        # 3.2 Emotion Profiling (Amygdala/Symbolic Binder)
        # Profile the task before processing to prime the state
        emotion_profile = self.symbolic_binder.profile_emotion(task_description)

        # 3.3 Retrieve Past Memories (Cortex/Hippocampus)
        # Prioritize high emotional intensity in the future, for now standard recall
        memories = self.episodic_memory.get_lessons_for_goal(task_description)
        logger.info(f"💾 RECALLED {len(memories)} past lessons. Emotion: {emotion_profile.to_dict()}")

        # 3.5 Hierarchical Planning (Prefrontal Cortex)
        is_complex = depth == 0 and (len(task_description.split()) > 10 or "plan" in task_description.lower())
        
        if is_complex and self.planner:
            logger.info("🧠 ACTIVATING PREFRONTAL CORTEX: Decomposing complex task...")
            plan = self.planner.create_plan(task_description, context=self.state.current_context)
            if plan:
                return self._execute_plan(plan)

        # 4. Reason (with chemical temperature and recalled memories)
        # Model Escalation: If cortisol is high or dopamine is low (panic/confusion), escalate to R1
        # Also escalate if the previous attempt failed.
        use_reasoner = (brain_state.mode in ["PANIC", "CONFUSION"]) or (depth > 0)
        model_to_use = "deepseek-reasoner" if use_reasoner else "deepseek-chat"
        
        logger.info(f"🧠 MODEL ESCALATION: Using {model_to_use} for depth {depth} (Mode: {brain_state.mode})")
        
        context = self.reasoning_engine.build_context(
            problem_statement=task_description,
            code_files=code_files,
            test_outputs=test_outputs,
            past_memories=memories
        )
        
        # We need a way to pass the model to the reasoning engine.
        # Assuming we can pass it via temperature or a new arg. 
        # For now, let's assume reason() can take a model_id or we'll just use the temperature as a proxy 
        # if the engine doesn't support model_id yet.
        # But wait, let's check reasoning_engine.py
        
        reasoning_result = self.reasoning_engine.reason(
            context, 
            temperature=brain_state.temperature,
            model=model_to_use
        )
        
        # --- PHASE 2.8: UPSTREAM UPDATE (Learning) ---
        # Calculate Reward Multiplier (Metabolic/Stress Weighting)
        # High Cortisol + Success = High Multiplier (Crucial Survival Strategy)
        reward_multiplier = 1.0 + (current_cortisol * 2.0)
        
        # Placeholder: In a real run, the reward comes later, but we can set 
        # a 'metabolic importance' flag for when the bandit is updated.
        self.state.current_context["reward_multiplier"] = reward_multiplier
        
        # 4.5 Adaptive Self-Correction Loop (Neuro-Recursive Feedback)
        # Instead of hardcoded depth < 2, we use patience (0.0-1.0) * some max depth
        max_patience_depth = int(brain_state.patience * 4) # Up to 4 retries at max patience
        if test_outputs and reasoning_result.confidence < 0.7 and depth < max_patience_depth:
             logger.warning(f"🔄 NEURO-FEEDBACK: Confidence {reasoning_result.confidence:.2f} too low. Retrying (Depth {depth}/{max_patience_depth})...")
             correction_task = f"Fix the errors found in the previous attempt: {test_outputs[0][:100]}"
             correction_res = self.process_task(correction_task, code_files=code_files, test_outputs=test_outputs, depth=depth + 1)
             return correction_res

        # 5. Proactive Thought Generation
        proactive_thought = None
        if brain_state.mode == "FLOW":
            proactive_thought = self.proactive_engine.generate_proactive_thought()

        # 6. Memory & Identity Formation
        episode_id = hashlib.sha256(f"{task_description}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        episode = Episode(
            episode_id=episode_id,
            timestamp=datetime.utcnow().isoformat(),
            goal=task_description,
            actions=[{"action": "reason", "success": reasoning_result.confidence > 0.5}],
            outcome="success" if reasoning_result.confidence > 0.7 else "partial",
            reward=reasoning_result.confidence,
            lessons=[reasoning_result.understanding],
            emotion_profile=emotion_profile.to_dict()
        )
        self.episodic_memory.store(episode)
        
        self.memory_core.create_capsule(
            content=f"Task: {task_description}",
            context={"reasoning": reasoning_result.understanding, "mode": brain_state.mode},
            emotion_profile=emotion_profile.to_dict(),
            tags=["task", "processing", brain_state.mode],
            self_relevance=0.7
        )

        # 7. Self-Review (Metacognition)
        thought = self.identity_feedback.capture_thought(
            thought_content=reasoning_result.suggested_approach,
            context={"mode": brain_state.mode, "confidence": reasoning_result.confidence},
            decision_made="approach_proposed",
            reasoning=reasoning_result.understanding
        )
        if brain_state.mode in ["FOCUSED", "FLOW"]:
            self.identity_feedback.self_review(thought)
        
        # --- PHASE 3: METABOLISM (SLEEP) ---
        
        # 7. Drain Energy
        effort = 3.0 if brain_state.mode == "PANIC" else 1.0
        self.dream_sync.mark_activity(effort_level=effort)
        
        # 8. Check Circadian Rhythm
        sleep_report = None
        if self.dream_sync.should_sleep():
            # Trigger Sleep Cycle
            sleep_report = self.dream_sync.enter_rem_cycle(
                self.recent_failures, 
                self.security_incidents
            )
            
            # Reset buffers
            self.recent_failures = []
            self.security_incidents = []
            self.neuro_modulator.reset_baseline()
            
        return {
            "result": reasoning_result.suggested_approach,
            "confidence": reasoning_result.confidence,
            "neuro_state": brain_state.mode,
            "temperature_used": brain_state.temperature,
            "proactive_thought": proactive_thought.content if proactive_thought else None,
            "sleep_report": sleep_report,
            "consciousness_level": self.state.consciousness_level,
            "memories_recalled": len(memories),
            "emotions": emotion_profile.to_dict(),
            "patience": brain_state.patience
        }
    
    def _execute_plan(self, plan) -> Dict[str, Any]:
        """Execute a hierarchical plan."""
        results = []
        max_steps = 20
        step_count = 0
        
        logger.info(f"🚀 Executing Plan with {len(plan.graph.nodes)} steps.")
        
        while not plan.is_complete() and step_count < max_steps:
            ready_tasks = plan.get_ready_tasks()
            
            if not ready_tasks:
                if not plan.is_complete():
                    logger.warning("⚠️ PLAN BLOCKED: No ready tasks but plan incomplete.")
                    return {"result": "Plan Blocked", "status": "FAILED", "neuro_state": "CONFUSION"}
                break
                
            for task in ready_tasks:
                plan.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                
                # Execute sub-task (recurse with depth=1)
                logger.info(f"▶️ Sub-Task [{task.id}]: {task.description}")
                try:
                    res = self.process_task(task.description, depth=1)
                    
                    status = TaskStatus.COMPLETED
                    if "error" in res:
                        status = TaskStatus.FAILED
                        logger.error(f"❌ Sub-Task Failed: {res['error']}")
                        
                    plan.update_task_status(task.id, status, result=str(res.get("result", "")))
                    results.append({"id": task.id, "result": res})
                    
                except Exception as e:
                    logger.error(f"❌ Sub-Task Exception: {e}")
                    plan.update_task_status(task.id, TaskStatus.FAILED, result=str(e))
            
            step_count += 1
            
        return {
            "result": "Hierarchical Plan Executed",
            "steps_completed": len(results),
            "plan_status": "COMPLETED" if plan.is_complete() else "INCOMPLETE",
            "neuro_state": "FLOW",
            "details": results
        }

    def execute_with_security(self, command: List[str], workspace_path: str) -> Dict[str, Any]:
        """Execute with security monitoring and chemical feedback."""
        
        # 1. Execute
        result = self.monitor.record_event("command_exec", {"command": " ".join(command)})
        
        # 2. Check for Trauma
        if result.risk_score > 0.8:
            self.security_incidents.append({
                "event_type": "command_exec",
                "risk_score": result.risk_score,
                "details": {"command": command},
                "is_anomalous": True
            })
            
        # 3. Run in Sandbox
        # (Simplified pass-through to existing sandbox logic)
        sandbox_res = self.sandbox.execute(
             self.sandbox.create_sandbox(workspace_path), 
             command
        )
        
        # 4. Track Failures for Dreaming
        if not sandbox_res.exit_code == 0:
            self.recent_failures.append({
                "task_description": f"Command: {command}",
                "error": sandbox_res.stderr
            })
            
        return {"success": sandbox_res.exit_code == 0, "output": sandbox_res.stdout}

# Singleton instance
_best_build_agent: Optional[BestBuildAgent] = None

def get_best_build_agent() -> BestBuildAgent:
    global _best_build_agent
    if _best_build_agent is None:
        _best_build_agent = BestBuildAgent()
    return _best_build_agent


