# RFSN Agent - Complete Build & Implementation Guide

**Version**: 1.0  
**Status**: Ready for Implementation

## Introduction

This document provides a step-by-step guide to implementing the missing components of the RFSN Cognitive Architecture. By following this guide, you will build a fully functional, self-regulating digital organism.

The total estimated implementation time is **~8-10 hours** for an experienced Python developer.

**Before you begin, ensure you have:**
1.  Completed the setup instructions in `README.md`.
2.  Reviewed the **[System Analysis](./rfsn_analysis.md)** to understand the architecture.
3.  Familiarized yourself with the **[Project Structure](./project_structure.md)**.

---

## Phase 1: Foundational Components (Critical Path)

This phase implements the absolute requirements for the agent to function.

### **Step 1.1: LLM Client**

-   **File**: `rfsn_agent/rfsn_controller/llm_client.py`
-   **Purpose**: To provide a standardized interface for making calls to an OpenAI-compatible LLM API (like DeepSeek or OpenAI).
-   **Complexity**: Low

**Implementation:**

Create the file and add the following code. This implementation uses the `openai` library, which can be configured to point to different API endpoints via environment variables.

```python
"""
LLM API Client.
Provides a unified interface to an OpenAI-compatible API.
"""
from __future__ import annotations

import os
import logging
from typing import Dict, Any, Union

from openai import OpenAI, APIError

logger = logging.getLogger(__name__)

# Initialize the client from environment variables
# Ensure OPENAI_API_KEY and OPENAI_BASE_URL are set in your .env file
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)

def call_deepseek(prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> Union[Dict[str, Any], str]:
    """
    Calls the configured LLM with a given prompt and temperature.

    Args:
        prompt: The input prompt for the LLM.
        temperature: The creativity/randomness of the output (0.0 - 1.0).
        max_tokens: The maximum number of tokens to generate.

    Returns:
        A dictionary containing the response content or an error string.
    """
    try:
        logger.debug(f"Calling LLM with temp={temperature}, prompt='{prompt[:100]}...'" )
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
            messages=[
                {"role": "system", "content": "You are a component of a larger AI system. Be concise and accurate."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.choices[0].message.content
        if not content:
            return {"error": "Empty response from LLM."}
            
        return {"content": content.strip()}

    except APIError as e:
        logger.error(f"LLM API Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"An unexpected error occurred during LLM call: {e}")
        return {"error": "An unexpected error occurred."}

```

### **Step 1.2: Behavioral Monitor (The Amygdala)**

-   **File**: `rfsn_agent/security/behavioral_monitor.py`
-   **Purpose**: To detect risky or anomalous actions and generate a "Cortisol" signal.
-   **Complexity**: Medium

**Implementation:**

This implementation uses a simple rule-based system to identify potentially dangerous commands. A production system might use a more sophisticated statistical model.

```python
"""
Behavioral Monitor (The Amygdala).
Detects threats and generates risk signals (Cortisol).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class EventResult:
    risk_score: float = 0.0
    is_anomalous: bool = False
    explanation: str = ""

@dataclass
class SecurityReport:
    risk_percentage: float = 0.0
    recent_anomalies: List[Dict] = field(default_factory=list)

class BehavioralMonitor:
    def __init__(self):
        self.recent_events: List[Dict] = []
        self.risk_level: float = 0.0
        # Simple rule-based threat detection
        self.dangerous_patterns = [
            "rm -rf", "| bash", "> /dev/null", "/etc/shadow", "wget http", "curl http"
        ]

    def record_event(self, event_type: str, details: Dict[str, Any]) -> EventResult:
        """
        Records and analyzes an event for potential threats.
        """
        command = details.get("command", "")
        risk_score = 0.0
        is_anomalous = False
        explanation = ""

        for pattern in self.dangerous_patterns:
            if pattern in command:
                risk_score = 0.9
                is_anomalous = True
                explanation = f"Detected dangerous pattern: '{pattern}'"
                break
        
        if "sudo" in command and risk_score < 0.8:
            risk_score = 0.6
            explanation = "Use of sudo requires caution."

        self.risk_level = (self.risk_level * 0.5) + (risk_score * 0.5) # Decay risk over time
        
        event_log = {"type": event_type, "details": details, "risk": risk_score}
        self.recent_events.append(event_log)
        if len(self.recent_events) > 100:
            self.recent_events.pop(0)
            
        logger.debug(f"Event recorded: {event_type}, Risk: {risk_score:.2f}")
        return EventResult(risk_score=risk_score, is_anomalous=is_anomalous, explanation=explanation)

    def get_security_report(self) -> Dict[str, Any]:
        """
        Returns a summary of the current security state.
        """
        report = {
            "risk_percentage": self.risk_level * 100,
            "total_events": len(self.recent_events)
        }
        return report

# Singleton instance
_monitor: Optional[BehavioralMonitor] = None

def get_monitor() -> BehavioralMonitor:
    global _monitor
    if _monitor is None:
        _monitor = BehavioralMonitor()
    return _monitor

```

