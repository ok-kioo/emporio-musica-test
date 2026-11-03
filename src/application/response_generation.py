"""Evidence-bounded response generation."""

import json

from src.application.ports import TextClient
from src.application.privacy import minimize_evidence, redact_text
from src.domain import EvidenceBundle


class EvidenceResponseGenerator:
    """Delegates wording to a text model without delegating facts or decisions."""

    def __init__(self, client: TextClient) -> None:
        self._client = client

    def generate(self, *, customer_message: str, evidence: EvidenceBundle) -> str:
        system_prompt = (
            "You are a customer-service writer. Use only the supplied evidence. "
            "Never invent prices, stock, promotions, order details, policy exceptions, or eligibility. "
            "A policy result is a preliminary analysis and must not authorize refunds or exchanges. "
            "If evidence requests escalation, direct the customer to human support."
        )
        user_prompt = json.dumps(
            {
                "customer_message": redact_text(customer_message),
                "intent": evidence.intent,
                "facts": minimize_evidence(evidence.facts),
                "sources": [
                    {
                        "source": source.source,
                        "record_id": source.record_id,
                        "page": source.page,
                        "section": source.section,
                        "chunk_id": source.chunk_id,
                    }
                    for source in evidence.sources
                ],
                "escalation": evidence.escalation,
            },
            ensure_ascii=False,
            default=str,
        )
        response = self._client.generate(system_prompt=system_prompt, user_prompt=user_prompt).strip()
        if not response:
            raise ValueError("text model returned an empty response")
        return response
