from pathlib import Path
from shutil import copytree

import pytest

from src.domain import ToolStatus
from src.infrastructure.database import SQLAlchemyPolicyVersionRegistryRepository, create_database_engine
from src.infrastructure.policies import PolicyPublisher
from src.infrastructure.retrieval import DeterministicHashEmbeddingClient, FilePolicyIndex


POLICIES = Path(__file__).parents[1] / "data" / "policies"


def _publisher(tmp_path: Path, policy_root: Path = POLICIES) -> tuple[PolicyPublisher, FilePolicyIndex, SQLAlchemyPolicyVersionRegistryRepository]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    index = FilePolicyIndex(tmp_path / "indexes", DeterministicHashEmbeddingClient(), relevance_threshold=0.1)
    registry = SQLAlchemyPolicyVersionRegistryRepository(create_database_engine(tmp_path / "policies.sqlite3"))
    return PolicyPublisher(policy_root, index, registry), index, registry


def test_publish_real_policy_indexes_and_activates_only_v21(tmp_path: Path) -> None:
    publisher, index, registry = _publisher(tmp_path)

    count = publisher.publish("2.1")
    result = index.retrieve("direito de arrependimento", policy_version="2.1")

    assert count > 0
    assert registry.active() is not None
    assert registry.active().version == "2.1"
    assert result.status is ToolStatus.SUCCESS
    assert result.sources
    assert all(item["policy_version"] == "2.1" for item in result.data or [])
    assert index.retrieve("arrependimento", policy_version="unknown").status is ToolStatus.INSUFFICIENT_EVIDENCE


def test_failed_publication_preserves_the_active_policy_pointer(tmp_path: Path) -> None:
    copied_root = tmp_path / "policies"
    copytree(POLICIES, copied_root)
    rules = copied_root / "v2.1" / "rules.yaml"
    rules.write_text(rules.read_text(encoding="utf-8").replace('section: "4.1"', 'section: "99.9"', 1), encoding="utf-8")
    publisher, _index, registry = _publisher(tmp_path / "runtime", copied_root)
    registry.activate("2.1")

    with pytest.raises(ValueError, match="absent from the manual"):
        publisher.publish("2.1")

    assert registry.active() is not None
    assert registry.active().version == "2.1"
