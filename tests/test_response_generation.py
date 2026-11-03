from src.application.response_generation import EvidenceResponseGenerator
from src.domain import EvidenceBundle, Source
from src.infrastructure.llm import FakeTextClient


def test_response_generator_delegates_only_wording_to_the_text_client() -> None:
    evidence = EvidenceBundle(
        intent="policy", access_level=0, facts={"rule_status": "eligible"},
        sources=(Source(source="políticas_da_loja.pdf", section="4.1"),),
    )

    response = EvidenceResponseGenerator(FakeTextClient("A equipe confirmará a análise.")).generate(
        customer_message="Posso devolver?", evidence=evidence
    )

    assert response == "A equipe confirmará a análise."


def test_response_generator_rejects_an_unsupported_human_handoff() -> None:
    evidence = EvidenceBundle(intent="policy", access_level=0)

    try:
        EvidenceResponseGenerator(FakeTextClient("Vou transferir você para o suporte.")).generate(
            customer_message="Qual é a política de devolução?", evidence=evidence
        )
    except ValueError as error:
        assert "unsupported human handoff" in str(error)
    else:
        raise AssertionError("An unsupported handoff must be rejected")
