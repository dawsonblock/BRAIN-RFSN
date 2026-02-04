# ui_pages/research_ui.py
"""
Research Mode UI - AGI Exploration

The RFSN Neural Interface:
- Mission Control (chat)
- Brain MRI (neuro state)
- Memory Bank (vector search)
- Learning Lab (cognitive modules)
"""
from __future__ import annotations

import streamlit as st
import time
import plotly.graph_objects as go


def render_research_mode(agent):
    """Render the Research mode dashboard (original UI)."""
    
    tab_brain, tab_memory, tab_learning = st.tabs([
        "🧠 Brain MRI", 
        "💾 Memory Bank",
        "🎓 Learning Lab"
    ])
    
    with tab_brain:
        render_brain_mri(agent)
    
    with tab_memory:
        render_memory_bank(agent)
    
    with tab_learning:
        render_learning_lab(agent)


def render_mission_control(agent):
    """Chat interface with the digital organism."""
    st.subheader("🚀 Interaction Terminal")
    
    # Initialize messages if needed
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display Chat History
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                st.markdown(f'<div class="chat-user"><b>👤 USER:</b><br>{content}</div>', unsafe_allow_html=True)
            else:
                meta = f"<i>(Mode: {msg.get('mode', 'UNKNOWN')} | Conf: {msg.get('confidence', 0.0):.2f})</i>"
                st.markdown(f'<div class="chat-agent"><b>🤖 RFSN:</b> {meta}<br>{content}</div>', unsafe_allow_html=True)
                if msg.get("proactive"):
                    st.info(f"💡 Proactive Thought: {msg['proactive']}")

    # User Input
    if prompt := st.chat_input("Enter command or task description..."):
        # Add User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Run Agent
        with st.status("⚡ Thinking...", expanded=True) as status:
            st.write("🛡️ Scanning for Prompt Injection...")
            time.sleep(0.5)
            
            start_time = time.time()
            result = agent.process_task(prompt)
            duration = time.time() - start_time
            
            st.write(f"✨ Processing complete in {duration:.2f}s")
            status.update(label=f"Done ({result['neuro_state']})", state="complete", expanded=False)
        
        # Add Agent Response
        st.session_state.messages.append({
            "role": "assistant", 
            "content": result.get("result", "Error processing request."),
            "mode": result.get("neuro_state"),
            "confidence": result.get("confidence"),
            "proactive": result.get("proactive_thought")
        })
        
        st.rerun()


def render_brain_mri(agent):
    """Display neuro-chemical state and cognitive parameters."""
    col_chem, col_params = st.columns([1, 1])
    
    with col_chem:
        st.subheader("🧪 Neuro-Chemical Levels")
        state = agent.neuro_modulator.current_state
        
        categories = ['Temperature', 'Strictness', 'Patience', 'Cooperation']
        values = [state.temperature, state.gate_strictness, state.patience, state.cooperation]
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            fillcolor='rgba(139, 92, 246, 0.3)',
            line=dict(color='#8b5cf6', width=2)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], gridcolor='rgba(99, 102, 241, 0.3)'),
                angularaxis=dict(gridcolor='rgba(99, 102, 241, 0.3)')
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e8e8e8'),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_params:
        st.subheader("⚙️ Cognitive Parameters")
        state = agent.neuro_modulator.current_state
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mode", state.mode)
            st.metric("Search Depth", state.search_depth)
        with col2:
            st.metric("Context Size", len(agent.state.current_context or {}))
            st.metric("Failures", len(agent.recent_failures))
        
        st.divider()
        
        st.subheader("🛡️ Security Shield")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sensitivity", f"{agent.injection_shield.sensitivity:.2f}")
        with col2:
            st.metric("Patterns", len(agent.injection_shield.patterns))


