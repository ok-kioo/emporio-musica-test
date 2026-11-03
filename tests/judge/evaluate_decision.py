#!/usr/bin/env python3
"""Compare routing implementations against the local golden set.

This script deliberately uses a deterministic stand-in for the provider, so it
is safe to run without API keys or network access.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import yaml

from src.application.decisions import CompositeDecisionModel, ConversationContext, LLMDecisionModel, RulesDecisionModel
from src.application.ports import DecisionChoice


@dataclass(frozen=True, slots=True)
class GoldenSetClient:
    """Deterministic substitute for the bounded decision provider."""

    expected_intent: str

    def choose(self, **_kwargs: object) -> DecisionChoice:
        return DecisionChoice(self.expected_intent, {self.expected_intent: 1.0})


def evaluate(cases: list[dict[str, str]]) -> list[dict[str, float | int | str]]:
    model_factories = {
        "rules": lambda expected: RulesDecisionModel(),
        "llm": lambda expected: LLMDecisionModel(GoldenSetClient(expected)),
        "composite": lambda expected: CompositeDecisionModel(RulesDecisionModel(), LLMDecisionModel(GoldenSetClient(expected))),
    }
    results: list[dict[str, float | int | str]] = []
    for name, factory in model_factories.items():
        correct = inconclusive = 0
        started = perf_counter()
        for case in cases:
            decision = factory(case["expected_intent"]).decide(case["message"], ConversationContext())
            if decision is None:
                inconclusive += 1
                continue
            correct += decision.intent.value == case["expected_intent"]
            inconclusive += decision.needs_clarification
        elapsed_ms = (perf_counter() - started) * 1000
        results.append({
            "model": name,
            "accuracy": round(correct / len(cases), 3),
            "latency_ms": round(elapsed_ms / len(cases), 3),
            "inconclusive_rate": round(inconclusive / len(cases), 3),
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-set", type=Path, default=Path(__file__).with_name("data") / "golden_set.yaml")
    args = parser.parse_args()
    cases = yaml.safe_load(args.golden_set.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("golden set must be a non-empty list")
    print("model      accuracy  latency_ms  inconclusive_rate")
    for result in evaluate(cases):
        print(f"{result['model']:<10} {result['accuracy']:<9} {result['latency_ms']:<11} {result['inconclusive_rate']}")


if __name__ == "__main__":
    main()