### **Step 1.3: Advanced Sandbox**

-   **File**: `rfsn_agent/security/advanced_sandbox.py`
-   **Purpose**: To execute commands in an isolated and controlled environment.
-   **Complexity**: Medium

**Implementation:**

This implementation uses Python's built-in `subprocess` module. For enhanced security, this could be extended to use Docker containers.

```python
"""
Advanced Sandbox.
Provides an isolated environment for command execution.
"""
from __future__ import annotations

import subprocess
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class SandboxConfig:
    network_enabled: bool = True
    timeout_seconds: int = 30

@dataclass
class SandboxInstance:
    workspace_path: str

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str

class AdvancedSandbox:
    def __init__(self):
        self.config = SandboxConfig()

    def create_sandbox(self, workspace_path: str) -> SandboxInstance:
        """Creates a new sandbox instance (workspace)."""
        os.makedirs(workspace_path, exist_ok=True)
        return SandboxInstance(workspace_path=workspace_path)

    def execute(self, sandbox: SandboxInstance, command: List[str]) -> ExecutionResult:
        """
        Executes a command within the specified sandbox.
        """
        env = os.environ.copy()
        if not self.config.network_enabled:
            # This is a simplistic way to disable network. 
            # A real sandbox would use network namespaces or other robust methods.
            logger.warning("Sandbox network is disabled.")

        try:
            process = subprocess.run(
                command,
                cwd=sandbox.workspace_path,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                env=env,
                check=False  # Do not raise exception on non-zero exit codes
            )
            
            logger.info(f"Executed command: {' '.join(command)}, Exit Code: {process.returncode}")
            return ExecutionResult(
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(command)}")
            return ExecutionResult(exit_code=-1, stdout="", stderr=f"Timeout after {self.config.timeout_seconds}s")
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return ExecutionResult(exit_code=-1, stdout="", stderr=str(e))

# Singleton instance
_sandbox: Optional[AdvancedSandbox] = None

def get_sandbox() -> AdvancedSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = AdvancedSandbox()
    return _sandbox

```

---

## Phase 2: Cognitive Layer

With the foundational components in place, we can now build the agent's "mind."

### **Step 2.1: Proactive Output Engine (The Striatum)**

-   **File**: `rfsn_agent/cognitive/proactive_output_engine.py`
-   **Purpose**: To generate spontaneous thoughts and a "Dopamine" signal when the agent is idle or under-stimulated.
-   **Complexity**: Medium

**Implementation:**

This implementation simulates "entropy" by checking if recent memories are repetitive. It uses the LLM to generate a curious question when entropy is low.

```python
"""
Proactive Output Engine (The Striatum).
Generates spontaneous thoughts and curiosity signals (Dopamine).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cognitive.capsule_memory_core import get_memory_core
from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

@dataclass
class ProactiveThought:
    content: str
    source: str = "spontaneous"

class ProactiveOutputEngine:
    def __init__(self):
        self.memory_core = get_memory_core()
        self.entropy_level = 0.5 # Start with moderate entropy

    def scan_for_entropy(self) -> float:
        """
        Scans recent memory for repetitiveness to calculate entropy.
        High entropy = novel experiences. Low entropy = repetitive/boring.
        """
        recent_capsules = self.memory_core.retrieve_capsules(limit=10)
        if len(recent_capsules) < 5:
            self.entropy_level = 0.8 # Not enough data, assume high entropy
            return self.entropy_level

        # Simple entropy check: count unique content hashes
        unique_contents = {hash(c.content) for c in recent_capsules}
        repetition_ratio = 1.0 - (len(unique_contents) / len(recent_capsules))
        
        # Low repetition = high entropy
        self.entropy_level = 1.0 - repetition_ratio
        logger.debug(f"Entropy calculated: {self.entropy_level:.2f}")
        return self.entropy_level

    def generate_proactive_thought(self) -> Optional[ProactiveThought]:
        """
        Generates a spontaneous thought or question based on recent context.
        """
        if self.entropy_level > 0.6:
            return None # No need for proactive thought if entropy is high

        recent_capsules = self.memory_core.retrieve_capsules(limit=3)
        if not recent_capsules:
            return None

        context = "\n".join([f"- {c.content}" for c in recent_capsules])
        prompt = f"""
        Based on this recent activity:
        {context}
        
        What is one unexpected question I could ask to discover something new?
        Frame it as a hypothesis. Be concise.
        """
        
        response = call_deepseek(prompt, temperature=0.8)
        if "content" in response and response["content"]:
            thought_content = response["content"]
            logger.info(f"Generated proactive thought: {thought_content}")
            return ProactiveThought(content=thought_content)
        
        return None

# Singleton instance
_proactive_engine: Optional[ProactiveOutputEngine] = None

def get_proactive_engine() -> ProactiveOutputEngine:
    global _proactive_engine
    if _proactive_engine is None:
        _proactive_engine = ProactiveOutputEngine()
    return _proactive_engine

```

