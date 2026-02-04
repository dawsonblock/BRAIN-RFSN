# ui_pages/learner_ui.py
"""
Learner Mode UI - SWE-bench Training

Displays:
- Contextual bandit arm statistics
- Outcomes database viewer
- SWE-bench task runner
- Proposer strategy selector
"""
from __future__ import annotations

import streamlit as st
import json
from pathlib import Path


def render_learner_mode():
    """Render the Learner mode dashboard."""
    
    tab_bandit, tab_outcomes, tab_swebench = st.tabs([
        "🎰 Bandit Dashboard", 
        "📊 Outcomes", 
        "🔧 SWE-bench Runner"
    ])
    
    with tab_bandit:
        render_bandit_dashboard()
    
    with tab_outcomes:
        render_outcomes_view()
    
    with tab_swebench:
        render_swebench_runner()


def render_bandit_dashboard():
    """Display contextual bandit arm statistics."""
    st.subheader("Contextual Bandit Strategy Selector")
    
    try:
        from upstream_learner.contextual_bandit import ContextualThompsonBandit
        
        # Try to load existing bandit state
        bandit_path = Path(".rfsn/bandit_state.json")
        
        if bandit_path.exists():
            bandit = ContextualThompsonBandit.load(str(bandit_path))
            
            st.metric("Total Arms", len(bandit.arms))
            
            # Show arm statistics
            st.subheader("Arm Statistics")
            
            for arm_name in bandit.arms:
                stats = bandit.get_arm_stats(arm_name)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(f"🎲 {arm_name}", f"{stats['alpha']:.1f}α / {stats['beta']:.1f}β")
                with col2:
                    st.metric("Pulls", stats["pulls"])
                with col3:
                    st.metric("Successes", stats["successes"])
                with col4:
                    mean = stats["alpha"] / (stats["alpha"] + stats["beta"])
                    st.metric("Mean", f"{mean:.2%}")
        else:
            st.info("No bandit state found. Initialize one by running a task.")
            
            # Initialize bandit button
            if st.button("🚀 Initialize Bandit"):
                bandit = ContextualThompsonBandit(
                    arms=["trace_read", "semantic_loc", "combined"],
                    seed=42
                )
                bandit.save(str(bandit_path))
                st.success("Bandit initialized!")
                st.rerun()
                
    except ImportError as e:
        st.error(f"Could not load bandit module: {e}")


def render_outcomes_view():
    """Display outcomes database entries."""
    st.subheader("Outcomes Database")
    
    try:
        from upstream_learner import outcomes_db
        
        db_path = Path(".rfsn/outcomes.db")
        
        if db_path.exists():
            # Get aggregate stats
            stats = outcomes_db.get_arm_stats(str(db_path))
            
            if stats:
                st.subheader("Aggregate Statistics")
                
                for arm, arm_stats in stats.items():
                    with st.expander(f"📈 {arm}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Tasks", arm_stats["total"])
                        with col2:
                            st.metric("Pass Rate", f"{arm_stats['pass_rate']:.1%}")
                        with col3:
                            st.metric("Avg Reward", f"{arm_stats['avg_reward']:.2f}")
            else:
                st.info("No outcomes recorded yet.")
                
            # Overall stats
            overall = outcomes_db.get_stats(str(db_path))
            st.subheader("Overall")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Outcomes", overall["total"])
            with col2:
                st.metric("Pass Rate", f"{overall['pass_rate']:.1%}")
            
        else:
            st.info("No outcomes database found. Run tasks to generate outcomes.")
            
            if st.button("🗃️ Initialize Outcomes DB"):
                outcomes_db.init_db(str(db_path))
                st.success("Outcomes DB initialized!")
                
    except ImportError as e:
        st.error(f"Could not load outcomes module: {e}")


def render_swebench_runner():
    """SWE-bench task runner interface."""
    st.subheader("SWE-bench Task Runner")
    
    st.info("Run SWE-bench tasks from the command line:")
    
    st.code("""
# Run SWE-bench Lite sample
python benchmarks/swebench_runner.py

# View results
cat swebench_results/summary.json
    """, language="bash")
    
    # Show recent results if available
    results_dir = Path("swebench_results")
    if results_dir.exists():
        result_files = list(results_dir.glob("*.json"))
        
        if result_files:
            st.subheader("Recent Results")
            
            for result_file in result_files[-5:]:
                with st.expander(f"📄 {result_file.name}"):
                    with open(result_file) as f:
                        st.json(json.load(f))
    
    # Proposer selection
    st.divider()
    st.subheader("🔧 Proposer Strategy")
    
    try:
        from rfsn_companion.proposer_variants import PROPOSER_BY_VARIANT
        
        selected = st.selectbox(
            "Select Proposer",
            options=list(PROPOSER_BY_VARIANT.keys()),
            help="Choose which proposer strategy to use for generating patches."
        )
        
        st.info(f"Selected: **{selected}**")
        
    except ImportError:
        st.warning("Proposer variants not available.")
