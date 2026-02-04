# rfsn_kernel/tools/__init__.py
"""Extended tools for general intelligence capabilities."""

from .web import web_search, browse_url
from .shell import shell_exec
from .memory import remember, recall

__all__ = ["web_search", "browse_url", "shell_exec", "remember", "recall"]
