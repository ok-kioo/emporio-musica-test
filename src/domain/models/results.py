"""Results and evidence for the domain layer."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolStatus(StrEnum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Source:
    """Auditable reference to a consulted record or document passage."""

    source: str
    record_id: str | int | None = None
    page: int | None = None
    section: str | None = None
    chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.page is not None and self.page < 1:
            raise ValueError("page must be at least 1")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Common envelope for successful, absent, ambiguous, and failed lookups."""

    status: ToolStatus
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    sources: tuple[Source, ...] = ()
    message: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Authorized facts and sources used to generate a response."""

    intent: str
    access_level: int
    facts: dict[str, Any] = field(default_factory=dict)
    sources: tuple[Source, ...] = ()
    escalation: str | None = None

    def __post_init__(self) -> None:
        if self.access_level not in (0, 1, 2):
            raise ValueError("access_level must be between 0 and 2")
