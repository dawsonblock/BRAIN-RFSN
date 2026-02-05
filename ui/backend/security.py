# FILE: ui/backend/security.py
"""Security utilities for path confinement."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def is_path_confined(base_dir: str, target_path: str) -> bool:
    """
    Check if target_path is safely confined within base_dir.
    Resolves symlinks and prevents directory traversal attacks.
    
    Returns True if target_path is within base_dir, False otherwise.
    """
    try:
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(os.path.join(base_dir, target_path))
        
        # Ensure target starts with base (plus separator or is exact match)
        return (
            target_real == base_real or
            target_real.startswith(base_real + os.sep)
        )
    except (OSError, ValueError):
        return False


def safe_join(base_dir: str, *paths: str) -> Optional[str]:
    """
    Safely join paths, returning None if the result escapes base_dir.
    """
    joined = os.path.join(base_dir, *paths)
    if is_path_confined(base_dir, os.path.relpath(joined, base_dir)):
        return os.path.realpath(joined)
    return None


def validate_run_id(run_id: str) -> bool:
    """
    Validate run_id to prevent path traversal.
    Only alphanumeric, hyphens, and underscores allowed.
    """
    if not run_id:
        return False
    return all(c.isalnum() or c in '-_' for c in run_id)


class ConfinementError(Exception):
    """Raised when a path escapes its confinement."""
    pass
