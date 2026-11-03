from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain.policies.policy_engine import PolicyEngine, PolicyFacts, RuleStatus
from src.infrastructure.policies import load_ruleset



RULES_PATH = Path(__file__).parents[1] / "data" / "policies" / "v2.1" / "rules.yaml"


@pytest.fixture
def engine() -> PolicyEngine:
    version, rules = load_ruleset(RULES_PATH)
    return PolicyEngine({version: rules})


def test_describe_returns_versioned_rule_metadata(engine: PolicyEngine) -> None:
    description = engine.describe("return_regret_window", "2.1")

    assert description.section == "4.1"
    assert description.policy_version == "2.1"
    assert description.source.source == "políticas_da_loja.pdf"


def test_rule_result_contains_only_decision_facts_and_authorized_source(engine: PolicyEngine) -> None:
    result = engine.evaluate(
        "metropolitan_free_shipping",
        PolicyFacts({"total_brl": Decimal("500"), "untrusted_claim": "free shipping promised"}),
        "2.1",
    )

    assert result.facts_used == {"total_brl": Decimal("500")}
    assert result.sources[0].source == "políticas_da_loja.pdf"
    assert result.sources[0].section == "5.1"


def test_regret_return_is_eligible_before_the_deadline(engine: PolicyEngine) -> None:
    result = engine.evaluate(
        "return_regret_window",
        PolicyFacts({"order_status": "delivered", "delivery_date": date(2025, 6, 1), "evaluation_date": date(2025, 6, 5)}),
        "2.1",
    )

    assert result.status is RuleStatus.ELIGIBLE
    assert result.reason_code == "WITHIN_REGRET_WINDOW"


def test_non_delivered_order_does_not_start_return_window(engine: PolicyEngine) -> None:
    result = engine.evaluate(
        "return_regret_window",
        PolicyFacts({"order_status": "shipped", "delivery_date": None, "evaluation_date": date(2025, 6, 5)}),
        "2.1",
    )

    assert result.status is RuleStatus.NOT_ELIGIBLE
    assert result.reason_code == "WINDOW_NOT_STARTED"


def test_missing_facts_do_not_produce_an_eligibility_decision(engine: PolicyEngine) -> None:
    result = engine.evaluate("metropolitan_free_shipping", PolicyFacts({}), "2.1")

    assert result.status is RuleStatus.NEEDS_INFORMATION
    assert result.missing_facts == ("total_brl",)


def test_threshold_and_exclusion_rules_are_deterministic(engine: PolicyEngine) -> None:
    shipping = engine.evaluate("metropolitan_free_shipping", PolicyFacts({"total_brl": Decimal("500")}), "2.1")
    pix = engine.evaluate("pix_discount_non_cumulative", PolicyFacts({"price_is_promotional": True}), "2.1")

    assert shipping.status is RuleStatus.ELIGIBLE
    assert pix.status is RuleStatus.NOT_ELIGIBLE
    assert pix.reason_code == "PIX_DISCOUNT_NOT_CUMULATIVE"


def test_deadline_is_escalated_and_expired_warranty_is_rejected(engine: PolicyEngine) -> None:
    borderline = engine.evaluate(
        "return_regret_window",
        PolicyFacts({"order_status": "delivered", "delivery_date": date(2025, 6, 1), "evaluation_date": date(2025, 6, 8)}),
        "2.1",
    )
    warranty = engine.evaluate(
        "legal_warranty_window",
        PolicyFacts({"order_date": date(2025, 1, 1), "evaluation_date": date(2025, 5, 1)}),
        "2.1",
    )

    assert borderline.status is RuleStatus.MANUAL_REVIEW
    assert warranty.status is RuleStatus.NOT_ELIGIBLE


def test_installment_ranges_match_the_manual_minimums(engine: PolicyEngine) -> None:
    eligible = engine.evaluate(
        "installments_4_to_6", PolicyFacts({"installments": 6, "total_brl": Decimal("480")}), "2.1"
    )
    rejected = engine.evaluate(
        "installments_7_to_12", PolicyFacts({"installments": 12, "total_brl": Decimal("1199")}), "2.1"
    )

    assert eligible.status is RuleStatus.ELIGIBLE
    assert rejected.status is RuleStatus.NOT_ELIGIBLE


def test_invalid_rules_yaml_is_rejected(tmp_path: Path) -> None:
    malformed = tmp_path / "rules.yaml"
    malformed.write_text("policy_version: '2.1'\nrules: []\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_ruleset(malformed)
