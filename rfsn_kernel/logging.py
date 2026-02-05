# rfsn_kernel/logging.py
"""
Structured logging for the RFSN kernel.

Provides consistent, JSON-formatted logging for all kernel operations.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def get_logger(name: str, structured: bool = True) -> logging.Logger:
    """
    Get a logger configured for RFSN.

    Args:
        name: Logger name (usually __name__)
        structured: If True, use JSON format; if False, use plain text

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stderr)

    if structured:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


class LogContext:
    """Context manager for adding fields to log messages."""

    def __init__(self, logger: logging.Logger, **fields: Any):
        self.logger = logger
        self.fields = fields
        self._old_factory = None

    def __enter__(self):
        old_factory = logging.getLogRecordFactory()
        fields = self.fields

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.extra = getattr(record, "extra", {})
            record.extra.update(fields)
            return record

        self._old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, *args):
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)


# Convenience functions for common log patterns
def log_gate_decision(
    logger: logging.Logger,
    allowed: bool,
    action_type: str,
    reason: str,
    workspace: str = "",
):
    """Log a gate decision."""
    logger.info(
        f"Gate decision: {'ALLOW' if allowed else 'DENY'} {action_type}",
        extra={
            "event": "gate_decision",
            "allowed": allowed,
            "action_type": action_type,
            "reason": reason,
            "workspace": workspace,
        },
    )


def log_action_execution(
    logger: logging.Logger,
    action_type: str,
    success: bool,
    duration_ms: float,
    workspace: str = "",
):
    """Log an action execution."""
    logger.info(
        f"Action executed: {action_type} {'OK' if success else 'FAILED'}",
        extra={
            "event": "action_execution",
            "action_type": action_type,
            "success": success,
            "duration_ms": duration_ms,
            "workspace": workspace,
        },
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    details: dict[str, Any],
    severity: str = "warning",
):
    """Log a security-relevant event."""
    level = getattr(logging, severity.upper(), logging.WARNING)
    logger.log(
        level,
        f"Security event: {event_type}",
        extra={
            "event": "security",
            "event_type": event_type,
            "details": details,
        },
    )
