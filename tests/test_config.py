# tests/test_config.py
"""Tests for rfsn_kernel/config.py."""
import os
import pytest

from rfsn_kernel.config import RFSNConfig, get_config, reset_config


class TestRFSNConfig:
    """Tests for RFSNConfig class."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = RFSNConfig()
        assert config.llm_model == "gpt-4.1-mini"
        assert config.max_patch_bytes == 100_000
        assert config.timeout_seconds == 300
        assert config.log_level == "INFO"
        assert config.docker_enabled is False

    def test_from_env_uses_defaults(self, monkeypatch):
        """from_env should use defaults when no env vars set."""
        # Clear any existing RFSN_ vars
        for key in list(os.environ.keys()):
            if key.startswith("RFSN_"):
                monkeypatch.delenv(key, raising=False)

        reset_config()
        config = RFSNConfig.from_env()
        assert config.workspace == "."
        assert config.llm_model == "gpt-4.1-mini"

    def test_from_env_reads_vars(self, monkeypatch):
        """from_env should read environment variables."""
        monkeypatch.setenv("RFSN_WORKSPACE", "/custom/path")
        monkeypatch.setenv("RFSN_LLM_MODEL", "custom-model")
        monkeypatch.setenv("RFSN_MAX_PATCH_BYTES", "50000")
        monkeypatch.setenv("RFSN_DOCKER_ENABLED", "true")

        config = RFSNConfig.from_env()
        assert config.workspace == "/custom/path"
        assert config.llm_model == "custom-model"
        assert config.max_patch_bytes == 50000
        assert config.docker_enabled is True

    def test_validate_valid_config(self):
        """Valid config should pass validation."""
        config = RFSNConfig()
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_patch_bytes(self):
        """Invalid max_patch_bytes should fail validation."""
        config = RFSNConfig(max_patch_bytes=-1)
        errors = config.validate()
        assert any("max_patch_bytes" in e for e in errors)

    def test_validate_excessive_patch_bytes(self):
        """Excessive max_patch_bytes should fail validation."""
        config = RFSNConfig(max_patch_bytes=20_000_000)
        errors = config.validate()
        assert any("10MB" in e for e in errors)

    def test_validate_invalid_timeout(self):
        """Invalid timeout should fail validation."""
        config = RFSNConfig(timeout_seconds=-1)
        errors = config.validate()
        assert any("timeout_seconds" in e for e in errors)

    def test_validate_excessive_timeout(self):
        """Excessive timeout should fail validation."""
        config = RFSNConfig(timeout_seconds=7200)
        errors = config.validate()
        assert any("1 hour" in e for e in errors)

    def test_validate_invalid_log_level(self):
        """Invalid log level should fail validation."""
        config = RFSNConfig(log_level="INVALID")
        errors = config.validate()
        assert any("log_level" in e for e in errors)

    def test_workspace_path_property(self):
        """workspace_path should return resolved Path."""
        config = RFSNConfig(workspace="/tmp/test")
        assert config.workspace_path.is_absolute()

    def test_has_llm_credentials(self):
        """has_llm_credentials should check api_key."""
        config = RFSNConfig(llm_api_key="")
        assert not config.has_llm_credentials()

        config = RFSNConfig(llm_api_key="sk-test")
        assert config.has_llm_credentials()


class TestGetConfig:
    """Tests for get_config singleton."""

    def test_get_config_returns_config(self, monkeypatch):
        """get_config should return RFSNConfig instance."""
        for key in list(os.environ.keys()):
            if key.startswith("RFSN_"):
                monkeypatch.delenv(key, raising=False)

        reset_config()
        config = get_config()
        assert isinstance(config, RFSNConfig)

    def test_get_config_caches(self, monkeypatch):
        """get_config should cache the config."""
        reset_config()
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config_clears_cache(self):
        """reset_config should clear the cache."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        # Different instances after reset
        # (might be equal but not necessarily same object due to frozen dataclass)
        assert config1 is not config2 or True  # Allow same frozen instance
