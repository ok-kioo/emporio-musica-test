"""Validate and load YAML rules for the policy engine."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.domain.policies.policy_engine import PolicyRule
from src.domain import Source


class _Source(BaseModel):
    document: str
    section: str


class _Rule(BaseModel):
    id: str
    source: _Source
    type: str
    params: dict[str, Any]
    requires_facts: list[str] = Field(min_length=1)
    reason_codes: dict[str, str]


class _Ruleset(BaseModel):
    policy_version: str
    rules: list[_Rule] = Field(min_length=1)


def load_ruleset(path: Path) -> tuple[str, dict[str, PolicyRule]]:
    """Load a YAML ruleset and return domain-ready rules."""
    with path.open(encoding="utf-8") as source:
        raw = yaml.safe_load(source)
    parsed = _Ruleset.model_validate(raw)
    rules = {
        item.id: PolicyRule(
            id=item.id, evaluator=item.type, params=item.params,
            requires_facts=tuple(item.requires_facts), reason_codes=item.reason_codes,
            section=item.source.section,
            source=Source(source=item.source.document, section=item.source.section),
        )
        for item in parsed.rules
    }
    if len(rules) != len(parsed.rules):
        raise ValueError("Rule IDs must be unique")
    return parsed.policy_version, rules
