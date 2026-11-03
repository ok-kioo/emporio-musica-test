"""Provider-independent routing decisions for the customer-service agent."""

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Mapping

from src.application.ports import DecisionClient
from src.config import ROUTER_CONFIDENCE_THRESHOLD
from src.application.privacy import redact_text
from src.domain import AccessLevel


class Intent(StrEnum):
    DATA = "data"
    POLICY = "policy"
    HYBRID = "hybrid"
    OFF_TOPIC = "off_topic"
    CLARIFICATION = "clarification"


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Minimal non-sensitive context that can influence routing."""

    access_level: AccessLevel = AccessLevel.ANONYMOUS
    policy_version: str | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    intent: Intent
    confidence: float
    reason: str
    action: str
    entities: Mapping[str, str | int | None] = field(default_factory=dict)
    missing_fields: tuple[str, ...] = ()
    needs_clarification: bool = False
    escalate: bool = False
    escalation_reason: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.escalate and not self.escalation_reason:
            raise ValueError("an escalation requires an escalation_reason")


class DecisionModel:
    """Structural base class; implementations never execute tools or access data."""

    def decide(self, message: str, context: ConversationContext) -> Decision | None:
        raise NotImplementedError


class RulesDecisionModel(DecisionModel):
    _HUMAN_PATTERN = re.compile(r"\b(atendente|humano|pessoa|gerente)\b", re.IGNORECASE)
    _COMPLAINT_PATTERN = re.compile(r"\b(reclama(?:ç|c)(?:ão|ao)|insatisfeit|procon)\w*", re.IGNORECASE)
    _INJECTION_PATTERN = re.compile(r"ignore\s+(as\s+)?(instru|regra)|system\s+prompt|dados?\s+intern", re.IGNORECASE)
    _ORDER_PATTERN = re.compile(r"\bpedido\s*(?:n[ºo°.]?\s*)?(\d+)\b", re.IGNORECASE)
    _POLICY_PATTERN = re.compile(r"\b(troca|devolu|arrependimento|garantia|defeito|frete|parcel|pix|política)\w*", re.IGNORECASE)
    _DATA_PATTERN = re.compile(r"\b(preço|estoque|produto|catálogo|pedido|rastreio|entrega)\w*", re.IGNORECASE)
    _ACCESSORY_PATTERN = re.compile(r"\b(corda|palheta|capotraste|cabo|afinador|suporte)\w*", re.IGNORECASE)
    _GREETING_PATTERN = re.compile(r"^\s*(oi|olá|ola|bom dia|boa tarde|boa noite)\W*$", re.IGNORECASE)
    _FAREWELL_PATTERN = re.compile(r"^\s*(tchau|até logo|ate logo|obrigad[oa])\W*$", re.IGNORECASE)

    def decide(self, message: str, context: ConversationContext) -> Decision | None:
        del context
        if self._INJECTION_PATTERN.search(message):
            return Decision(Intent.OFF_TOPIC, 1.0, "Unsafe instruction pattern detected.", "decline_unsafe_request")
        if self._HUMAN_PATTERN.search(message):
            return Decision(Intent.CLARIFICATION, 1.0, "Customer requested human assistance.", "escalate_human", escalate=True, escalation_reason="human_requested")
        if self._COMPLAINT_PATTERN.search(message):
            return Decision(Intent.CLARIFICATION, 1.0, "Complaint requires human follow-up.", "escalate_human", escalate=True, escalation_reason="complaint")
        if self._GREETING_PATTERN.match(message):
            return Decision(Intent.CLARIFICATION, 1.0, "Greeting without a request.", "greet", needs_clarification=True)
        if self._FAREWELL_PATTERN.match(message):
            return Decision(Intent.CLARIFICATION, 1.0, "Farewell without a request.", "farewell", needs_clarification=False)
        order_match = self._ORDER_PATTERN.search(message)
        has_policy = bool(self._POLICY_PATTERN.search(message))
        if order_match and has_policy:
            return Decision(Intent.HYBRID, 0.95, "Order reference and policy topic detected.", "evaluate_policy_for_order", {"order_id": int(order_match.group(1))})
        if order_match:
            return Decision(Intent.DATA, 0.95, "Order reference detected.", "lookup_order", {"order_id": int(order_match.group(1))})
        if has_policy:
            return Decision(Intent.POLICY, 0.9, "Policy topic detected.", "retrieve_policy")
        if self._DATA_PATTERN.search(message) or self._ACCESSORY_PATTERN.search(message):
            return Decision(Intent.DATA, 0.8, "Catalog or order data topic detected.", "lookup_data")
        return None


class LLMDecisionModel(DecisionModel):
    _CRITERIA = {
        Intent.DATA.value: "Catalog, price, availability, order status, or delivery tracking question.",
        Intent.POLICY.value: "Question about policies without a specific order.",
        Intent.HYBRID.value: "Policy question about a specific order or purchase.",
        Intent.OFF_TOPIC.value: "Unrelated request or request for internal instructions or private data.",
        Intent.CLARIFICATION.value: "Intent cannot be determined safely from the message.",
    }

    def __init__(self, client: DecisionClient, *, confidence_threshold: float = ROUTER_CONFIDENCE_THRESHOLD) -> None:
        self._client = client
        self._confidence_threshold = confidence_threshold

    def decide(self, message: str, context: ConversationContext) -> Decision:
        del context
        try:
            response = self._client.choose(
                state=redact_text(message),
                question="Classify the customer's intent. Do not infer customer identity or authorize operations.",
                criteria=self._CRITERIA,
            )
            confidence = float(response.probabilities.get(response.choice, 0.0))
        except Exception:
            return Decision(
                Intent.CLARIFICATION,
                0.0,
                "Decision provider was unavailable or returned an invalid response.",
                "ask_clarifying_question",
                needs_clarification=True,
            )
        if response.choice not in self._CRITERIA or confidence < self._confidence_threshold:
            return Decision(Intent.CLARIFICATION, confidence, "Classifier confidence is insufficient.", "ask_clarifying_question", needs_clarification=True)
        intent = Intent(response.choice)
        return Decision(intent, confidence, "Classifier selected a bounded intent.", _action_for(intent), needs_clarification=intent is Intent.CLARIFICATION)


class CompositeDecisionModel(DecisionModel):
    def __init__(self, rules: RulesDecisionModel, llm: LLMDecisionModel) -> None:
        self._rules = rules
        self._llm = llm

    def decide(self, message: str, context: ConversationContext) -> Decision:
        return self._rules.decide(message, context) or self._llm.decide(message, context)


def _action_for(intent: Intent) -> str:
    return {
        Intent.DATA: "lookup_data", Intent.POLICY: "retrieve_policy", Intent.HYBRID: "evaluate_policy_for_order",
        Intent.OFF_TOPIC: "decline_unsafe_request", Intent.CLARIFICATION: "ask_clarifying_question",
    }[intent]
