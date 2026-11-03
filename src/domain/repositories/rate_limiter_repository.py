"""Rate limiting port."""

from datetime import datetime
from typing import Protocol


class RateLimiterRepository(Protocol):
    def consume(self, key: str, *, limit: int, window_seconds: int, now: datetime) -> bool: ...
