"""Channel-phone authentication and session creation for the chat boundary."""

import hashlib
import hmac
import os
from datetime import datetime, timezone

from src.domain import AccessLevel, Session
from src.domain.repositories import CustomerRepository, SessionRepository


def normalize_phone(phone: str) -> str:
    """Return a comparable Brazilian phone number with country code 55."""
    digits = "".join(character for character in phone if character.isdigit())
    if digits.startswith("55"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = f"{digits[:2]}9{digits[2:]}"
    if len(digits) != 11:
        raise ValueError("phone must include a Brazilian area code and number")
    return f"55{digits}"


class AuthService:
    def __init__(self, customers: CustomerRepository, sessions: SessionRepository, *, secret: str | None = None) -> None:
        self._customers = customers
        self._sessions = sessions
        self._secret = (secret or os.getenv("SESSION_HASH_SECRET", "local-development-secret")).encode()

    def get_or_create_session(self, phone: str, policy_version: str) -> Session:
        normalized = normalize_phone(phone)
        session_id = hmac.new(self._secret, normalized.encode(), hashlib.sha256).hexdigest()[:32]
        existing = self._sessions.get(session_id)
        if existing:
            return existing
        customer = self._customers.find_by_phone(normalized)
        now = datetime.now(timezone.utc)
        session = Session(
            id=session_id,
            channel_phone=normalized,
            customer_id=customer.id if customer else None,
            access_level=AccessLevel.VERIFIED_CHANNEL if customer else AccessLevel.ANONYMOUS,
            policy_version=policy_version,
            created_at=now,
            updated_at=now,
        )
        self._sessions.save(session)
        return session
