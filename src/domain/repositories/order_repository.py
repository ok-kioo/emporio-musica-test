"""Order repository interface."""

from typing import Protocol

from src.domain import Order, OrderItem


class OrderRepository(Protocol):
    def get_for_customer(self, order_id: int, customer_id: int) -> Order | None: ...

    def list_for_customer(self, customer_id: int) -> list[Order]: ...

    def list_items(self, order_id: int) -> list[OrderItem]: ...