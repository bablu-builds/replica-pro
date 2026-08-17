
"""Structured logging with automatic secret redaction."""
import logging
import re
from typing import Any

import structlog


# Patterns that commonly indicate secrets
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)[\"\']?[a-zA-Z0-9_\-]{20,}[\"\']?", re.I),
    re.compile(r"(token\s*[:=]\s*)[\"\']?[a-zA-Z0-9_\-]{20,}[\"\']?", re.I),
    re.compile(r"(authorization\s*[:=]\s*)[\"\']?\S+[\"\']?", re.I),
    re.compile(r"(bearer\s+)\S+", re.I),
    re.compile(r"(connect\.sid\s*[:=]\s*)\S+", re.I),
    re.compile(r"(password\s*[:=]\s*)\S+", re.I),
    re.compile(r"(secret\s*[:=]\s*)\S+", re.I),
]

# Known secret key names to redact from dicts
SECRET_KEY_NAMES = {
    "api_key", "token", "auth_token", "access_token", "refresh_token",
    "password", "secret", "connect_sid", "cookie", "authorization",
    "github_token", "llm_api_key", "key",
}

REDACTED = "***REDACTED***"


class RedactingProcessor:
    """structlog processor that redacts secrets from log messages and event dicts."""

    def __init__(self, known_secrets: set[str] | None = None):
        self._known: set[str] = known_secrets or set()

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        event_dict = self._redact_dict(event_dict)
        if "event" in event_dict and isinstance(event_dict["event"], str):
            event_dict["event"] = self._redact_str(event_dict["event"])
        return event_dict

    def _redact_str(self, text: str) -> str:
        for pattern in SECRET_PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + REDACTED, text)
        for secret in self._known:
            if secret and len(secret) > 3:
                text = text.replace(secret, REDACTED)
        return text

    def _redact_dict(self, d: Any) -> Any:
        if isinstance(d, dict):
            return {
                k: REDACTED if self._is_secret_key(k) else self._redact_dict(v)
                for k, v in d.items()
            }
        if isinstance(d, list):
            return [self._redact_dict(item) for item in d]
        if isinstance(d, str):
            return self._redact_str(d)
        return d

    def _is_secret_key(self, key: str) -> bool:
        lowered = key.lower().replace("-", "_")
        return any(name in lowered for name in SECRET_KEY_NAMES)


def setup_logging(log_level: str = "INFO", redact: bool = True, known_secrets: set[str] | None = None) -> None:
    """Configure structured logging with optional redaction."""
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if redact:
        processors.append(RedactingProcessor(known_secrets=known_secrets))
    processors.extend([
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "rmao") -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
