from pathlib import Path

from src.composition import build_policy_runtime
from src.config import PolicyRuntimeSettings


def test_composition_builds_an_offline_policy_runtime(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    settings = PolicyRuntimeSettings(
        database_url=f"sqlite:///{tmp_path / 'emporio.sqlite3'}",
        policy_root=project_root / "data" / "policies",
        vector_backend="file",
        vector_directory=tmp_path / "vectors",
        embedding_provider="hash",
        embedding_api_key=None,
    )

    runtime = build_policy_runtime(settings)

    assert runtime.publisher.publish("2.1") > 0
    assert runtime.registry.active() is not None
    assert runtime.registry.active().version == "2.1"
