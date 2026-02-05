# rfsn_kernel/config.py
"""
Environment configuration with validation.

Uses pydantic-settings for validated environment variables.
All RFSN config can be overridden via RFSN_ prefixed env vars.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RFSNConfig:
    """
    Validated RFSN configuration.

    Environment variables (all optional, with defaults):
    - RFSN_WORKSPACE: Default workspace path
    - RFSN_LLM_MODEL: LLM model to use
    - RFSN_LLM_BASE_URL: LLM API base URL
    - RFSN_LLM_API_KEY: LLM API key (sensitive)
    - RFSN_MAX_PATCH_BYTES: Max patch size in bytes
    - RFSN_TIMEOUT_SECONDS: Default operation timeout
    - RFSN_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # Workspace
    workspace: str = "."

    # LLM settings
    llm_model: str = "gpt-4.1-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""

    # Safety limits
    max_patch_bytes: int = 100_000
    max_files_per_action: int = 50
    timeout_seconds: int = 300

    # Logging
    log_level: str = "INFO"

    # Docker sandbox
    docker_enabled: bool = False
    docker_image: str = "python:3.12-slim"
    docker_timeout: int = 120

    @classmethod
    def from_env(cls) -> "RFSNConfig":
        """Load configuration from environment variables."""
        return cls(
            workspace=os.getenv("RFSN_WORKSPACE", "."),
            llm_model=os.getenv("RFSN_LLM_MODEL", "gpt-4.1-mini"),
            llm_base_url=os.getenv("RFSN_LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=os.getenv("RFSN_LLM_API_KEY", ""),
            max_patch_bytes=int(os.getenv("RFSN_MAX_PATCH_BYTES", "100000")),
            max_files_per_action=int(os.getenv("RFSN_MAX_FILES_PER_ACTION", "50")),
            timeout_seconds=int(os.getenv("RFSN_TIMEOUT_SECONDS", "300")),
            log_level=os.getenv("RFSN_LOG_LEVEL", "INFO"),
            docker_enabled=os.getenv("RFSN_DOCKER_ENABLED", "").lower() in ("1", "true", "yes"),
            docker_image=os.getenv("RFSN_DOCKER_IMAGE", "python:3.12-slim"),
            docker_timeout=int(os.getenv("RFSN_DOCKER_TIMEOUT", "120")),
        )

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors: list[str] = []

        if self.max_patch_bytes <= 0:
            errors.append("max_patch_bytes must be positive")
        if self.max_patch_bytes > 10_000_000:
            errors.append("max_patch_bytes exceeds 10MB limit")

        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")
        if self.timeout_seconds > 3600:
            errors.append("timeout_seconds exceeds 1 hour limit")

        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            errors.append(f"Invalid log_level: {self.log_level}")

        return errors

    @property
    def workspace_path(self) -> Path:
        """Get workspace as Path object."""
        return Path(self.workspace).resolve()

    def has_llm_credentials(self) -> bool:
        """Check if LLM credentials are configured."""
        return bool(self.llm_api_key)


# Global singleton (lazy loaded)
_config: Optional[RFSNConfig] = None


def get_config() -> RFSNConfig:
    """Get the global configuration, loading from env if needed."""
    global _config
    if _config is None:
        _config = RFSNConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None
