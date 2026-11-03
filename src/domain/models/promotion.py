"""Promotion entity."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Promotion:
    id: int
    product_id: int
    discount_percent: Decimal
    description: str
    is_active: bool
