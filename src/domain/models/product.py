"""Product entity and its catalog states."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Mapping


class ProductStatus(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    price_brl: Decimal
    category_id: int
    description: str
    stock_quantity: int
    status: ProductStatus
    specs: Mapping[str, str]
    created_at: date

    @property
    def is_available(self) -> bool:
        return self.status is ProductStatus.ACTIVE and self.stock_quantity > 0