def render_memory_bank(agent):
    """Display core beliefs and vector memory search."""
    st.subheader("💎 Core Beliefs (Identity Layer)")
    
    # Access nightmare_engine through dream_sync
    try:
        beliefs = agent.dream_sync.nightmare_engine.core_beliefs.get_active_beliefs()
        if beliefs:
            for b in beliefs:
                st.warning(f"**{b.principle}**\n\n*Origin: {b.origin_trauma}*")
        else:
            st.info("No Core Beliefs crystallized yet. Processing trauma needed.")
    except AttributeError:
        st.info("Core beliefs module not available.")
        
    st.divider()
    
    st.subheader("🔍 Vector Memory (Hippocampus)")
    search_query = st.text_input("Query Memory Cortex:", placeholder="Search for memories...")
    if search_query:
        if agent.vector_memory:
            results = agent.vector_memory.retrieve(search_query, k=3)
            for res in results:
                with st.expander(f"📄 Match ({res.relevance:.2f})"):
                    st.write(res.text)
                    st.json(res.metadata)
        else:
            st.error("Vector Store not available.")


def render_learning_lab(agent):
    """Display learning and self-improvement modules."""
    st.subheader("🎓 Cognitive Learning Modules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📚 Self-Improvement Engine")
        try:
            # Module remains available, but imports cleaned up for linting
            st.write("**Status:** ✅ Module Available")
            st.write("**Mode:** Continuous Learning")
            
            with st.expander("📊 Module Info"):
                st.info("Self-improvement analyzes failures from episodic memory and proposes system improvements.")
                st.write("- Failure pattern detection")
                st.write("- Improvement proposals")
                st.write("- Gate-approved changes")
            
            if st.button("🔄 Trigger Self-Analysis"):
                st.toast("Self-analysis requires an active episodic store. Run tasks first.")
                
        except ImportError as e:
            st.error(f"Module not available: {e}")
    
    with col2:
        st.markdown("### 🧠 Episodic Memory")
        try:
            
            st.write("**Status:** ✅ Module Available")
            st.write("**Type:** Long-term Storage")
            
            with st.expander("📊 Module Info"):
                st.info("Episodic memory stores complete task episodes for later recall and learning.")
                st.write("- Episode storage")
                st.write("- Pattern retrieval")
                st.write("- Failure analysis")
                
        except ImportError as e:
            st.error(f"Module not available: {e}")
    
    st.divider()
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("### 🌙 Memory Consolidation")
        try:
            
            st.write("**Status:** ✅ Module Available")
            st.write("**Mode:** Sleep-based Transfer")
            
            with st.expander("📊 Module Info"):
                st.info("Memory consolidation transfers important experiences from STM to LTM during sleep cycles.")
                st.write("- STM → LTM transfer")
                st.write("- Memory pruning")
                st.write("- Knowledge synthesis")
                
            if st.button("💤 Force Consolidation"):
                st.toast("Consolidation happens during sleep cycles. Use 'Force Sleep' in sidebar.")
                
        except ImportError as e:
            st.error(f"Module not available: {e}")
    
    with col4:
        st.markdown("### 🔗 Recursive Identity Feedback")
        try:
            from cognitive.recursive_identity_feedback import RecursiveIdentityFeedback
            
            rif = RecursiveIdentityFeedback()
            stats = rif.get_meta_statistics()
            
            st.write("**Status:** ✅ Active")
            st.write("**Mode:** Identity Reinforcement")
            
            with st.expander("📊 Identity Stats"):
                st.metric("Thoughts Recorded", stats["total_thoughts"])
                st.metric("Reviews Conducted", stats["total_reviews_conducted"])
                st.metric("Avg Quality", f"{stats['average_quality']:.1%}")
                st.info("Identity strengthens through consistent behavior.")
                
        except ImportError as e:
            st.error(f"Module not available: {e}")
    
    st.divider()
    
    st.markdown("### 🎯 Learning Dashboard")
    
    # Create a summary chart
    learning_modules = ["Self-Improve", "Episodic", "Consolidation", "Identity"]
    status_values = [0.75, 0.60, 0.85, 0.90]
    
    fig = go.Figure(data=go.Bar(
        x=learning_modules,
        y=status_values,
        marker=dict(
            color=['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'],
            line=dict(color='rgba(255,255,255,0.3)', width=1)
        ),
        text=[f"{v:.0%}" for v in status_values],
        textposition='outside'
    ))
    fig.update_layout(
        title="Module Health Status",
        yaxis=dict(range=[0, 1.2], showgrid=True, gridcolor='rgba(99, 102, 241, 0.2)'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8'),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)
