"""Validation for a versioned policy package manifest."""

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel


class PolicyManifest(BaseModel):
    policy_version: str
    effective_from: date
    document: str
    synthetic: bool = False


def load_manifest(policy_directory: Path) -> PolicyManifest:
    """Load a package manifest and ensure its referenced manual exists."""
    manifest_path = policy_directory / "manifest.yaml"
    with manifest_path.open(encoding="utf-8") as source:
        manifest = PolicyManifest.model_validate(yaml.safe_load(source))
    document = policy_directory / manifest.document
    if not document.is_file():
        raise ValueError(f"Policy manual was not found: {document}")
    return manifest
