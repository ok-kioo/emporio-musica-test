"""In-memory implementations of application ports for deterministic tests."""

from datetime import datetime, timedelta

from src.domain import Message, Session


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[Message]] = {}

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def save(self, session: Session) -> None:
        self._sessions[session.id] = session

    def append_message(self, message: Message) -> None:
        if message.session_id not in self._sessions:
            raise ValueError("message session does not exist")
        self._messages.setdefault(message.session_id, []).append(message)

    def list_messages(self, session_id: str) -> list[Message]:
        return sorted(self._messages.get(session_id, ()), key=lambda message: (message.created_at, message.id))


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[datetime, int]] = {}

    def consume(self, key: str, *, limit: int, window_seconds: int, now: datetime) -> bool:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        starts_at, count = self._windows.get(key, (now, 0))
        if now >= starts_at + timedelta(seconds=window_seconds):
            starts_at, count = now, 0
        if count >= limit:
            self._windows[key] = (starts_at, count)
            return False
        self._windows[key] = (starts_at, count + 1)
        return True
