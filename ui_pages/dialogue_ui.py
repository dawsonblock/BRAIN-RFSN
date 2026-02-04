# ui_pages/dialogue_ui.py
"""
Dialogue Mode UI - Direct Interaction
"""
from __future__ import annotations
import streamlit as st
import time

def render_dialogue_mode(agent):
    """Render a modern chat interface."""
    
    # --- NEURAL MONITOR SIDEBAR ---
    with st.sidebar:
        st.header("🧠 Neural Monitor")
        
        # Mode Glow/Indicator
        current_mode = agent.state.mode
        mode_colors = {
            "FLOW": "background-color: #9b59b6; color: white;",
            "FOCUSED": "background-color: #3498db; color: white;",
            "CONFUSION": "background-color: #f1c40f; color: black;",
            "PANIC": "background-color: #e74c3c; color: white;",
            "BLOCK": "background-color: #2c3e50; color: white;"
        }
        style = mode_colors.get(current_mode, "background-color: #7f8c8d; color: white;")
        st.markdown(f"""
            <div style="padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; {style}">
                MODE: {current_mode}
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        
        # Chemical Levels (Simulated/Tracked)
        # Use real-time chemicals if the agent has run at least once
        nm = agent.neuro_modulator
        chem = getattr(agent, "last_chemicals", {
            "cortisol": 0.1,
            "dopamine": 0.4,
            "acetylcholine": 0.8,
            "serotonin": 0.9,
            "oxytocin": 0.7
        })
        
        st.write("**Neuro-Chemical Levels**")
        st.progress(agent.state.temperature, text=f"🌡️ Temp: {agent.state.temperature:.2f}")
        st.progress(chem["acetylcholine"], text=f"🧪 Acetylcholine: {chem['acetylcholine']:.2f}")
        st.progress(chem["dopamine"], text=f"🧬 Dopamine: {chem['dopamine']:.2f}")
        st.progress(chem["cortisol"], text=f"💢 Cortisol: {chem['cortisol']:.2f}")
        st.progress(chem["serotonin"], text=f"✨ Serotonin: {chem['serotonin']:.2f}")
        st.progress(chem["oxytocin"], text=f"💞 Oxytocin: {chem['oxytocin']:.2f}")
        
        st.divider()
        st.write("**Cognitive Tuning**")
        st.caption(f"🛡️ Strictness: {nm.base_strictness:.2f}")
        st.caption(f"⏳ Patience: {getattr(agent, 'last_chemicals', {}).get('patience', nm.base_patience):.2f}")
        st.caption(f"🤝 Cooperation: {nm.base_cooperation:.2f}")

        # Meta-Stats (Metacognition)
        st.divider()
        st.write("**Metacognition & Metabolism**")
        
        # Battery Indicator
        battery = getattr(agent.dream_sync, "wakefulness_battery", 0.0)
        battery_color = "green" if battery > 50 else "orange" if battery > 20 else "red"
        st.markdown(f"🔋 **Wakefulness:** :{battery_color}[{battery:.1f}%]")
        st.progress(battery / 100.0)

        meta = agent.identity_feedback.get_meta_statistics()
        st.metric("Self-Quality", f"{meta['average_quality']*100:.1f}%")
        st.caption(f"Thoughts: {meta['total_thoughts']}")

    st.subheader("💬 Neural Dialogue Bridge")
    st.caption("Direct neural link to the RFSN Digital Organism")

    # --- THOUGHT HISTORY (SIDEBAR EXTENSION) ---
    with st.sidebar:
        st.divider()
        st.write("**Thought History (Metacognitive Stream)**")
        with st.expander("View Internal Monologue", expanded=False):
            thoughts = agent.identity_feedback.thought_history[-10:] # Recent 10
            if not thoughts:
                st.write("No recorded thoughts in current session.")
            for t in reversed(thoughts):
                st.code(f"[{time.strftime('%H:%M:%S', time.localtime(t.timestamp))}] {t.decision}\n{t.content[:100]}...", language="text")
                if st.button(f"Analyze {t.thought_id}", key=t.thought_id):
                    st.json(t.context)

    # Display Chat History using st.chat_message
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        
        with st.chat_message(role):
            if role == "assistant":
                mem_str = f" | 💾 M: {msg.get('memories', 0)}" if msg.get("memories") else ""
                meta = f"(Mode: {msg.get('mode', 'UNKNOWN')} | Conf: {msg.get('confidence', 0.0):.2f}{mem_str})"
                st.markdown(f"**RFSN** `{meta}`")
                st.markdown(content)
                if msg.get("proactive"):
                    st.info(f"💡 {msg['proactive']}")
            else:
                st.markdown(content)

    # User Input using st.chat_input
    if prompt := st.chat_input("How can I assist your evolution today?"):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Add to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Run Agent
        with st.chat_message("assistant"):
            with st.status("⚡ Neural Processing...", expanded=True) as status:
                st.write("🛡️ Integrity Scan...")
                time.sleep(0.2)
                st.write("💾 Hippocampal Retrieval...")
                time.sleep(0.3)
                st.write("🧠 Cortical Synthesis...")
                
                start_time = time.time()
                result = agent.process_task(prompt)
                duration = time.time() - start_time
                
                st.write(f"✨ Synthesis complete in {duration:.2f}s")
                status.update(label=f"Response Generated ({result['neuro_state']})", state="complete", expanded=False)
            
            # Display assistant response
            memories_found = result.get("memories_recalled", 0)
            mem_str = f" | 💾 M: {memories_found}" if memories_found > 0 else ""
            meta = f"(Mode: {result.get('neuro_state')} | Conf: {result.get('confidence', 0.0):.2f}{mem_str})"
            st.markdown(f"**RFSN** `{meta}`")
            st.markdown(result.get("result", "Error processing request."))
            if result.get("proactive_thought"):
                st.info(f"💡 {result['proactive_thought']}")

        # Add to state
        st.session_state.messages.append({
            "role": "assistant", 
            "content": result.get("result", "Error processing request."),
            "mode": result.get("neuro_state"),
            "confidence": result.get("confidence"),
            "proactive": result.get("proactive_thought"),
            "memories": memories_found
        })
        
        st.rerun()
