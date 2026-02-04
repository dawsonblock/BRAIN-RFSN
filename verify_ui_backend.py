
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from best_build_agent import get_best_build_agent

print("Initializing agent...")
agent = get_best_build_agent()
print("Agent initialized.")

print("Checking components...")
assert agent.neuro_modulator is not None
assert agent.memory_core is not None
assert agent.dream_sync is not None
print("Components ok.")

print("Checking state access...")
state = agent.neuro_modulator.current_state
print(f"Mode: {state.mode}")
print(f"Temp: {state.temperature}")

print("Checking memory access...")
# Check if we can access the attribute
assert hasattr(agent, 'vector_memory')

print("UI Verification Successful.")
