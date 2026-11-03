"""Application ports and compatibility exports for use cases.

Ports are owned by the domain and are re-exported here temporarily to keep imports
stable while use cases are introduced.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol

from src.domain.repositories import (
    CustomerRepository,
    OrderRepository,
    ProductRepository,
    PromotionRepository,
    RateLimitRepository,
    SessionRepository,
)


@dataclass(frozen=True, slots=True)
class DecisionChoice:
    """A bounded classification choice returned by a decision provider."""

    choice: str
    probabilities: Mapping[str, float]


class DecisionClient(Protocol):
    """External calibrated classifier used only for ambiguous routing."""

    def choose(self, *, state: str, question: str, criteria: Mapping[str, str]) -> DecisionChoice: ...


class TextClient(Protocol):
    """External text generator used only after evidence collection."""

    def generate(self, *, system_prompt: str, user_prompt: str) -> str: ...


__all__ = [
    "CustomerRepository", "DecisionChoice", "DecisionClient", "OrderRepository", "ProductRepository", "PromotionRepository", "RateLimitRepository", "SessionRepository", "TextClient",
]
