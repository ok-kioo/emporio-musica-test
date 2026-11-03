"""SQLAlchemy Core implementations for session history"""

from datetime import datetime, timedelta
from sqlalchemy import Engine, select, update

from src.domain import AccessLevel, Message, MessageRole, Session
from src.infrastructure.database.schema import messages, rate_limits, sessions


class SQLAlchemySessionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, session_id: str) -> Session | None:
        with self._engine.connect() as connection:
            row = connection.execute(select(sessions).where(sessions.c.session_id == session_id)).mappings().first()
        return _to_session(row) if row else None

    def save(self, session: Session) -> None:
        values = {"channel_phone": session.channel_phone, "customer_id": session.customer_id, "access_level": int(session.access_level), "policy_version": session.policy_version, "updated_at": session.updated_at}
        with self._engine.begin() as connection:
            changed = connection.execute(update(sessions).where(sessions.c.session_id == session.id).values(**values))
            if changed.rowcount == 0:
                connection.execute(sessions.insert().values(session_id=session.id, created_at=session.created_at, **values))

    def append_message(self, message: Message) -> None:
        with self._engine.begin() as connection:
            connection.execute(messages.insert().values(message_id=message.id, session_id=message.session_id, role=message.role.value, content=message.content, created_at=message.created_at))

    def list_messages(self, session_id: str) -> list[Message]:
        statement = select(messages).where(messages.c.session_id == session_id).order_by(messages.c.created_at, messages.c.message_id)
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_to_message(row) for row in rows]

class SQLAlchemyRateLimitRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def consume(self, key: str, *, limit: int, window_seconds: int, now: datetime) -> bool:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        with self._engine.begin() as connection:
            row = connection.execute(select(rate_limits).where(rate_limits.c.rate_limit_key == key)).mappings().first()
            started_at, count = (row["window_started_at"], row["request_count"]) if row else (now, 0)
            if started_at.tzinfo is None and now.tzinfo is not None:
                started_at = started_at.replace(tzinfo=now.tzinfo)
            if now >= started_at + timedelta(seconds=window_seconds):
                started_at, count = now, 0
            if count >= limit:
                return False
            values = {"window_started_at": started_at, "request_count": count + 1}
            if row:
                connection.execute(update(rate_limits).where(rate_limits.c.rate_limit_key == key).values(**values))
            else:
                connection.execute(rate_limits.insert().values(rate_limit_key=key, **values))
        return True


def _to_session(row) -> Session:
    return Session(id=row["session_id"], channel_phone=row["channel_phone"], customer_id=row["customer_id"], access_level=AccessLevel(row["access_level"]), policy_version=row["policy_version"], created_at=row["created_at"], updated_at=row["updated_at"])


def _to_message(row) -> Message:
    return Message(id=row["message_id"], session_id=row["session_id"], role=MessageRole(row["role"]), content=row["content"], created_at=row["created_at"])
