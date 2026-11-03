"""SQLite implementations for session history and rate limiting."""

import sqlite3
from datetime import datetime, timedelta

from src.domain import AccessLevel, Message, MessageRole, Session


class SQLiteSessionStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, session_id: str) -> Session | None:
        row = self._connection.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return _to_session(row) if row else None

    def save(self, session: Session) -> None:
        self._connection.execute(
            """INSERT INTO sessions
            (session_id, channel_phone, customer_id, access_level, policy_version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                channel_phone = excluded.channel_phone, customer_id = excluded.customer_id,
                access_level = excluded.access_level, policy_version = excluded.policy_version,
                updated_at = excluded.updated_at""",
            (session.id, session.channel_phone, session.customer_id, int(session.access_level), session.policy_version,
             session.created_at.isoformat(), session.updated_at.isoformat()),
        )
        self._connection.commit()

    def append_message(self, message: Message) -> None:
        self._connection.execute(
            "INSERT INTO messages (message_id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (message.id, message.session_id, message.role.value, message.content, message.created_at.isoformat()),
        )
        self._connection.commit()

    def list_messages(self, session_id: str) -> list[Message]:
        rows = self._connection.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at, message_id", (session_id,)
        ).fetchall()
        return [_to_message(row) for row in rows]


class SQLiteRateLimiter:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def consume(self, key: str, *, limit: int, window_seconds: int, now: datetime) -> bool:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        row = self._connection.execute(
            "SELECT window_started_at, request_count FROM rate_limits WHERE rate_limit_key = ?", (key,)
        ).fetchone()
        starts_at = datetime.fromisoformat(row["window_started_at"]) if row else now
        count = row["request_count"] if row else 0
        if now >= starts_at + timedelta(seconds=window_seconds):
            starts_at, count = now, 0
        if count >= limit:
            return False
        self._connection.execute(
            """INSERT INTO rate_limits (rate_limit_key, window_started_at, request_count) VALUES (?, ?, ?)
            ON CONFLICT(rate_limit_key) DO UPDATE SET
                window_started_at = excluded.window_started_at, request_count = excluded.request_count""",
            (key, starts_at.isoformat(), count + 1),
        )
        self._connection.commit()
        return True


def _to_session(row: sqlite3.Row) -> Session:
    return Session(
        id=row["session_id"], channel_phone=row["channel_phone"], customer_id=row["customer_id"],
        access_level=AccessLevel(row["access_level"]), policy_version=row["policy_version"],
        created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["message_id"], session_id=row["session_id"], role=MessageRole(row["role"]),
        content=row["content"], created_at=datetime.fromisoformat(row["created_at"]),
    )
