from src.application.decisions import CompositeDecisionModel, ConversationContext, Intent, LLMDecisionModel, RulesDecisionModel
from src.application.ports import DecisionChoice
from src.application.router import Router
from src.infrastructure.llm import FakeDecisionClient


def test_router_consumes_the_single_decision_model_without_executing_tools() -> None:
    router = Router(CompositeDecisionModel(RulesDecisionModel(), LLMDecisionModel(FakeDecisionClient(DecisionChoice("data", {"data": 1.0})))))

    decision = router.route("Quero uma palheta", ConversationContext())

    assert decision.intent is Intent.DATA
    assert decision.action == "lookup_data"


def test_provider_failure_falls_back_to_a_safe_clarification() -> None:
    class UnavailableClient:
        def choose(self, **_kwargs):
            raise RuntimeError("provider unavailable")

    decision = Router(LLMDecisionModel(UnavailableClient())).route("Explique isso", ConversationContext())

    assert decision.intent is Intent.CLARIFICATION
    assert decision.needs_clarification
    assert not decision.escalate


def test_invalid_provider_payload_falls_back_to_a_safe_clarification() -> None:
    class InvalidPayloadClient:
        def choose(self, **_kwargs):
            return DecisionChoice("data", None)  # type: ignore[arg-type]

    decision = Router(LLMDecisionModel(InvalidPayloadClient())).route("Explique isso", ConversationContext())

    assert decision.intent is Intent.CLARIFICATION
    assert decision.needs_clarification


def test_router_turns_an_inconclusive_rules_only_model_into_a_clarification() -> None:
    decision = Router(RulesDecisionModel()).route("Pode me ajudar?", ConversationContext())

    assert decision.intent is Intent.CLARIFICATION
    assert decision.needs_clarification


def test_rules_escalate_a_complaint_without_calling_the_provider() -> None:
    decision = Router(RulesDecisionModel()).route("Quero registrar uma reclamação", ConversationContext())

    assert decision.escalate
    assert decision.escalation_reason == "complaint"
