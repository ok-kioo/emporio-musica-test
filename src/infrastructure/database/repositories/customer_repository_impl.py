"""SQLAlchemy Core implementation of the customer repository port."""

import re

from sqlalchemy import Engine, select

from src.domain import Customer
from src.infrastructure.database.schema import customers


class SQLAlchemyCustomerRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_by_phone(self, phone: str) -> Customer | None:
        target = _normalized_phone(phone)
        with self._engine.connect() as connection:
            rows = connection.execute(select(customers)).mappings().all()
        row = next((candidate for candidate in rows if _normalized_phone(candidate["phone"]) == target), None)
        return _to_customer(row) if row else None


def _to_customer(row) -> Customer:
    return Customer(id=row["customer_id"], name=row["name"], phone=row["phone"], email=row["email"], city=row["city"])


def _normalized_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return digits if digits.startswith("55") else f"55{digits}"
