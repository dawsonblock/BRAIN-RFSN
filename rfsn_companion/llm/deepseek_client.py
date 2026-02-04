# rfsn_companion/llm/deepseek_client.py
from __future__ import annotations

import os
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


def call_deepseek(
    messages: List[Dict[str, str]],
    api_key: Optional[str] = None,
    model: str = "deepseek-chat",
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> LLMResponse:
    """
    Call DeepSeek API (OpenAI-compatible).
    """
    import httpx

    key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise ValueError("No DeepSeek API key provided")

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    return LLMResponse(
        content=choice["message"]["content"],
        model=data.get("model", model),
        usage=data.get("usage", {}),
        finish_reason=choice.get("finish_reason", "stop"),
    )


def generate_patch_from_context(
    file_path: str,
    file_content: str,
    error_trace: str,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Use DeepSeek to generate a patch for the given file based on error trace.
    Returns the full fixed file content, or None if no fix suggested.
    """
    system = """You are an expert software engineer. Your task is to fix bugs in Python code.

Given a file and an error trace, output the COMPLETE fixed file content.
Do NOT output explanations or markdown. Output ONLY the fixed Python code.
If you cannot fix the bug, output exactly: NO_FIX"""

    user = f"""File: {file_path}

=== FILE CONTENT ===
{file_content}
=== END FILE ===

=== ERROR TRACE ===
{error_trace}
=== END TRACE ===

Output the complete fixed file content:"""

    try:
        resp = call_deepseek(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_key=api_key,
            temperature=0.0,
            max_tokens=8192,
        )

        content = resp.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```python and ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        if content == "NO_FIX" or not content:
            return None

        return content

    except Exception as e:
        print(f"[DeepSeek] Error: {e}")
        return None
