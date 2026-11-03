from pathlib import Path

from src.application.auth_service import AuthService, normalize_phone
from src.application.decisions import RulesDecisionModel
from src.application.orchestrator import ChatOrchestrator
from src.application.router import Router
from src.application.tools import DataTools
from src.domain import AccessLevel
from src.infrastructure.database import (
    SQLAlchemyCustomerRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyProductRepository,
    SQLAlchemyPromotionRepository,
    SQLAlchemySessionRepository,
    create_database_engine,
    ingest_csv_data,
)


DATA_DIRECTORY = Path(__file__).parents[1] / "data"


def _chat(tmp_path: Path) -> tuple[AuthService, ChatOrchestrator]:
    engine = create_database_engine(tmp_path / "chat.sqlite3")
    ingest_csv_data(engine, DATA_DIRECTORY)
    sessions = SQLAlchemySessionRepository(engine)
    authenticator = AuthService(SQLAlchemyCustomerRepository(engine), sessions, secret="test-secret")
    tools = DataTools(SQLAlchemyProductRepository(engine), SQLAlchemyPromotionRepository(engine), SQLAlchemyOrderRepository(engine))
    return authenticator, ChatOrchestrator(Router(RulesDecisionModel()), sessions, tools)


def test_phone_is_normalized_and_authenticates_the_matching_customer(tmp_path: Path) -> None:
    authenticator, _ = _chat(tmp_path)

    session = authenticator.get_or_create_session("+55 (67) 99812-3456", "2.1")

    assert normalize_phone("(67) 99812-3456") == "5567998123456"
    assert session.access_level is AccessLevel.VERIFIED_CHANNEL
    assert session.customer_id == 1


def test_chat_uses_source_backed_catalog_lookup(tmp_path: Path) -> None:
    authenticator, chat = _chat(tmp_path)
    session = authenticator.get_or_create_session("(67) 99812-3456", "2.1")

    turn = chat.reply("Yamaha C40 Nylon Natural", session)

    assert "Yamaha C40 Nylon Natural" in turn.response
    assert turn.evidence.sources[0].source == "products.csv"


def test_unverified_channel_cannot_read_an_order(tmp_path: Path) -> None:
    authenticator, chat = _chat(tmp_path)
    session = authenticator.get_or_create_session("(67) 90000-0000", "2.1")

    turn = chat.reply("pedido 1", session)

    assert session.access_level is AccessLevel.ANONYMOUS
    assert "Não localizei" in turn.response
