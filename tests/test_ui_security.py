# tests/test_ui_security.py
"""Comprehensive security tests for UI backend."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Add ui directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))

from backend.security import (
    is_path_confined,
    safe_join,
    validate_run_id,
    sanitize_log_type,
    sanitize_model_name,
    sanitize_path_query,
    is_safe_to_view,
    RateLimiter,
    audit_log,
)


class TestPathConfinement:
    """Test path confinement security."""
    
    def test_normal_paths_allowed(self):
        """Normal relative paths should be allowed."""
        assert is_path_confined("/base", "sub/file.txt")
        assert is_path_confined("/base", "file.txt")
        assert is_path_confined("/base", "a/b/c/d.txt")
    
    def test_traversal_rejected(self):
        """Directory traversal attempts should be rejected."""
        assert not is_path_confined("/base", "../other")
        assert not is_path_confined("/base", "sub/../../../etc/passwd")
        assert not is_path_confined("/base", "..")
    
    def test_null_byte_rejected(self):
        """Null byte injection should be rejected."""
        assert not is_path_confined("/base", "file.txt\x00.jpg")
        assert not is_path_confined("/base\x00/evil", "file.txt")
    
    def test_overly_long_paths_rejected(self):
        """Overly long paths should be rejected."""
        long_path = "a" * 5000
        assert not is_path_confined("/base", long_path)
    
    def test_long_component_rejected(self):
        """Overly long path components should be rejected."""
        long_component = "a" * 300
        assert not is_path_confined("/base", long_component)
    
    def test_symlink_escape_rejected(self):
        """Symlink escape attempts should be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "base"
            base.mkdir()
            
            outside = Path(tmpdir) / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text("secret")
            
            # Create symlink pointing outside
            symlink = base / "escape"
            symlink.symlink_to(outside)
            
            # Should reject
            assert not is_path_confined(str(base), "escape/secret.txt")


class TestSafeJoin:
    """Test safe path joining."""
    
    def test_safe_join_normal(self):
        """Normal paths should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = safe_join(tmpdir, "sub", "file.txt")
            assert result is not None
            # Handle macOS /private prefix
            assert os.path.realpath(tmpdir) in result
    
    def test_safe_join_rejects_absolute(self):
        """Absolute paths in components should be rejected."""
        assert safe_join("/base", "/etc/passwd") is None
        assert safe_join("/base", "sub", "/abs") is None
    
    def test_safe_join_rejects_traversal(self):
        """Traversal in components should be rejected."""
        assert safe_join("/base", "..") is None
        assert safe_join("/base", "sub", "..", "..", "other") is None
    
    def test_safe_join_empty(self):
        """Empty paths should return None."""
        assert safe_join("/base") is None


class TestRunIdValidation:
    """Test run ID validation."""
    
    def test_valid_run_ids(self):
        """Valid run IDs should pass."""
        assert validate_run_id("run_20240215_143022_a1b2c3d4")
        assert validate_run_id("run_20230101_000000_00000000")
        assert validate_run_id("run_20251231_235959_ffffffff")
    
    def test_invalid_run_ids(self):
        """Invalid run IDs should fail."""
        assert not validate_run_id("")
        assert not validate_run_id(None)
        assert not validate_run_id("run_abc")
        assert not validate_run_id("../../../etc/passwd")
        assert not validate_run_id("run_20240215_143022_a1b2c3d4; rm -rf /")
        assert not validate_run_id("run_20240215_143022_ABCDEFGH")  # uppercase
        assert not validate_run_id("run_20240215_143022_a1b2c")  # too short (5 chars)
        assert not validate_run_id("notarunid")
    
    def test_injection_attempts(self):
        """Injection attempts should fail."""
        assert not validate_run_id("run_20240215_143022_a1b2c3d4\x00")
        assert not validate_run_id("run_$(id)_143022_a1b2c3d4")
        assert not validate_run_id("run_`id`_143022_a1b2c3d4")


class TestInputSanitization:
    """Test input sanitization functions."""
    
    def test_sanitize_log_type(self):
        """Log type sanitization."""
        assert sanitize_log_type("stdout") == "stdout"
        assert sanitize_log_type("stderr") == "stderr"
        assert sanitize_log_type("../passwd") == "stdout"
        assert sanitize_log_type("") == "stdout"
    
    def test_sanitize_model_name(self):
        """Model name sanitization."""
        assert sanitize_model_name("gpt-4") == "gpt-4"
        assert sanitize_model_name("claude-3-opus") == "claude-3-opus"
        assert sanitize_model_name("gpt-4; rm -rf /") == "gpt-4rm-rf"
        assert sanitize_model_name("") == "gpt-4"
        assert sanitize_model_name(None) == "gpt-4"
    
    def test_sanitize_path_query(self):
        """Path query sanitization."""
        assert sanitize_path_query("sub/file.txt") == "sub/file.txt"
        assert sanitize_path_query("/leading/slash") == "leading/slash"
        assert sanitize_path_query("double//slash") == "double/slash"
        assert sanitize_path_query("file\x00.txt") == "file.txt"
        assert sanitize_path_query("") == ""


class TestFileSafety:
    """Test file safety checks."""
    
    def test_safe_extensions(self):
        """Safe extensions should be allowed."""
        assert is_safe_to_view("file.txt")
        assert is_safe_to_view("file.log")
        assert is_safe_to_view("file.json")
        assert is_safe_to_view("file.py")
        assert is_safe_to_view("file.md")
    
    def test_dangerous_files_blocked(self):
        """Dangerous files should be blocked."""
        assert not is_safe_to_view(".env")
        assert not is_safe_to_view("id_rsa")
        assert not is_safe_to_view("id_rsa.pub")  # Contains the pattern
        assert not is_safe_to_view("credentials.json")
        assert not is_safe_to_view("secrets.yaml")
    
    def test_unknown_extensions_blocked(self):
        """Unknown extensions should be blocked."""
        assert not is_safe_to_view("file.exe")
        assert not is_safe_to_view("file.bin")
        assert not is_safe_to_view("file.so")


class TestRateLimiter:
    """Test rate limiting."""
    
    def test_allows_under_limit(self):
        """Requests under limit should be allowed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        for _ in range(10):
            assert limiter.is_allowed("test_key")
    
    def test_blocks_over_limit(self):
        """Requests over limit should be blocked."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            limiter.is_allowed("test_key")
        assert not limiter.is_allowed("test_key")
    
    def test_separate_keys(self):
        """Different keys should have separate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("key1")
        limiter.is_allowed("key1")
        assert not limiter.is_allowed("key1")
        assert limiter.is_allowed("key2")


class TestAuditLog:
    """Test security audit logging."""
    
    def test_logs_events(self):
        """Audit log should record events."""
        initial_count = len(audit_log._events)
        audit_log.log("TEST_EVENT", {"test": "data"})
        assert len(audit_log._events) == initial_count + 1
    
    def test_log_path_violation(self):
        """Path violation logging."""
        initial_count = len(audit_log._events)
        audit_log.log_path_violation("/bad/path", "/base")
        assert len(audit_log._events) == initial_count + 1
        assert audit_log._events[-1]['type'] == 'PATH_VIOLATION'
    
    def test_log_truncates_long_values(self):
        """Long values should be truncated in logs."""
        long_value = "x" * 500
        audit_log.log_invalid_input("field", long_value)
        logged_value = audit_log._events[-1]['details']['value']
        assert len(logged_value) <= 100
