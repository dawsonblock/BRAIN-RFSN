# rfsn_companion/tools/__init__.py
"""
Upstream tools - NOT in kernel scope.

These tools (web, memory, shell) are for companion/proposer use ONLY.
They should NEVER be called from rfsn_kernel/*.
"""
from .web import web_search, browse_url
from .memory import remember, recall
from .shell import shell_exec

__all__ = ["web_search", "browse_url", "remember", "recall", "shell_exec"]
