"""Conversation entities and access levels."""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum


class AccessLevel(IntEnum):
    ANONYMOUS = 0
    VERIFIED_CHANNEL = 1
    HUMAN_AGENT = 2


class MessageRole(StrEnum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    HUMAN_AGENT = "human_agent"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class Session:
    id: str
    channel_phone: str
    customer_id: int | None
    access_level: AccessLevel
    policy_version: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.channel_phone:
            raise ValueError("channel_phone is required")
        if self.access_level >= AccessLevel.VERIFIED_CHANNEL and self.customer_id is None:
            raise ValueError("a verified session requires an authenticated customer_id")
        if not self.policy_version:
            raise ValueError("policy_version is required")


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.content:
            raise ValueError("content is required")
