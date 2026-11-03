"""OpenRouter adapters; API keys are supplied only at construction time."""

from dataclasses import dataclass
import json
import os
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.application.ports import DecisionChoice


class OpenRouterError(RuntimeError):
    """A provider response could not be used safely."""


@dataclass(frozen=True, slots=True)
class OpenRouterClients:
    """Separately scoped OpenRouter clients assembled from environment variables."""

    decision: "OpenRouterDecisionClient"
    text: "OpenRouterTextClient"


@dataclass(frozen=True, slots=True)
class OpenRouterDecisionClient:
    api_key: str
    model: str = "respan/span-01-lite:free"
    endpoint: str = "https://openrouter.ai/api/alpha/decisions"

    def choose(self, *, state: str, question: str, criteria: Mapping[str, str]) -> DecisionChoice:
        body = {
            "model": self.model,
            "state": state,
            "questions": {"intent": {"type": "choice", "instructions": question, "criteria": dict(criteria)}},
        }
        payload = _post_json(self.endpoint, self.api_key, body)
        answer = payload.get("answers", {}).get("intent", {})
        choice, probabilities = answer.get("choice"), answer.get("probabilities")
        if not isinstance(choice, str) or not isinstance(probabilities, dict):
            raise OpenRouterError("decision response did not include a valid choice")
        return DecisionChoice(choice=choice, probabilities={key: float(value) for key, value in probabilities.items()})


@dataclass(frozen=True, slots=True)
class OpenRouterEmbeddingClient:
    """Semantic embedding adapter, configured explicitly by the composition root."""

    api_key: str
    model: str = "openai/text-embedding-3-small"
    endpoint: str = "https://openrouter.ai/api/v1/embeddings"

    def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        if not texts:
            return []
        payload = _post_json(self.endpoint, self.api_key, {"model": self.model, "input": texts})
        records = payload.get("data")
        if not isinstance(records, list) or len(records) != len(texts):
            raise OpenRouterError("embedding response did not include one vector per input")
        vectors: list[tuple[float, ...]] = []
        for record in sorted(records, key=lambda item: item.get("index", -1) if isinstance(item, dict) else -1):
            embedding = record.get("embedding") if isinstance(record, dict) else None
            if not isinstance(embedding, list) or not embedding or not all(isinstance(value, (int, float)) for value in embedding):
                raise OpenRouterError("embedding response contained an invalid vector")
            vectors.append(tuple(float(value) for value in embedding))
        return vectors


@dataclass(frozen=True, slots=True)
class OpenRouterTextClient:
    api_key: str
    model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = _post_json(self.endpoint, self.api_key, {"model": self.model, "temperature": 0, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]})
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OpenRouterError("text response did not include message content") from error
        if not isinstance(content, str):
            raise OpenRouterError("text response content was not a string")
        return content


def clients_from_environment() -> OpenRouterClients:
    """Build real clients only when both separately scoped API keys are configured."""
    decision_key = os.environ.get("OPENROUTER_DECISION_API_KEY")
    text_key = os.environ.get("OPENROUTER_TEXT_API_KEY")
    if not decision_key or not text_key:
        raise ValueError("OPENROUTER_DECISION_API_KEY and OPENROUTER_TEXT_API_KEY are required")
    return OpenRouterClients(
        decision=OpenRouterDecisionClient(api_key=decision_key),
        text=OpenRouterTextClient(api_key=text_key),
    )


def _post_json(endpoint: str, api_key: str, body: Mapping[str, object]) -> dict:
    if not api_key:
        raise ValueError("OpenRouter API key is required")
    request = Request(endpoint, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OpenRouterError("OpenRouter request failed") from error
    if not isinstance(payload, dict):
        raise OpenRouterError("OpenRouter response was not an object")
    return payload
