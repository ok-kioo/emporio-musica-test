"""Promotion repository interface."""

from typing import Protocol

from src.domain import Promotion


class PromotionRepository(Protocol):
    def active_for_product(self, product_id: int) -> list[Promotion]: ...
