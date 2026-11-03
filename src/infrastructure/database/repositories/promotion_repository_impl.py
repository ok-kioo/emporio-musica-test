"""SQLite implementation of the PromotionRepository interface."""

import sqlite3
from decimal import Decimal

from src.domain import Promotion


class SQLitePromotionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def active_for_product(self, product_id: int) -> list[Promotion]:
        rows = self._connection.execute(
            "SELECT * FROM promotions WHERE product_id = ? AND is_active = 1", (product_id,)
        ).fetchall()
        return [_to_promotion(row) for row in rows]

def _to_promotion(row: sqlite3.Row) -> Promotion:
    return Promotion(
        id=row["promotion_id"], product_id=row["product_id"], discount_percent=Decimal(str(row["discount_percent"])),
        description=row["description"], is_active=bool(row["is_active"]),
    )