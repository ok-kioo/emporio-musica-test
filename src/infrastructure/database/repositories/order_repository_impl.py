"""SQLAlchemy Core implementation of the order repository port."""

from decimal import Decimal

from sqlalchemy import Engine, select

from src.domain import Order, OrderItem, OrderStatus, PaymentMethod
from src.infrastructure.database.schema import order_items, orders


class SQLAlchemyOrderRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_for_customer(self, order_id: int, customer_id: int) -> Order | None:
        statement = select(orders).where(orders.c.order_id == order_id, orders.c.customer_id == customer_id)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return _to_order(row) if row else None

    def list_for_customer(self, customer_id: int) -> list[Order]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(orders).where(orders.c.customer_id == customer_id).order_by(orders.c.order_date.desc())).mappings().all()
        return [_to_order(row) for row in rows]

    def list_items(self, order_id: int) -> list[OrderItem]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(order_items).where(order_items.c.order_id == order_id).order_by(order_items.c.product_id)).mappings().all()
        return [OrderItem(order_id=row["order_id"], product_id=row["product_id"], quantity=row["quantity"]) for row in rows]


def _to_order(row) -> Order:
    return Order(id=row["order_id"], customer_id=row["customer_id"], order_date=row["order_date"], status=OrderStatus(row["status"]), total_brl=Decimal(str(row["total_brl"])), payment_method=PaymentMethod(row["payment_method"]), tracking_code=row["tracking_code"], estimated_delivery=row["estimated_delivery"], notes=row["notes"])
