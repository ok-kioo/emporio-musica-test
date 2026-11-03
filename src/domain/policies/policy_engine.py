"""Deterministic policy engine that applies named evaluators; never interprets manual text."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any, Mapping

from src.domain.models.results import Source


class RuleStatus(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    NEEDS_INFORMATION = "needs_information"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True, slots=True)
class PolicyFacts:
    values: Mapping[str, Any]

    def get(self, name: str) -> Any:
        return self.values.get(name)


@dataclass(frozen=True, slots=True)
class PolicyRule:
    id: str
    evaluator: str
    params: Mapping[str, Any]
    requires_facts: tuple[str, ...]
    reason_codes: Mapping[str, str]
    section: str
    source: Source


@dataclass(frozen=True, slots=True)
class RuleDescription:
    rule_id: str
    policy_version: str
    section: str
    requires_facts: tuple[str, ...]
    source: Source


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: str
    status: RuleStatus
    reason_code: str
    policy_version: str
    facts_used: Mapping[str, Any]
    sources: tuple[Source, ...] = ()
    missing_facts: tuple[str, ...] = ()
    explanation_hint: str | None = None


class PolicyEngine:

    def __init__(self, rules_by_version: Mapping[str, Mapping[str, PolicyRule]]) -> None:
        self._rules_by_version = rules_by_version

    def describe(self, topic_or_rule_id: str, policy_version: str) -> RuleDescription:
        rule = self._rule(topic_or_rule_id, policy_version)
        return RuleDescription(rule.id, policy_version, rule.section, rule.requires_facts, rule.source)

    def evaluate(self, rule_id: str, facts: PolicyFacts, policy_version: str) -> RuleResult:
        rule = self._rule(rule_id, policy_version)
        if rule.evaluator == "days_window" and rule.params["reference"] == "delivery_date":
            if facts.get("order_status") is not None and facts.get("order_status") != "delivered":
                return self._result(rule, policy_version, RuleStatus.NOT_ELIGIBLE, "not_started", facts)
        missing = tuple(name for name in rule.requires_facts if facts.get(name) is None)
        if missing:
            return self._result(rule, policy_version, RuleStatus.NEEDS_INFORMATION, "missing", facts, missing)
        if rule.evaluator == "days_window":
            return self._days_window(rule, facts, policy_version)
        if rule.evaluator == "threshold":
            return self._threshold(rule, facts, policy_version)
        if rule.evaluator == "installment_minimum":
            return self._installment_minimum(rule, facts, policy_version)
        if rule.evaluator == "exclusion_flag":
            return self._exclusion_flag(rule, facts, policy_version)
        raise ValueError(f"Unsupported evaluator: {rule.evaluator}")

    def _rule(self, rule_id: str, version: str) -> PolicyRule:
        try:
            return self._rules_by_version[version][rule_id]
        except KeyError as error:
            raise ValueError(f"Rule {rule_id!r} does not exist in policy {version!r}") from error

    def _days_window(self, rule: PolicyRule, facts: PolicyFacts, version: str) -> RuleResult:
        reference_name = str(rule.params["reference"])
        reference = facts.get(reference_name)
        evaluation_date = facts.get("evaluation_date")
        if not isinstance(reference, date) or not isinstance(evaluation_date, date):
            return self._result(rule, version, RuleStatus.NEEDS_INFORMATION, "missing", facts, (reference_name, "evaluation_date"))
        deadline = reference + timedelta(days=int(rule.params["days"]))
        if evaluation_date == deadline:
            return self._result(rule, version, RuleStatus.MANUAL_REVIEW, "borderline", facts)
        status = RuleStatus.ELIGIBLE if evaluation_date < deadline else RuleStatus.NOT_ELIGIBLE
        return self._result(rule, version, status, "met" if status is RuleStatus.ELIGIBLE else "not_met", facts)

    def _threshold(self, rule: PolicyRule, facts: PolicyFacts, version: str) -> RuleResult:
        value = facts.get(str(rule.params["field"]))
        threshold = rule.params["minimum"]
        status = RuleStatus.ELIGIBLE if value >= threshold else RuleStatus.NOT_ELIGIBLE
        return self._result(rule, version, status, "met" if status is RuleStatus.ELIGIBLE else "not_met", facts)

    def _installment_minimum(self, rule: PolicyRule, facts: PolicyFacts, version: str) -> RuleResult:
        installments = facts.get("installments")
        total = facts.get("total_brl")
        valid_range = int(rule.params["minimum_installments"]) <= installments <= int(rule.params["maximum_installments"])
        meets_minimum = total / installments >= rule.params["minimum_installment_brl"]
        status = RuleStatus.ELIGIBLE if valid_range and meets_minimum else RuleStatus.NOT_ELIGIBLE
        return self._result(rule, version, status, "met" if status is RuleStatus.ELIGIBLE else "not_met", facts)

    def _exclusion_flag(self, rule: PolicyRule, facts: PolicyFacts, version: str) -> RuleResult:
        excluded = any(bool(facts.get(name)) for name in rule.params["excluded_facts"])
        status = RuleStatus.NOT_ELIGIBLE if excluded else RuleStatus.ELIGIBLE
        return self._result(rule, version, status, "not_met" if excluded else "met", facts)

    @staticmethod
    def _result(rule: PolicyRule, version: str, status: RuleStatus, reason_key: str, facts: PolicyFacts,
                missing: tuple[str, ...] = ()) -> RuleResult:
        return RuleResult(
            rule_id=rule.id, status=status, reason_code=rule.reason_codes[reason_key], policy_version=version,
            facts_used={name: facts.get(name) for name in rule.requires_facts if facts.get(name) is not None},
            sources=(rule.source,), missing_facts=missing,
        )
