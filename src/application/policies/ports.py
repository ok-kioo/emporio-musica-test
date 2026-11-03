"""Ports for semantic policy retrieval, independent of vector vendors."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.domain import ToolResult


@dataclass(frozen=True, slots=True)
class VectorRecord:
    policy_version: str
    document_id: str
    section: str | None
    page: int
    chunk_id: str
    text: str
    embedding: tuple[float, ...]


class EmbeddingClient(Protocol):
    """Transforms text into vectors; provider choice stays in infrastructure."""

    def embed(self, texts: list[str]) -> list[tuple[float, ...]]: ...


class PolicyVectorStore(Protocol):
    """A collection per policy version, implementable by Chroma, Qdrant or pgvector."""

    def replace(self, policy_version: str, records: list[VectorRecord]) -> None: ...
    def delete(self, policy_version: str) -> None: ...
    def count(self, policy_version: str) -> int: ...
    def sections(self, policy_version: str) -> set[str]: ...
    def search(self, policy_version: str, embedding: tuple[float, ...], limit: int) -> list[tuple[float, VectorRecord]]: ...


class PolicyIndexer(Protocol):
    def index(self, *, policy_version: str, document: Path, document_id: str) -> int: ...
    def delete(self, policy_version: str) -> None: ...
    def count(self, policy_version: str) -> int: ...


class PolicyPublicationIndex(PolicyIndexer, Protocol):
    """Additional validation operations required during policy publication."""

    def sections(self, policy_version: str) -> set[str]: ...
    def document_sections(self, document: Path) -> set[str]: ...


class PolicyRetriever(Protocol):
    def retrieve(self, query: str, *, policy_version: str, limit: int = 3) -> ToolResult: ...
