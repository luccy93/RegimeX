"""
RegimeX API — Centralized Structured Logging
============================================
Configures Python standard logging to support structured JSON or human-readable text
output with security sanitization (masking credentials, tokens, and secrets).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Sensitive field patterns that must be masked in log records
SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|api_key|authorization|bearer|cookie|key)",
    re.IGNORECASE,
)
URL_PASSWORD_PATTERN = re.compile(r"://([^:]+):([^@]+)@")


def mask_sensitive_value(value: object) -> object:
    """Recursively mask sensitive values in dicts, lists, or strings."""
    if isinstance(value, str):
        # Mask embedded database connection credentials
        if "://" in value and "@" in value:
            try:
                from urllib.parse import urlsplit, urlunsplit

                parts = urlsplit(value)
                if parts.password:
                    netloc = f"{parts.username or ''}:***@{parts.hostname or ''}"
                    if parts.port:
                        netloc += f":{parts.port}"
                    return urlunsplit(
                        (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
                    )
            except (ValueError, AttributeError) as err:
                logger.debug("Failed parsing URL for masking: %s", err)
            return URL_PASSWORD_PATTERN.sub(r"://\1:***@", value)
        return value
    if isinstance(value, dict):
        masked: dict[str, object] = {}
        for k, v in value.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                masked[k] = "***"
            else:
                masked[k] = mask_sensitive_value(v)
        return masked
    if isinstance(value, (list, tuple)):
        return [mask_sensitive_value(v) for v in value]
    return value


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production container environments.

    Outputs single-line JSON log events to stdout/stderr for log aggregators
    (Fluentd, Datadog, CloudWatch, Loki) without polluting logs with credentials.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_value(record.getMessage()),
        }

        # Include standard exception information if present
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)

        # Include custom extra fields passed to logger calls
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                if SENSITIVE_KEY_PATTERN.search(key):
                    log_entry[key] = "***"
                else:
                    log_entry[key] = mask_sensitive_value(value)

        return json.dumps(log_entry, default=str)


def configure_logging(settings: Settings) -> None:
    """
    Configure application-wide logging handlers, levels, and formatters.

    Ensures consistent stdout delivery and adheres to the configured log_format
    ('json' for production or 'text' for development).
    """
    root_logger = logging.getLogger()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if called multiple times (e.g. in test suites)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)

    if settings.log_format == "json":
        stream_handler.setFormatter(JSONFormatter())
    else:
        text_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        stream_handler.setFormatter(logging.Formatter(text_format))

    root_logger.addHandler(stream_handler)
