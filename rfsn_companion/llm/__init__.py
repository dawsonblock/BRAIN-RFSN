# rfsn_companion/llm/__init__.py
from .deepseek_client import call_deepseek, generate_patch_from_context, LLMResponse

__all__ = ["call_deepseek", "generate_patch_from_context", "LLMResponse"]
