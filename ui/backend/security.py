# FILE: ui/backend/security.py
"""
RFSN UI Security Module - Hardened

Defense-in-depth security with:
- Path confinement (symlink-aware)
- Input sanitization
- Rate limiting
- Strict validation
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict
from functools import wraps

from typing import Callable, Dict, Optional


# ============ Constants ============

# Maximum path component length
MAX_PATH_COMPONENT = 255

# Maximum total path length
MAX_PATH_LENGTH = 4096

# Maximum file size for inline display (1MB)
MAX_INLINE_FILE_SIZE = 1024 * 1024

# Allowed file extensions for viewing (whitelist)
ALLOWED_VIEW_EXTENSIONS = frozenset({
    '.txt', '.log', '.json', '.jsonl', '.md', '.py', '.yaml', '.yml', 
    '.toml', '.diff', '.patch', '.cfg', '.ini', '.conf', '.sh', '.bash',
    '.html', '.css', '.js', '.ts', '.tsx', '.jsx', '.xml', '.csv',
})

# Dangerous file patterns (blocklist)
DANGEROUS_PATTERNS = frozenset({
    '.env', '.git/config', 'id_rsa', 'id_ed25519', '.pem', '.key',
    'credentials', 'secrets', 'password', '.htpasswd', 'shadow',
})

# Run ID format: run_YYYYMMDD_HHMMSS_hexchars (variable length hex)
RUN_ID_PATTERN = re.compile(r'^run_\d{8}_\d{6}_[a-f0-9]{6,16}$')


# ============ Exceptions ============

class SecurityError(Exception):
    """Base class for security exceptions."""
    pass


class ConfinementError(SecurityError):
    """Raised when a path escapes its confinement."""
    pass


class ValidationError(SecurityError):
    """Raised when input validation fails."""
    pass


class RateLimitError(SecurityError):
    """Raised when rate limit is exceeded."""
    pass


# ============ Path Security ============

def is_path_confined(base_dir: str, target_path: str) -> bool:
    """
    Check if target_path is safely confined within base_dir.
    
    Security measures:
    1. Resolves ALL symlinks before comparison
    2. Prevents directory traversal via ../
    3. Rejects null bytes and other injection attempts
    4. Validates path component lengths
    
    Returns True if target_path is within base_dir, False otherwise.
    """
    try:
        # Reject null bytes (C-string terminator injection)
        if '\x00' in target_path or '\x00' in base_dir:
            return False
        
        # Reject overly long paths
        if len(target_path) > MAX_PATH_LENGTH or len(base_dir) > MAX_PATH_LENGTH:
            return False
        
        # Check individual component lengths
        for component in target_path.split(os.sep):
            if len(component) > MAX_PATH_COMPONENT:
                return False
        
        # Resolve to real paths (follows symlinks)
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(os.path.join(base_dir, target_path))
        
        # Ensure target starts with base (plus separator or is exact match)
        return (
            target_real == base_real or
            target_real.startswith(base_real + os.sep)
        )
    except (OSError, ValueError, TypeError):
        return False


def safe_join(base_dir: str, *paths: str) -> Optional[str]:
    """
    Safely join paths, returning None if the result escapes base_dir.
    
    Security measures:
    1. Rejects absolute paths in components
    2. Rejects paths with traversal sequences
    3. Resolves symlinks and verifies confinement
    """
    if not paths:
        return None
    
    for path in paths:
        if not path:
            continue
        
        # Reject absolute paths
        if os.path.isabs(path):
            return None
        
        # Reject explicit traversal attempts
        if '..' in path.split(os.sep):
            return None
    
    try:
        joined = os.path.join(base_dir, *paths)
        rel = os.path.relpath(joined, base_dir)
        
        if is_path_confined(base_dir, rel):
            return os.path.realpath(joined)
    except (OSError, ValueError, TypeError):
        pass
    
    return None


def is_safe_to_view(filename: str) -> bool:
    """
    Check if a file is safe to view based on extension and name.
    
    Returns False for sensitive files that should not be exposed.
    """
    lower_name = filename.lower()
    
    # Check against dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern in lower_name:
            return False
    
    # Check extension whitelist
    ext = os.path.splitext(lower_name)[1]
    if ext and ext not in ALLOWED_VIEW_EXTENSIONS:
        return False
    
    return True


# ============ Input Validation ============

def validate_run_id(run_id: str) -> bool:
    """
    Validate run_id format strictly.
    
    Expected format: run_YYYYMMDD_HHMMSS_8hexchars
    Example: run_20240215_143022_a1b2c3d4
    
    Security: Prevents path traversal and injection attacks.
    """
    if not run_id or not isinstance(run_id, str):
        return False
    
    # Length check: run_ + 8 + _ + 6 + _ + (6-16 hex) = 23-33 chars
    if len(run_id) < 23 or len(run_id) > 33:
        return False
    
    # Pattern match
    return bool(RUN_ID_PATTERN.match(run_id))


def sanitize_log_type(log_type: str) -> str:
    """
    Sanitize log type to prevent path injection.
    Only allows 'stdout' or 'stderr'.
    """
    if log_type == 'stderr':
        return 'stderr'
    return 'stdout'  # Default to stdout


def sanitize_model_name(model: str) -> str:
    """
    Sanitize model name for configuration.
    Only allows alphanumeric, hyphens, underscores, dots, and slashes.
    """
    if not model or not isinstance(model, str):
        return 'gpt-4'
    
    # Max 64 chars
    model = model[:64]
    
    # Strip dangerous characters
    sanitized = re.sub(r'[^a-zA-Z0-9._/-]', '', model)
    
    # Remove trailing slashes
    sanitized = sanitized.rstrip('/')
    
    return sanitized or 'gpt-4'


def sanitize_path_query(path: str) -> str:
    """
    Sanitize a path query parameter.
    Removes null bytes, normalizes separators, strips dangerous sequences.
    """
    if not path or not isinstance(path, str):
        return ''
    
    # Remove null bytes
    path = path.replace('\x00', '')
    
    # Normalize to forward slashes then back
    path = path.replace('\\', '/')
    
    # Remove double slashes
    while '//' in path:
        path = path.replace('//', '/')
    
    # Strip leading/trailing slashes
    path = path.strip('/')
    
    # Limit length
    path = path[:1024]
    
    return path


# ============ Rate Limiting ============

class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    NOT for production - use Redis or similar in production.
    This provides basic protection for local development.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean old requests
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def check(self, key: str) -> None:
        """Raise RateLimitError if rate limit exceeded."""
        if not self.is_allowed(key):
            raise RateLimitError(f"Rate limit exceeded for {key}")


# Global rate limiters
api_limiter = RateLimiter(max_requests=100, window_seconds=60)
file_limiter = RateLimiter(max_requests=50, window_seconds=60)


# ============ Token Security ============

def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage (not for comparison)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


# ============ Audit Logging ============

class SecurityAuditLog:
    """
    Security audit logger for tracking security-relevant events.
    
    In production, this should write to a secure, append-only log.
    """
    
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path
        self._events: list = []
    
    def log(self, event_type: str, details: Dict) -> None:
        """Log a security event."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details,
        }
        self._events.append(event)
        
        if self.log_path:
            import json
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
    
    def log_path_violation(self, attempted_path: str, base_dir: str) -> None:
        """Log a path confinement violation."""
        self.log('PATH_VIOLATION', {
            'attempted': attempted_path,
            'base': base_dir,
        })
    
    def log_rate_limit(self, key: str) -> None:
        """Log a rate limit hit."""
        self.log('RATE_LIMIT', {'key': key})
    
    def log_invalid_input(self, field: str, value: str) -> None:
        """Log invalid input attempt."""
        # Truncate value to prevent log injection
        safe_value = value[:100] if isinstance(value, str) else str(value)[:100]
        self.log('INVALID_INPUT', {'field': field, 'value': safe_value})


# Global audit log
audit_log = SecurityAuditLog()


# ============ Security Decorators ============

def require_rate_limit(limiter: RateLimiter, key_func: Callable = lambda: 'global'):
    """Decorator to enforce rate limiting on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func()
            if not limiter.is_allowed(key):
                audit_log.log_rate_limit(key)
                raise RateLimitError("Too many requests")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============ Summary ============

__all__ = [
    # Exceptions
    'SecurityError',
    'ConfinementError', 
    'ValidationError',
    'RateLimitError',
    # Path security
    'is_path_confined',
    'safe_join',
    'is_safe_to_view',
    # Validation
    'validate_run_id',
    'sanitize_log_type',
    'sanitize_model_name',
    'sanitize_path_query',
    # Rate limiting
    'RateLimiter',
    'api_limiter',
    'file_limiter',
    # Tokens
    'generate_csrf_token',
    'hash_api_key',
    'secure_compare',
    # Audit
    'SecurityAuditLog',
    'audit_log',
    # Constants
    'MAX_INLINE_FILE_SIZE',
    'ALLOWED_VIEW_EXTENSIONS',
]
