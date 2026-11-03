"""Local, version-filtered retrieval for policy manuals.

The index is intentionally dependency-light: collections are JSON files named
``policy_<version>.json``.  This keeps policy publishing reproducible while
leaving a single adapter boundary for a future vector store.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from src.application.policies.ports import EmbeddingClient, VectorRecord
from src.domain import Source, ToolResult, ToolStatus


_SECTION = re.compile(r"(?m)^\s*(\d+(?:\.\d+)?)\.?\s+")
_TERM = re.compile(r"[\wÀ-ÿ]{3,}", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    policy_version: str
    document_id: str
    section: str | None
    page: int
    chunk_id: str
    text: str


class DeterministicHashEmbeddingClient:
    """Offline embedding adapter for tests and local development only.

    Production composition should inject a semantic embedding provider through
    ``EmbeddingClient``; this deterministic adapter keeps the test suite free
    of model downloads and network access.
    """

    def __init__(self, dimension: int = 128) -> None:
        if dimension < 8:
            raise ValueError("embedding dimension must be at least 8")
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self._dimension
            for term in _terms(text):
                vector[hash(term) % self._dimension] += 1.0
            magnitude = math.sqrt(sum(value * value for value in vector))
            vectors.append(tuple(value / magnitude for value in vector) if magnitude else tuple(vector))
        return vectors


class FilePolicyIndex:
    """A version-isolated vector store backed by local JSON collections.

    It is a small, deterministic adapter; callers depend only on the policy
    ports, so a Chroma, Qdrant or pgvector adapter can replace it unchanged.
    """

    def __init__(self, root: Path, embeddings: EmbeddingClient, *, relevance_threshold: float = 0.35) -> None:
        self._root = root
        self._embeddings = embeddings
        self._threshold = relevance_threshold

    def index(self, *, policy_version: str, document: Path, document_id: str) -> int:
        chunks = _chunks_from_pdf(document, policy_version, document_id)
        if not chunks:
            raise ValueError("Policy manual did not yield any indexable chunks")
        embeddings = self._embeddings.embed([chunk.text for chunk in chunks])
        if len(embeddings) != len(chunks) or any(not vector for vector in embeddings):
            raise ValueError("Embedding client returned an invalid vector batch")
        records = [VectorRecord(chunk.policy_version, chunk.document_id, chunk.section, chunk.page, chunk.chunk_id, chunk.text, vector) for chunk, vector in zip(chunks, embeddings, strict=True)]
        self.replace(policy_version, records)
        return len(records)

    def replace(self, policy_version: str, records: list[VectorRecord]) -> None:
        if not records or any(record.policy_version != policy_version for record in records):
            raise ValueError("A vector collection must contain only its policy version")
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._path(policy_version)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)

    def delete(self, policy_version: str) -> None:
        self._path(policy_version).unlink(missing_ok=True)

    def count(self, policy_version: str) -> int:
        return len(self._read(policy_version))

    def sections(self, policy_version: str) -> set[str]:
        return {chunk.section for chunk in self._read(policy_version) if chunk.section is not None}

    def document_sections(self, document: Path) -> set[str]:
        """Inspect a manual before publishing, without changing an index."""
        return {match.group(1) for page in _pdf_pages(document) for match in _SECTION.finditer(page)}

    def retrieve(self, query: str, *, policy_version: str, limit: int = 3) -> ToolResult:
        if limit < 1:
            raise ValueError("limit must be positive")
        vectors = self._embeddings.embed([query])
        if len(vectors) != 1 or not vectors[0]:
            return ToolResult(status=ToolStatus.INSUFFICIENT_EVIDENCE, message="The query could not be embedded.")
        ranked = self.search(policy_version, vectors[0], limit)
        if not ranked:
            return ToolResult(status=ToolStatus.INSUFFICIENT_EVIDENCE, message="No policy passage met the relevance threshold.")
        selected = ranked[:limit]
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=[{"text": record.text, "score": score, "policy_version": record.policy_version} for score, record in selected],
            sources=tuple(Source(source=record.document_id, page=record.page, section=record.section, chunk_id=record.chunk_id) for _, record in selected),
        )

    def search(self, policy_version: str, embedding: tuple[float, ...], limit: int) -> list[tuple[float, VectorRecord]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        ranked = [(score, record) for record in self._read(policy_version) if (score := _cosine(embedding, record.embedding)) >= self._threshold]
        return sorted(ranked, key=lambda item: (-item[0], item[1].page, item[1].chunk_id))[:limit]

    def _read(self, policy_version: str) -> list[VectorRecord]:
        path = self._path(policy_version)
        if not path.is_file():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = [VectorRecord(**{**entry, "embedding": tuple(entry["embedding"])}) for entry in raw]
        if any(record.policy_version != policy_version for record in records):
            raise ValueError("Policy index contains chunks from another version")
        return records

    def _path(self, policy_version: str) -> Path:
        safe_version = re.sub(r"[^A-Za-z0-9._-]", "_", policy_version)
        return self._root / f"policy_{safe_version}.json"


def _chunks_from_pdf(document: Path, policy_version: str, document_id: str) -> list[PolicyChunk]:
    pages = _pdf_pages(document)
    chunks: list[PolicyChunk] = []
    previous_section: str | None = None
    for page, text in enumerate(pages, 1):
        matches = list(_SECTION.finditer(text))
        if not matches:
            normalized = " ".join(text.split())
            if normalized:
                chunks.append(PolicyChunk(policy_version, document_id, previous_section, page, f"{policy_version}-p{page}-0", normalized))
            continue
        for position, match in enumerate(matches):
            end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
            section = match.group(1)
            normalized = " ".join(text[match.start():end].split())
            if normalized:
                chunks.append(PolicyChunk(policy_version, document_id, section, page, f"{policy_version}-p{page}-{position + 1}", normalized))
            previous_section = section
    return chunks


def _pdf_pages(document: Path) -> list[str]:
    try:
        process = subprocess.run(["pdftotext", "-layout", str(document), "-"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("pdftotext is required to index policy manuals") from error
    return process.stdout.split("\f")


def _terms(value: str) -> list[str]:
    return [term.casefold() for term in _TERM.findall(value)]


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions do not match")
    return sum(a * b for a, b in zip(left, right, strict=True))
