"""
RFSN Neural Interface
A modern, real-time command center for the RFSN Digital Organism.
Now with Mode Switcher: Kernel, Learner, Research + Learning Modules
Updated to Light/White Theme
"""
import streamlit as st

from modes import RFSNMode, get_mode_options, parse_mode_selection, get_mode_config

# Configure page
st.set_page_config(
    page_title="RFSN Neural Interface",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light Theme CSS with clean white background and vibrant accents
st.markdown("""
<style>
    /* Main app background - Clean White */
    .stApp {
        background-color: #ffffff;
        color: #1f2937;
    }
    
    /* Sidebar styling - Light Grey with Border */
    [data-testid="stSidebar"] {
        background-color: #f9fafb;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Headers with vibrant gradients but dark text compatibility */
    h1, h2, h3 {
        background: linear-gradient(90deg, #2563eb, #7c3aed, #db2777);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
    }
    
    /* Buttons - Vibrant but clean */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        font-weight: 600;
        padding: 0.6rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(79, 70, 229, 0.1);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
        box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2);
        transform: translateY(-1px);
    }
    
    /* Metrics - Distinct colors on white */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        color: #111827;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #4b5563;
        font-weight: 500;
    }
    
    /* Tabs styling - Minimalist light tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f3f4f6;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #6b7280;
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: #4f46e5 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Cards/Containers */
    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Chat styling - Light variant */
    .chat-user {
        background-color: #f3f4f6;
        color: #1f2937;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 12px;
        border-right: 4px solid #4f46e5;
    }
    .chat-agent {
        background-color: #f0f9ff;
        color: #1e3a8a;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #0ea5e9;
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        background: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        color: #111827;
    }
    
    /* Code blocks */
    code {
        color: #dc2626;
        background: #f9fafb;
    }
    
    /* Mode indicators */
    .mode-kernel { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 99px; font-weight: 600; }
    .mode-learner { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 99px; font-weight: 600; }
    .mode-research { background: #f3e8ff; color: #6b21a8; padding: 4px 12px; border-radius: 99px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Initialize mode in session state
if "current_mode" not in st.session_state:
    st.session_state.current_mode = RFSNMode.DIALOGUE

# Sidebar - Mode Selector & System Status
with st.sidebar:
    st.title("🧠 RFSN-V1")
    st.caption("Recursive Feedback Sensitive Network")
    
    st.divider()
    
    # Mode Selector
    st.subheader("🔄 Active Mode")
    mode_options = get_mode_options()
    current_index = list(RFSNMode).index(st.session_state.current_mode)
    
    selected_mode = st.selectbox(
        "Select Mode",
        options=mode_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    new_mode = parse_mode_selection(selected_mode)
    if new_mode != st.session_state.current_mode:
        st.session_state.current_mode = new_mode
        st.rerun()
    
    # Show mode description
    config = get_mode_config(st.session_state.current_mode)
    st.caption(config.description)
    
    st.divider()
    
    # Mode-specific sidebar content
    if st.session_state.current_mode in [RFSNMode.DIALOGUE, RFSNMode.RESEARCH]:
        # Initialize Agent (for Dialogue and Research modes)
        if "agent" not in st.session_state:
            with st.spinner("🚀 Booting Digital Organism..."):
                from best_build_agent import get_best_build_agent
                st.session_state.agent = get_best_build_agent()
                st.session_state.messages = []
                st.success("⚡ System Online")
        
        agent = st.session_state.agent
        
        # Brain State Metrics
        neuro_state = agent.neuro_modulator.current_state
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mode", neuro_state.mode, delta=None)
        with col2:
            st.metric("Battery", f"{agent.dream_sync.wakefulness_battery:.0f}%")
            
        st.progress(agent.dream_sync.wakefulness_battery / 100.0, text="Wakefulness")
        
        st.divider()
        
        st.subheader("⚡ Controls")
        if st.button("💤 Force Sleep Cycle"):
            report = agent.dream_sync.enter_rem_cycle(agent.recent_failures, agent.security_incidents)
            agent.neuro_modulator.reset_baseline()
            st.toast(f"Sleep Complete. Learned: {len(report.lessons_learned)} lessons.")
            
        if st.button("🧼 Prune Memory"):
            if agent.vector_memory:
                stats = agent.vector_memory.count()
                st.toast(f"Memory Integrity Check: {stats} capsules active.")
            else:
                st.error("Vector Memory not available.")

        if st.button("🔴 Reset Simulation"):
            st.session_state.messages = []
            agent.recent_failures = []
            agent.security_incidents = []
            agent.neuro_modulator.reset_baseline()
            st.rerun()
    
    elif st.session_state.current_mode == RFSNMode.KERNEL:
        st.subheader("🔒 Kernel Status")
        from rfsn_kernel.policy import DEFAULT_POLICY
        st.write(f"**Shell:** {'❌ Blocked' if DEFAULT_POLICY.deny_shell else '✅ Allowed'}")
        st.write(f"**Network:** {'❌ Blocked' if DEFAULT_POLICY.deny_network else '✅ Allowed'}")
        st.write(f"**Unknown:** {'❌ Blocked' if DEFAULT_POLICY.deny_unknown_actions else '✅ Allowed'}")
    
    elif st.session_state.current_mode == RFSNMode.LEARNER:
        st.subheader("📈 Learner Status")
        from pathlib import Path
        bandit_path = Path(".rfsn/bandit_state.json")
        outcomes_path = Path(".rfsn/outcomes.db")
        st.write(f"**Bandit:** {'✅ Loaded' if bandit_path.exists() else '⏳ Init needed'}")
        st.write(f"**Outcomes:** {'✅ Ready' if outcomes_path.exists() else '⏳ Init needed'}")

# Main Content Area - Route to mode-specific UI
if st.session_state.current_mode == RFSNMode.DIALOGUE:
    from ui_pages.dialogue_ui import render_dialogue_mode
    render_dialogue_mode(st.session_state.agent)

elif st.session_state.current_mode == RFSNMode.KERNEL:
    from ui_pages.kernel_ui import render_kernel_mode
    render_kernel_mode()

elif st.session_state.current_mode == RFSNMode.LEARNER:
    from ui_pages.learner_ui import render_learner_mode
    render_learner_mode()

elif st.session_state.current_mode == RFSNMode.RESEARCH:
    from ui_pages.research_ui import render_research_mode
    render_research_mode(st.session_state.agent)
