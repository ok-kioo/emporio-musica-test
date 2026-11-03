"""SQLAlchemy Core implementation of the customer repository port."""

from sqlalchemy import Engine, select

from src.domain import Customer
from src.infrastructure.database.schema import customers


class SQLAlchemyCustomerRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_by_phone(self, phone: str) -> Customer | None:
        with self._engine.connect() as connection:
            row = connection.execute(select(customers).where(customers.c.phone == phone)).mappings().first()
        return _to_customer(row) if row else None


def _to_customer(row) -> Customer:
    return Customer(id=row["customer_id"], name=row["name"], phone=row["phone"], email=row["email"], city=row["city"])
