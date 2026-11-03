import pytest

from src.application.privacy import minimize_evidence, redact_text
from src.infrastructure.llm import OpenRouterEmbeddingClient, clients_from_environment


def test_provider_bound_data_is_minimized_and_redacted() -> None:
    assert redact_text("Ligue para (67) 99812-3456 ou ana@example.com") == "Ligue para [phone redacted] ou [email redacted]"
    assert minimize_evidence({"customer_id": 12, "phone": "(67) 99812-3456", "product": "Violão"}) == {"product": "Violão"}


def test_openrouter_clients_require_separate_environment_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_DECISION_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_TEXT_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER"):
        clients_from_environment()


def test_openrouter_clients_read_keys_only_when_explicitly_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_DECISION_API_KEY", "decision-key")
    monkeypatch.setenv("OPENROUTER_TEXT_API_KEY", "text-key")

    clients = clients_from_environment()

    assert clients.decision.api_key == "decision-key"
    assert clients.text.api_key == "text-key"


def test_embedding_adapter_validates_provider_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.infrastructure.llm.openrouter._post_json",
        lambda *_args: {"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]},
    )

    vectors = OpenRouterEmbeddingClient(api_key="embedding-key").embed(["primeiro", "segundo"])

    assert vectors == [(1.0, 0.0), (0.0, 1.0)]
