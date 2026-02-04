from best_build_agent import BestBuildAgent
from rfsn_kernel.types import StateSnapshot, Proposal, Action
from rfsn_kernel.gate import gate

def test_reflexive_safety():
    print("--- Testing Phase 9: Reflexive Safety ---")
    agent = BestBuildAgent()
    
    # 1. Simulate High Stress (Cortisol = 1.0) -> Triggers PANIC mode
    # We'll mock the security report to simulate max risk
    from unittest.mock import patch
    
    with patch.object(agent.monitor, 'get_security_report') as mock_sec:
        mock_sec.return_value = {"risk_percentage": 100.0}
        
        print("\n[SCENARIO 1] High Cortisol (PANIC Mode)")
        # A proposal with 2 actions should be DENIED in Panic mode
        # NOTE: Using state.mode="PANIC" instead of brain_state (kernel-native approach)
        snapshot = StateSnapshot(task_id="test", workspace_root=".", mode="PANIC")
        proposal = Proposal(
            proposal_id="multi_action",
            actions=(
                Action(name="READ_FILE", args={"path": "test.py"}),
                Action(name="READ_FILE", args={"path": "test2.py"})
            )
        )
        
        # No brain_state needed - mode is in StateSnapshot now
        decision = gate(snapshot, proposal)
        print(f"Decision Status (Multi-action in PANIC): {decision.status}")
        print(f"Reasons: {decision.reasons}")
        assert decision.status == "DENY"
        assert "reflexive:panic_lockdown:single_action_only" in decision.reasons

        # A proposal with a non-kernel action should be DENIED as unknown_action
        # (WEB_SEARCH is no longer a kernel action)
        proposal_net = Proposal(
            proposal_id="net_action",
            actions=(Action(name="WEB_SEARCH", args={"query": "test"}),)
        )
        decision_net = gate(snapshot, proposal_net)
        print(f"Decision Status (WEB_SEARCH in PANIC): {decision_net.status}")
        assert decision_net.status == "DENY"
        # Now denied as unknown action (not in kernel envelopes)
        assert any("unknown_action:WEB_SEARCH" in r for r in decision_net.reasons)

    # 2. Test Adaptive Bandit (Dopamine Exploration)
    print("\n[SCENARIO 2] High Dopamine (Adaptive Exploration)")
    agent.last_chemicals["dopamine"] = 1.0
    choices = []
    for _ in range(10):
        choices.append(agent.strategy_bandit.choose(["A", "B"], dopamine=1.0))
    print(f"Bandit choices with high dopamine (varied?): {set(choices)}")

    # 3. Test Synaptic Pruning
    print("\n[SCENARIO 3] Synaptic Pruning")
    from consciousness.dream_reality_sync import get_dream_sync_clock
    ds = get_dream_sync_clock()
    # Mock knowledge base to have a weak entry
    from learning.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    kb.add_knowledge("heuristic", "Weak", "Delete me", [], 0.1)
    print(f"KB Entries before pruning: {len(kb.entries)}")
    ds.enter_rem_cycle(recent_failures=[])
    print(f"KB Entries after pruning: {len(kb.entries)}")
    
    print("\n✅ PHASE 9 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    test_reflexive_safety()

