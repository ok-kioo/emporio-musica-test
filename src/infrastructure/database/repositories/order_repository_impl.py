"""SQLite implementation of the OrderRepository interface."""

import sqlite3
from datetime import date
from decimal import Decimal

from src.domain import Order, OrderItem, OrderStatus, PaymentMethod


class SQLiteOrderRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_for_customer(self, order_id: int, customer_id: int) -> Order | None:
        row = self._connection.execute(
            "SELECT * FROM orders WHERE order_id = ? AND customer_id = ?", (order_id, customer_id)
        ).fetchone()
        return _to_order(row) if row else None

    def list_for_customer(self, customer_id: int) -> list[Order]:
        rows = self._connection.execute(
            "SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC", (customer_id,)
        ).fetchall()
        return [_to_order(row) for row in rows]

    def list_items(self, order_id: int) -> list[OrderItem]:
        rows = self._connection.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY product_id", (order_id,)
        ).fetchall()
        return [OrderItem(order_id=row["order_id"], product_id=row["product_id"], quantity=row["quantity"]) for row in rows]


def _to_order(row: sqlite3.Row) -> Order:
    estimated_delivery = row["estimated_delivery"] or None
    return Order(
        id=row["order_id"], customer_id=row["customer_id"], order_date=date.fromisoformat(row["order_date"]),
        status=OrderStatus(row["status"]), total_brl=Decimal(str(row["total_brl"])),
        payment_method=PaymentMethod(row["payment_method"]), tracking_code=row["tracking_code"] or None,
        estimated_delivery=date.fromisoformat(estimated_delivery) if estimated_delivery else None,
        notes=row["notes"] or None,
    )
