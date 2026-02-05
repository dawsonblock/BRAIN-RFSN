# rfsn_swe_llm.py
"""
Stdlib-only OpenAI-compatible client + strict diff extractor.

You can point this at:
- OpenAI chat completions endpoint
- Any gateway that accepts the same JSON shape
- A local server (LLM_BASE_URL=http://localhost:.../v1/chat/completions)

Env:
  LLM_API_KEY
  LLM_MODEL
  LLM_BASE_URL
Optional:
  LLM_TIMEOUT_S
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict


_UNIFIED_DIFF_START_RE = re.compile(r"(?m)^(diff --git .+)$")
_UNIFIED_DIFF_HEADER_RE = re.compile(r"(?m)^(---\s+\S+)$")


def extract_unified_diff(raw: str) -> str:
    """
    Extract a unified diff from arbitrary model text.

    Rules:
    - Prefer content from first "diff --git" to end
    - Else fallback to first "--- " header block
    - Strip surrounding whitespace
    """
    if not raw:
        return ""
    m = _UNIFIED_DIFF_START_RE.search(raw)
    if m:
        return raw[m.start():].strip()

    m2 = _UNIFIED_DIFF_HEADER_RE.search(raw)
    if m2:
        return raw[m2.start():].strip()

    return ""


@dataclass(frozen=True)
class LLMClient:
    api_key: str
    model: str
    base_url: str
    timeout_s: int = 60

    @staticmethod
    def from_env() -> "LLMClient":
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        model = os.environ.get("LLM_MODEL", "").strip() or "gpt-4.1-mini"
        base_url = os.environ.get("LLM_BASE_URL", "").strip() or "https://api.openai.com/v1/chat/completions"
        timeout_s = int(os.environ.get("LLM_TIMEOUT_S", "60"))
        if not api_key:
            raise RuntimeError("LLM_API_KEY is required")
        return LLMClient(api_key=api_key, model=model, base_url=base_url, timeout_s=timeout_s)

    def complete(
        self,
        *,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        """
        OpenAI-compatible chat.completions request.

        Expected response shapes supported:
        - {"choices":[{"message":{"content":"..."}}]}
        - {"choices":[{"text":"..."}]}
        """
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "temperature": temperature if temperature is not None else 0.2,
            "messages": [
                {"role": "system", "content": "You are a code repair model. Output only unified diffs."},
                {"role": "user", "content": prompt},
            ],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.base_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # If a gateway returns plain text, just pass it through.
            return raw

        # Common OpenAI-ish shapes
        choices = obj.get("choices")
        if isinstance(choices, list) and choices:
            c0 = choices[0]
            if isinstance(c0, dict):
                msg = c0.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    return msg["content"]
                if isinstance(c0.get("text"), str):
                    return c0["text"]

        # Fallback: try "output_text" (some gateways)
        if isinstance(obj.get("output_text"), str):
            return obj["output_text"]

        # Last resort: return json as text for debugging
        return raw
