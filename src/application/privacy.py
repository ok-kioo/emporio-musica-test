"""Data minimization for external model providers."""

import re
from typing import Any


_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?:\+?\d{1,3}\s*)?\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}")
_SENSITIVE_KEYS = {"phone", "email", "customer_id", "channel_phone", "address"}


def redact_text(value: str) -> str:
    """Remove common direct identifiers before a provider call."""
    return _PHONE.sub("[phone redacted]", _EMAIL.sub("[email redacted]", value))


def minimize_evidence(value: Any) -> Any:
    """Recursively remove direct identifiers from a provider-bound evidence payload."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: minimize_evidence(item) for key, item in value.items() if key not in _SENSITIVE_KEYS}
    if isinstance(value, (list, tuple)):
        return [minimize_evidence(item) for item in value]
    return value
