"""Product repository interface."""

from decimal import Decimal
from typing import Protocol

from src.domain import Customer, Order, OrderItem, Product, Promotion


class ProductRepository(Protocol):
    def get(self, product_id: int) -> Product | None: ...

    def search(
        self, *, category_id: int | None = None, max_price: Decimal | None = None,
        in_stock: bool = True, query: str | None = None, limit: int = 5,
    ) -> list[Product]: ...
