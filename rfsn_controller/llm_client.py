"""
LLM API Client.
Provides a unified interface to an OpenAI-compatible API.
"""
from __future__ import annotations

import os
import logging
import hashlib
import sqlite3
from typing import Dict, Any, Union, Optional

try:
    from openai import OpenAI, APIError
except ImportError:  # optional dependency
    OpenAI = None  # type: ignore
    APIError = Exception  # type: ignore

logger = logging.getLogger(__name__)

# Internal client cache
_client: Optional[OpenAI] = None

class LLMCache:
    """SQLite-based cache for LLM responses to reduce latency and costs."""
    def __init__(self, db_path: str = "llm_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize LLM cache: {e}")

    def get(self, prompt: str) -> Optional[str]:
        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT response FROM cache WHERE hash = ?", (prompt_hash,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None

    def set(self, prompt: str, response: str):
        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT OR REPLACE INTO cache (hash, prompt, response) VALUES (?, ?, ?)",
                        (prompt_hash, prompt, response))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Cache set failed: {e}")

# Global instances
_llm_cache = LLMCache()

def _get_client() -> OpenAI:
    if OpenAI is None:
        raise RuntimeError("openai package not installed; install with: pip install openai")

    """Returns a lazy-loaded OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
            
        _client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    return _client

def call_deepseek(prompt: str, temperature: float = 0.2, max_tokens: int = 1024, model: Optional[str] = None) -> Union[Dict[str, Any], str]:
    """
    Calls the configured LLM with a given prompt and temperature.
    Supports caching for near-deterministic calls (temp < 0.1).
    """
    # 1. Check Cache
    use_cache = temperature < 0.1
    if use_cache:
        cached_resp = _llm_cache.get(prompt)
        if cached_resp:
            logger.info("⚡ LLM Cache Hit!")
            return {"content": cached_resp, "cached": True}

    try:
        logger.debug(f"Calling LLM with temp={temperature}, prompt='{prompt[:100]}...'" )
        client = _get_client()
        
        target_model = model or os.getenv("LLM_MODEL", "deepseek-chat")
        
        response = client.chat.completions.create(
            model=target_model,
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
            
        # 2. Update Cache
        if use_cache:
            _llm_cache.set(prompt, content.strip())
            
        return {"content": content.strip(), "cached": False}

    except APIError as e:
        logger.error(f"LLM API Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"An unexpected error occurred during LLM call: {e}")
        return {"error": "An unexpected error occurred."}

