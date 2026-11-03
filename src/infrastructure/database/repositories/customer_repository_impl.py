"""SQLite implementation of the CustomerRepository interface."""

import sqlite3

from src.domain import Customer


class SQLiteCustomerRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def find_by_phone(self, phone: str) -> Customer | None:
        row = self._connection.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
        return _to_customer(row) if row else None


def _to_customer(row: sqlite3.Row) -> Customer:
    return Customer(id=row["customer_id"], name=row["name"], phone=row["phone"], email=row["email"], city=row["city"])
