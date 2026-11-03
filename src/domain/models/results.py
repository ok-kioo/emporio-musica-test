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
    """Referência auditável a um registro ou trecho consultado."""

    source: str
    record_id: str | int | None = None
    page: int | None = None
    section: str | None = None
    chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.page is not None and self.page < 1:
            raise ValueError("page deve ser maior ou igual a 1")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Envelope comum para sucesso, ausência, ambiguidade e falha."""

    status: ToolStatus
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    sources: tuple[Source, ...] = ()
    message: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Fatos e fontes autorizados para a geração de uma resposta."""

    intent: str
    access_level: int
    facts: dict[str, Any] = field(default_factory=dict)
    sources: tuple[Source, ...] = ()
    escalation: str | None = None

    def __post_init__(self) -> None:
        if self.access_level not in (0, 1, 2):
            raise ValueError("access_level deve estar entre 0 e 2")
