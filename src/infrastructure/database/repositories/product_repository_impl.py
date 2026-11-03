"""Implementações SQLite das portas de repositório da aplicação."""

import json
import sqlite3
from datetime import date
from decimal import Decimal

from src.domain import Product, ProductStatus


class SQLiteProductRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, product_id: int) -> Product | None:
        row = self._connection.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
        return _to_product(row) if row else None

    def search(
        self, *, category_id: int | None = None, max_price: Decimal | None = None,
        in_stock: bool = True, query: str | None = None, limit: int = 5,
    ) -> list[Product]:
        clauses, parameters = [], []
        if category_id is not None:
            clauses.append("category_id = ?")
            parameters.append(category_id)
        if max_price is not None:
            clauses.append("price_brl <= ?")
            parameters.append(str(max_price))
        if in_stock:
            clauses.extend(("status = ?", "stock_quantity > 0"))
            parameters.append(ProductStatus.ACTIVE.value)
        if query:
            clauses.append("lower(name) LIKE ?")
            parameters.append(f"%{query.casefold()}%")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(limit)
        rows = self._connection.execute(
            f"SELECT * FROM products{where} ORDER BY name LIMIT ?", parameters
        ).fetchall()
        return [_to_product(row) for row in rows]

def _to_product(row: sqlite3.Row) -> Product:
    return Product(
        id=row["product_id"], name=row["name"], price_brl=Decimal(str(row["price_brl"])),
        category_id=row["category_id"], description=row["description"], stock_quantity=row["stock_quantity"],
        status=ProductStatus(row["status"]), specs=json.loads(row["specs"]), created_at=date.fromisoformat(row["created_at"]),
    )
