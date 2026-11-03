"""Coordinates safe chat flows without giving the router data access."""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from uuid import uuid4

from src.application.router import Router
from src.application.response_generation import EvidenceResponseGenerator
from src.application.tools import DataTools
from src.domain import EvidenceBundle, Message, MessageRole, Session, ToolStatus
from src.domain.policies.policy_engine import PolicyEngine, PolicyFacts, RuleStatus
from src.application.policies.ports import PolicyRetriever
from src.domain.repositories import SessionRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatTurn:
    response: str
    evidence: EvidenceBundle


class ChatOrchestrator:
    def __init__(self, router: Router, sessions: SessionRepository, data_tools: DataTools,
                 policy_retriever: PolicyRetriever | None = None, policy_engine: PolicyEngine | None = None) -> None:
        self._router = router
        self._sessions = sessions
        self._data_tools = data_tools
        self._policy_retriever = policy_retriever
        self._policy_engine = policy_engine
        self._response_generator: EvidenceResponseGenerator | None = None

    def set_response_generator(self, generator: EvidenceResponseGenerator | None) -> None:
        """Enable a provider-backed writer after evidence has been assembled."""
        self._response_generator = generator

    def reply(self, message: str, session: Session) -> ChatTurn:
        self._save(session, MessageRole.CUSTOMER, message)
        decision = self._router.route(message, _context(session))
        if decision.escalate:
            return self._finish(session, message, "Vou encaminhar você à equipe: (67) 3341-4444 ou contato@emporiodamusica.com.br.", decision.intent.value, escalation=decision.escalation_reason)
        if decision.entities.get("order_id") is not None:
            result = self._data_tools.order_status(int(decision.entities["order_id"]), session)
            if result.status is ToolStatus.SUCCESS:
                data = result.data
                if decision.intent.value == "hybrid":
                    return self._hybrid_policy(session, message, data, result.sources)
                return self._finish(session, message, f"Seu pedido #{data['order_id']} está {data['status']}. Rastreamento: {data['tracking_code'] or 'indisponível'}.", decision.intent.value, facts=data, sources=result.sources)
            return self._finish(session, message, "Não localizei esse pedido neste canal. Use o número cadastrado ou fale com a equipe.", decision.intent.value)
        if decision.intent.value == "off_topic":
            return self._finish(session, message, "Posso ajudar com instrumentos musicais, pedidos e políticas da loja. O que você procura?", decision.intent.value)
        if decision.intent.value == "policy":
            return self._policy_response(session, message)
        if decision.intent.value == "data":
            result = self._data_tools.product_by_name(message)
            if result.status is ToolStatus.SUCCESS:
                data = result.data
                availability = "disponível" if data["available"] else "indisponível no momento"
                return self._finish(session, message, f"{data['name']} custa R$ {data['price_brl']} e está {availability}.", decision.intent.value, facts=data, sources=result.sources)
            if result.status is ToolStatus.AMBIGUOUS:
                names = ", ".join(item["name"] for item in result.data)
                return self._finish(session, message, f"Encontrei mais de uma opção: {names}. Qual modelo você quer?", decision.intent.value)
        if decision.needs_clarification:
            result = self._data_tools.product_by_name(message)
            if result.status is ToolStatus.SUCCESS:
                data = result.data
                availability = "disponível" if data["available"] else "indisponível no momento"
                return self._finish(session, message, f"{data['name']} custa R$ {data['price_brl']} e está {availability}.", "data", facts=data, sources=result.sources)
        return self._finish(session, message, "Como posso ajudar com instrumentos, pedidos ou políticas da loja?", decision.intent.value)

    def _policy_response(self, session: Session, message: str) -> ChatTurn:
        if not self._policy_retriever:
            return self._finish(session, message, "Não consegui consultar a política agora. Fale com a equipe: (67) 3341-4444.", "policy", escalation="policy_retriever_unavailable")
        result = self._policy_retriever.retrieve(message, policy_version=session.policy_version)
        if result.status is not ToolStatus.SUCCESS:
            return self._finish(session, message, "Não encontrei uma regra confiável para essa dúvida. A equipe pode confirmar em (67) 3341-4444.", "policy", escalation="insufficient_policy_evidence")
        return self._finish(session, message, "Consultei a política aplicável. Para uma pré-análise de uma compra, informe o número do pedido.", "policy", facts={"policy_version": session.policy_version}, sources=result.sources)

    def _hybrid_policy(self, session: Session, message: str, order: dict, order_sources) -> ChatTurn:
        if not self._policy_engine:
            return self._policy_response(session, message)
        rule_id = "return_regret_window" if any(term in message.casefold() for term in ("devol", "arrepend", "troca")) else "legal_warranty_window"
        facts = PolicyFacts({
            "order_status": order["status"], "delivery_date": _date_or_none(order["estimated_delivery"]),
            "order_date": _date_or_none(order["order_date"]), "evaluation_date": _reference_date(),
        })
        evaluation = self._policy_engine.evaluate(rule_id, facts, session.policy_version)
        status = "dentro do prazo" if evaluation.status is RuleStatus.ELIGIBLE else "em análise pela equipe"
        sources = tuple(order_sources) + evaluation.sources
        return self._finish(session, message, f"Pelo sistema, a pré-análise está {status}. A equipe confirma qualquer devolução, troca ou reembolso em (67) 3341-4444.", "hybrid", facts={"order": order, "rule_status": evaluation.status.value, "reason_code": evaluation.reason_code}, sources=sources, escalation="critical_policy_decision")

    def _finish(self, session: Session, customer_message: str, response: str, intent: str, *, facts: dict | None = None, sources=(), escalation: str | None = None) -> ChatTurn:
        evidence = EvidenceBundle(intent=intent, access_level=int(session.access_level), facts=facts or {}, sources=tuple(sources), escalation=escalation)
        if self._response_generator:
            try:
                response = self._response_generator.generate(
                    customer_message=customer_message,
                    evidence=evidence,
                    response_guidance=response,
                )
            except Exception as error:
                # The deterministic response remains available during provider outages.
                logger.warning("Response generation failed; using deterministic fallback: %s", error)
        self._save(session, MessageRole.ASSISTANT, response)
        return ChatTurn(response, evidence)

    def _save(self, session: Session, role: MessageRole, content: str) -> None:
        self._sessions.append_message(Message(str(uuid4()), session.id, role, content, datetime.now(timezone.utc)))


def _context(session: Session):
    from src.application.decisions import ConversationContext
    return ConversationContext(access_level=session.access_level, policy_version=session.policy_version)


def _date_or_none(value: str | None):
    from datetime import date
    return date.fromisoformat(value) if value else None


def _reference_date():
    from src.config import REFERENCE_DATE
    return REFERENCE_DATE
