<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Tests-180%20Passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/DeepSeek-R1%20Integrated-purple" alt="DeepSeek R1">
</p>

<h1 align="center">🧠 RFSN Cognitive Architecture</h1>
<p align="center"><strong>A Biologically-Inspired Digital Organism for Autonomous AI Agents</strong></p>

<p align="center">
  <em>Self-regulating • Adaptive • Memory-Augmented • Safety-First</em>
</p>

---

## 🌟 Overview

RFSN (**Recursive Feedback Sensitive Network**) is a next-generation cognitive architecture that treats AI agents as **living digital organisms** rather than static input-output machines.

The system implements a dynamic **"Stimulus → Internal State Change → Response → Adaptation"** cycle, enabling:

| Capability | Description |
|------------|-------------|
| 🧪 **Neuro-Chemical Modulation** | Simulated cortisol, dopamine, serotonin, and oxytocin dynamically adjust reasoning temperature, risk tolerance, and persistence |
| 🛡️ **Reflexive Safety** | PANIC mode lockdowns triggered by stress, restricting actions and network access |
| 🌙 **Dream Cycles** | REM-like offline processing for memory consolidation and trauma recovery |
| 📚 **Upstream Learning** | Cross-repository strategy transfer via semantic bandits |
| 🔬 **Self-Improvement** | Automated failure analysis and survival rule generation |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        🧠 RFSN DIGITAL ORGANISM                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  SECURITY   │  │  COGNITIVE  │  │CONSCIOUSNESS│  │  LEARNING   │ │
│  │  (Amygdala) │  │   (Cortex)  │  │  (Limbic)   │  │(Hippocampus)│ │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤ │
│  │ Sandbox     │  │ Reasoning   │  │ Neuro-Mod   │  │ Knowledge   │ │
│  │ Monitor     │  │ Memory Core │  │ Dream Sync  │  │ Base        │ │
│  │ Injection   │  │ Planner     │  │ Mirror      │  │ Vector      │ │
│  │ Shield      │  │ Emotions    │  │ Kernel      │  │ Store       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     RFSN KERNEL (GATE)                         ││
│  │  Hard Boundary: Proposal Validation • Path Containment • Budget ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Core Cycle: **Sense → Modulate → Act → Sleep**

1. **SENSE** — Perceive environment: risk levels, novelty (entropy), performance metrics
2. **MODULATE** — Translate to neuro-chemicals that adjust temperature, strictness, persistence
3. **ACT** — Execute tasks with chemical-influenced reasoning
4. **SLEEP** — REM cycles for memory consolidation, nightmare protocol, synaptic pruning

---

## ✨ Key Features

### 🛡️ Safety Kernel (Hard Boundary)

- **Path containment**: All file operations sandboxed to workspace
- **Action validation**: Unknown actions blocked, order rules enforced
- **Reflexive lockdown**: PANIC mode restricts to read/test/recall only
- **Budget enforcement**: Action limits prevent runaway execution

### 🧪 Neuro-Chemical System

| Chemical | Role | Effect |
|----------|------|--------|
| **Cortisol** | Stress | ↑ Gate strictness, ↓ Temperature |
| **Dopamine** | Curiosity | ↑ Exploration variance, ↑ Creativity |
| **Acetylcholine** | Focus | ↑ Persistence, ↑ Retry limits |
| **Serotonin** | Stability | ↑ Patience, ↓ Impulsivity |
| **Oxytocin** | Bonding | ↑ Cooperation signals |

### 🌙 Consciousness Layer

- **Dream Reality Sync**: Manages wake/REM cycles based on cognitive battery
- **Nightmare Protocol**: Adversarial replay of failures to derive survival rules
- **Memory Pruner**: Synaptic cleanup of low-confidence memories during REM
- **Mirror Kernel**: Identity continuity and self-awareness checks

### 📚 Learning System

- **Thompson Bandit**: Dopamine-scaled exploration for strategy selection
- **Semantic Bandit**: Cross-repository pattern matching via embeddings
- **Knowledge Base**: Survival rules and heuristics with confidence tracking
- **Episodic Memory**: Time-tagged experiences with emotional valence

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- DeepSeek API key (or OpenAI-compatible)

### Installation

```bash
# Clone the repository
git clone https://github.com/dawsonblock/BRAIN-RFSN.git
cd BRAIN-RFSN

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

### Running the Agent

```bash
# Interactive mode
python run_agent.py --interactive

# Single task
python run_agent.py --task "Fix the bug in utils.py"

# Run simulation demo
python main_simulation.py
```

### Launch the Neural Dashboard

```bash
streamlit run web_interface.py
```

---

## 📊 Benchmark Results

Evaluated with **DeepSeek R1** (`deepseek-reasoner`):

| Benchmark | Resolve Rate | Details |
|-----------|--------------|---------|
| **SWE-bench Lite** | 100% (5/5) | Automated code repair |
| **GAIA Sample** | 100% (8/8) | Multi-step reasoning |

---

## 🗂️ Project Structure

```
rfsn_complete_build/
├── security/           # Amygdala: Sandbox, Monitor, Injection Shield
├── cognitive/          # Cortex: Reasoning, Memory, Planner, Emotions
├── consciousness/      # Limbic: Neuro-Mod, Dreams, Mirror Kernel
├── learning/           # Hippocampus: Knowledge Base, Heuristics
├── rfsn_kernel/        # Hard Boundary: Gate, Types, Ledger, Replay
├── rfsn_companion/     # LLM Clients, Proposers, Selectors
├── upstream_learner/   # Bandits, Policy Store, Episode Runner
├── ui_pages/           # Streamlit UI Components
├── tests/              # 180+ Passing Tests
└── benchmarks/         # SWE-bench, GAIA Runners
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [System Analysis](./rfsn_analysis.md) | Deep dive into architecture and data flows |
| [Project Structure](./project_structure.md) | Component map and dependencies |
| [Build Guide](./BUILD_GUIDE.md) | Step-by-step implementation guide |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

---

<p align="center">
  <strong>Built with 🧠 by the RFSN Research Team</strong>
</p>
