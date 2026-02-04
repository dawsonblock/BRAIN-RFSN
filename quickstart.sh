#!/bin/bash
# RFSN Agent Quick Start Script

echo "🧠 RFSN Cognitive Architecture - Quick Start"
echo "============================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Edit .env and add your OPENAI_API_KEY before running!"
    echo "   Example: OPENAI_API_KEY=\"sk-your-key-here\""
    echo ""
    read -p "Press Enter after you've configured .env..."
fi

# Run the simulation
echo ""
echo "🚀 Launching RFSN Agent Simulation..."
echo "============================================="
echo ""
python3 main_simulation.py

echo ""
echo "✅ Simulation complete!"
