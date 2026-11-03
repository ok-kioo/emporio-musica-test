"""Deterministic LLM test doubles that never make network calls."""

from dataclasses import dataclass
from typing import Mapping

from src.application.ports import DecisionChoice


@dataclass(frozen=True, slots=True)
class FakeDecisionClient:
    response: DecisionChoice

    def choose(self, *, state: str, question: str, criteria: Mapping[str, str]) -> DecisionChoice:
        del state, question, criteria
        return self.response


@dataclass(frozen=True, slots=True)
class FakeTextClient:
    response: str

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        return self.response
