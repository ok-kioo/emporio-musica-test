"""Session persistence port."""

from typing import Protocol

from src.domain import Message, Session


class SessionRepository(Protocol):
    def get(self, session_id: str) -> Session | None: ...

    def save(self, session: Session) -> None: ...

    def append_message(self, message: Message) -> None: ...

    def list_messages(self, session_id: str) -> list[Message]: ...
