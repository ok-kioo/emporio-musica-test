"""Optional Chroma implementation of the policy vector-store port."""

from pathlib import Path

from src.application.policies.ports import VectorRecord


class ChromaPolicyVectorStore:
    """One Chroma collection per policy version.

    Chroma is imported only when this adapter is selected, keeping the default
    test path and the core domain independent from the optional dependency.
    """

    def __init__(self, directory: Path) -> None:
        try:
            import chromadb
        except ImportError as error:
            raise RuntimeError('Install the "rag" extra to use ChromaPolicyVectorStore') from error
        self._client = chromadb.PersistentClient(path=str(directory))

    def replace(self, policy_version: str, records: list[VectorRecord]) -> None:
        if not records or any(record.policy_version != policy_version for record in records):
            raise ValueError("A vector collection must contain only its policy version")
        name = self._collection_name(policy_version)
        try:
            self._client.delete_collection(name)
        except ValueError:
            pass
        collection = self._client.create_collection(name=name, metadata={"policy_version": policy_version})
        collection.add(
            ids=[record.chunk_id for record in records],
            documents=[record.text for record in records],
            embeddings=[list(record.embedding) for record in records],
            metadatas=[{"policy_version": record.policy_version, "document_id": record.document_id, "section": record.section or "", "page": record.page} for record in records],
        )

    def delete(self, policy_version: str) -> None:
        try:
            self._client.delete_collection(self._collection_name(policy_version))
        except ValueError:
            pass

    def count(self, policy_version: str) -> int:
        try:
            return self._client.get_collection(self._collection_name(policy_version)).count()
        except ValueError:
            return 0

    def sections(self, policy_version: str) -> set[str]:
        try:
            payload = self._client.get_collection(self._collection_name(policy_version)).get(include=["metadatas"])
        except ValueError:
            return set()
        return {metadata["section"] for metadata in payload["metadatas"] if metadata and metadata.get("section")}

    def search(self, policy_version: str, embedding: tuple[float, ...], limit: int) -> list[tuple[float, VectorRecord]]:
        try:
            result = self._client.get_collection(self._collection_name(policy_version)).query(query_embeddings=[list(embedding)], n_results=limit, include=["documents", "metadatas", "distances"])
        except ValueError:
            return []
        records: list[tuple[float, VectorRecord]] = []
        for chunk_id, text, metadata, distance in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True):
            records.append((1.0 - float(distance), VectorRecord(policy_version, metadata["document_id"], metadata.get("section") or None, int(metadata["page"]), chunk_id, text, embedding)))
        return records

    @staticmethod
    def _collection_name(policy_version: str) -> str:
        return f"policy_{policy_version.replace('.', '_').replace('-', '_')}"
