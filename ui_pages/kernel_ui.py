# ui_pages/kernel_ui.py
"""
Kernel Mode UI - Auditable Safety Core

Displays:
- Gate decision statistics
- Ledger hash chain view
- Policy configuration
- Replay runner
"""
from __future__ import annotations

import streamlit as st
import json
from pathlib import Path


def render_kernel_mode():
    """Render the Kernel mode dashboard."""
    
    tab_gate, tab_ledger, tab_policy = st.tabs(["🛡️ Gate Stats", "📜 Ledger View", "⚙️ Policy"])
    
    with tab_gate:
        render_gate_stats()
    
    with tab_ledger:
        render_ledger_view()
    
    with tab_policy:
        render_policy_config()


def render_gate_stats():
    """Display gate decision statistics."""
    st.subheader("Gate Decision Statistics")
    
    # Show current policy
    from rfsn_kernel.policy import DEFAULT_POLICY
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Actions/Proposal", DEFAULT_POLICY.max_actions_per_proposal)
    with col2:
        st.metric("Shell Access", "❌ Denied" if DEFAULT_POLICY.deny_shell else "✅ Allowed")
    with col3:
        st.metric("Network Access", "❌ Denied" if DEFAULT_POLICY.deny_network else "✅ Allowed")
    
    st.divider()
    
    # Gate test interface
    st.subheader("🧪 Test Gate Decision")
    
    with st.form("gate_test"):
        action_name = st.selectbox(
            "Action Type",
            ["READ_FILE", "WRITE_FILE", "RUN_TESTS", "SHELL_EXEC", "WEB_SEARCH", "BROWSE_URL"]
        )
        
        workspace = st.text_input("Workspace Path", value="/tmp/test")
        
        if st.form_submit_button("Test Gate"):
            from rfsn_kernel.gate import gate
            from rfsn_kernel.types import StateSnapshot, Proposal, Action
            
            state = StateSnapshot(
                task_id="ui_test",
                workspace_root=workspace,
                step=0,
                budget_actions_remaining=10,
            )
            
            proposal = Proposal(
                proposal_id="test",
                actions=(Action(name=action_name, args={}),),
            )
            
            decision = gate(state, proposal)
            
            if decision.status == "ALLOW":
                st.success(f"✅ **ALLOWED**: {action_name}")
            else:
                st.error(f"❌ **DENIED**: {action_name}")
                for reason in decision.reasons:
                    st.warning(f"Reason: {reason}")


def render_ledger_view():
    """Display ledger entries and hash chain."""
    st.subheader("Ledger Hash Chain")
    
    # Find ledger files
    ledger_dir = Path(".rfsn/ledgers")
    
    if not ledger_dir.exists():
        st.info("No ledger files found. Run some tasks to generate ledger entries.")
        return
    
    ledger_files = list(ledger_dir.glob("*.jsonl"))
    
    if not ledger_files:
        st.info("No ledger files found.")
        return
    
    selected_ledger = st.selectbox(
        "Select Ledger",
        options=ledger_files,
        format_func=lambda x: x.name
    )
    
    if selected_ledger:
        entries = []
        with open(selected_ledger) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        st.metric("Total Entries", len(entries))
        
        # Show entries in expandable format
        for i, entry in enumerate(entries[-10:]):  # Last 10 entries
            with st.expander(f"Entry {i+1}: {entry.get('proposal_id', 'N/A')[:8]}..."):
                st.json(entry)


def render_policy_config():
    """Display current policy configuration."""
    st.subheader("Current Kernel Policy")
    
    from rfsn_kernel.policy import DEFAULT_POLICY
    
    policy_dict = {
        "max_actions_per_proposal": DEFAULT_POLICY.max_actions_per_proposal,
        "require_tests_after_write": DEFAULT_POLICY.require_tests_after_write,
        "enforce_write_then_tests": DEFAULT_POLICY.enforce_write_then_tests,
        "deny_unknown_actions": DEFAULT_POLICY.deny_unknown_actions,
        "deny_shell": DEFAULT_POLICY.deny_shell,
        "deny_network": DEFAULT_POLICY.deny_network,
        "allow_run_cmd": DEFAULT_POLICY.allow_run_cmd,
    }
    
    st.json(policy_dict)
    
    st.divider()
    
    st.subheader("Envelope Specifications")
    
    from rfsn_kernel.envelopes import default_envelopes
    
    envs = default_envelopes("/tmp")
    
    for name, spec in envs.items():
        with st.expander(f"📦 {name}"):
            st.write(f"**Max Wall Time:** {spec.max_wall_ms}ms")
            st.write(f"**Allow Shell:** {spec.allow_shell}")
            st.write(f"**Allow Network:** {spec.allow_network}")
            if spec.path_roots:
                st.write(f"**Path Roots:** {spec.path_roots}")
