#!/bin/bash
# Launch the RFSN Neural Interface
echo "🧠 RFSN Neural Interface initializing..."
echo "📂 Loading Brain State..."

# Check designed for streamlit
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing..."
    pip install streamlit pandas plotly
fi

streamlit run web_interface.py
