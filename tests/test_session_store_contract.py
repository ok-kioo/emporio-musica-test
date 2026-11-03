import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.domain import AccessLevel, Message, MessageRole, Session
from src.domain.repositories import RateLimiter, SessionStore
from src.infrastructure.database import SQLiteRateLimiter, SQLiteSessionStore, connect
from src.infrastructure.memory.memory import InMemoryRateLimiter, InMemorySessionStore


NOW = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)


def _session() -> Session:
    return Session(
        id="session-1", channel_phone="(67) 99812-3456", customer_id=1,
        access_level=AccessLevel.VERIFIED_CHANNEL, policy_version="2.1", created_at=NOW, updated_at=NOW,
    )


@pytest.fixture(params=["memory", "sqlite"])
def session_store(request: pytest.FixtureRequest, tmp_path) -> SessionStore:
    if request.param == "memory":
        return InMemorySessionStore()
    connection = connect(tmp_path / "sessions.sqlite3")
    connection.execute(
        "INSERT INTO customers (customer_id, name, phone, email, city) VALUES (1, 'Test customer', '(67) 99812-3456', 'test@example.com', 'Campo Grande')"
    )
    connection.commit()
    return SQLiteSessionStore(connection)


@pytest.fixture(params=["memory", "sqlite"])
def rate_limiter(request: pytest.FixtureRequest, tmp_path) -> RateLimiter:
    if request.param == "memory":
        return InMemoryRateLimiter()
    return SQLiteRateLimiter(connect(tmp_path / "rate-limits.sqlite3"))


def test_session_store_contract_preserves_identity_policy_and_message_order(session_store: SessionStore) -> None:
    session_store.save(_session())
    session_store.append_message(Message("m-2", "session-1", MessageRole.ASSISTANT, "Hello", NOW + timedelta(seconds=2)))
    session_store.append_message(Message("m-1", "session-1", MessageRole.CUSTOMER, "Help", NOW))

    restored = session_store.get("session-1")

    assert restored is not None
    assert restored.customer_id == 1
    assert restored.policy_version == "2.1"
    assert [message.id for message in session_store.list_messages("session-1")] == ["m-1", "m-2"]


def test_session_store_contract_rejects_messages_for_unknown_sessions(session_store: SessionStore) -> None:
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        session_store.append_message(Message("m-1", "unknown", MessageRole.CUSTOMER, "Help", NOW))


def test_rate_limiter_contract_enforces_limit_and_resets_window(rate_limiter: RateLimiter) -> None:
    assert rate_limiter.consume("+5567999999999", limit=2, window_seconds=60, now=NOW)
    assert rate_limiter.consume("+5567999999999", limit=2, window_seconds=60, now=NOW)
    assert not rate_limiter.consume("+5567999999999", limit=2, window_seconds=60, now=NOW)
    assert rate_limiter.consume("+5567999999999", limit=2, window_seconds=60, now=NOW + timedelta(seconds=60))
