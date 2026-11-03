from src.application.decisions import CompositeDecisionModel, ConversationContext, Intent, LLMDecisionModel, RulesDecisionModel
from src.application.ports import DecisionChoice
from src.domain import AccessLevel
from src.infrastructure.llm import FakeDecisionClient


def test_rules_model_handles_human_escalation_without_an_llm() -> None:
    decision = RulesDecisionModel().decide("Quero falar com um atendente humano", ConversationContext())

    assert decision is not None
    assert decision.escalate
    assert decision.escalation_reason == "human_requested"


def test_rules_model_identifies_a_policy_question_for_an_order() -> None:
    decision = RulesDecisionModel().decide(
        "Posso trocar o pedido 17 por defeito?", ConversationContext(access_level=AccessLevel.VERIFIED_CHANNEL)
    )

    assert decision is not None
    assert decision.intent is Intent.HYBRID
    assert decision.entities == {"order_id": 17}


def test_composite_uses_llm_only_when_rules_are_inconclusive() -> None:
    llm = LLMDecisionModel(FakeDecisionClient(DecisionChoice("policy", {"policy": 0.94})))
    decision = CompositeDecisionModel(RulesDecisionModel(), llm).decide("Como funciona isso?", ConversationContext())

    assert decision.intent is Intent.POLICY
    assert decision.confidence == 0.94


def test_low_confidence_llm_decision_becomes_a_clarification() -> None:
    model = LLMDecisionModel(FakeDecisionClient(DecisionChoice("data", {"data": 0.5})))

    decision = model.decide("Quero saber uma coisa", ConversationContext())

    assert decision.intent is Intent.CLARIFICATION
    assert decision.needs_clarification