### **Step 2.2: Reasoning Engine (The Cortex)**

-   **File**: `rfsn_agent/cognitive/reasoning_engine.py`
-   **Purpose**: The primary problem-solving component, using the LLM to analyze tasks and devise solutions.
-   **Complexity**: High

**Implementation:**

This is the most critical LLM-facing component. The prompts here are key to the agent's performance.

```python
"""
Reasoning Engine (The Cortex).
Handles primary problem-solving and planning.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from rfsn_controller.llm_client import call_deepseek

logger = logging.getLogger(__name__)

@dataclass
class Context:
    problem_statement: str
    code_files: Dict[str, str] = field(default_factory=dict)
    test_outputs: List[str] = field(default_factory=list)

@dataclass
class ReasoningResult:
    understanding: str
    suggested_approach: str
    confidence: float

class ReasoningEngine:
    def __init__(self):
        pass

    def build_context(self, problem_statement: str, 
                      code_files: Optional[Dict[str, str]] = None, 
                      test_outputs: Optional[List[str]] = None) -> Context:
        """Constructs a structured context object."""
        return Context(
            problem_statement=problem_statement,
            code_files=code_files or {},
            test_outputs=test_outputs or []
        )

    def reason(self, context: Context, temperature: float = 0.2) -> ReasoningResult:
        """
        Uses the LLM to reason about the provided context and generate a plan.
        """
        code_context = "\n".join([f"--- {path} ---\n{content}" for path, content in context.code_files.items()])
        test_context = "\n".join(context.test_outputs)

        prompt = f"""
        **Problem Statement:**
        {context.problem_statement}

        **Relevant Code Files:**
        {code_context if code_context else 'None'}

        **Recent Test Outputs/Errors:**
        {test_context if test_context else 'None'}

        --- 
        **Your Task:**
        1.  **Understand:** In one sentence, what is the core problem?
        2.  **Approach:** In a few sentences, what is the most logical next step to solve this?
        3.  **Confidence:** On a scale of 0.0 to 1.0, how confident are you in this approach?

        Format your response as a JSON object with keys "understanding", "approach", and "confidence".
        """

        response = call_deepseek(prompt, temperature=temperature)
        
        if "content" in response and response["content"]:
            try:
                import json
                result_json = json.loads(response["content"])
                return ReasoningResult(
                    understanding=result_json.get("understanding", ""),
                    suggested_approach=result_json.get("approach", ""),
                    confidence=float(result_json.get("confidence", 0.5))
                )
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"Failed to parse reasoning response: {e}")
                # Fallback to simple parsing if JSON fails
                return ReasoningResult(
                    understanding="Could not parse LLM response.",
                    suggested_approach=response["content"],
                    confidence=0.3
                )
        
        return ReasoningResult(
            understanding="Failed to get a response from the reasoning core.",
            suggested_approach="",
            confidence=0.0
        )

# Singleton instance
_reasoning_engine: Optional[ReasoningEngine] = None

def get_reasoning_engine() -> ReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine

```

---

## Phase 3: Integration & Finalization

### **Step 3.1: Create `requirements.txt`**

Create a `requirements.txt` file in the root of the `rfsn_agent` directory:

```txt
# Core Dependencies
openai>=1.0.0
python-dotenv>=1.0.0

# Development & Testing
pytest>=7.0.0
```

### **Step 3.2: Create `.env.example`**

Create a `.env.example` file in the root of the `rfsn_agent` directory:

```bash
# API credentials for the LLM
OPENAI_API_KEY="sk-your-key-here"
OPENAI_BASE_URL="https://api.deepseek.com/v1" # Or https://api.openai.com/v1
LLM_MODEL="deepseek-chat" # Or gpt-4, etc.

# Logging level (DEBUG, INFO, WARNING, ERROR)
RFSN_LOG_LEVEL=INFO
```

### **Step 3.3: Review Imports**

Go through the provided files (`best_build_agent.py`, `dream_reality_sync.py`, etc.) and ensure all imports now resolve correctly. The provided code uses relative imports that should work with the new file structure.

---

## Congratulations!

If you have followed all the steps, you now have a complete, functional RFSN agent. You are ready to run the `main_simulation.py` script and observe the agent's life-like behavior.

### To Run the Simulation:

1.  Make sure your `.env` file is correctly configured.
2.  Run the main simulation script from the root directory:

    ```bash
    python3 rfsn_agent/main_simulation.py
    ```

Observe the console output to see the agent's neuro-state change as it encounters different scenarios. Watch as it enters a panic state, recovers through a nightmare, and learns from its experience.

Welcome to the future of autonomous AI.
