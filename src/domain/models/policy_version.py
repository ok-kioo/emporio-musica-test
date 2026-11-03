"""Versioned policy state owned by the domain."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    version: str
    is_active: bool = False
    activated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("policy version is required")
