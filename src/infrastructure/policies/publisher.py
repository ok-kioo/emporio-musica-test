"""Atomic publication of a validated, versioned policy package."""

from pathlib import Path

from src.application.policies.ports import PolicyPublicationIndex
from src.domain.repositories import PolicyVersionRegistryRepository
from src.infrastructure.policies.manifest import load_manifest
from src.infrastructure.policies.rules_loader import load_ruleset


class PolicyPublisher:
    """Validate and index a package before atomically changing the active pointer."""

    def __init__(self, policy_root: Path, index: PolicyPublicationIndex, registry: PolicyVersionRegistryRepository) -> None:
        self._policy_root = policy_root
        self._index = index
        self._registry = registry

    def publish(self, version: str) -> int:
        directory = self._policy_root / f"v{version}"
        manifest = load_manifest(directory)
        if manifest.policy_version != version:
            raise ValueError("Manifest version does not match the requested publication version")
        rules_version, rules = load_ruleset(directory / "rules.yaml")
        if rules_version != version:
            raise ValueError("Rules version does not match the manifest")
        document = directory / manifest.document
        missing_sections = sorted({rule.section for rule in rules.values()} - self._index.document_sections(document))
        if missing_sections:
            raise ValueError(f"Rules cite sections absent from the manual: {', '.join(missing_sections)}")

        # FilePolicyIndex writes the new collection through an atomic replacement.
        # The pointer only changes after all validation and indexing succeed.
        count = self._index.index(policy_version=version, document=document, document_id=manifest.document)
        if count < 1 or not self._index.sections(version):
            self._index.delete(version)
            raise ValueError("Policy index validation failed")
        self._registry.activate(version)
        return count

    def rollback(self) -> str | None:
        """Return the activated version, if there is a prior published version."""
        version = self._registry.rollback()
        return version.version if version else None
