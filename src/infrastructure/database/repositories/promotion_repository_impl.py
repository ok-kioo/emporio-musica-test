"""SQLAlchemy Core implementation of the promotion repository port."""

from decimal import Decimal

from sqlalchemy import Engine, select

from src.domain import Promotion
from src.infrastructure.database.schema import promotions


class SQLAlchemyPromotionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def active_for_product(self, product_id: int) -> list[Promotion]:
        statement = select(promotions).where(promotions.c.product_id == product_id, promotions.c.is_active.is_(True))
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_to_promotion(row) for row in rows]


def _to_promotion(row) -> Promotion:
    return Promotion(id=row["promotion_id"], product_id=row["product_id"], discount_percent=Decimal(str(row["discount_percent"])), description=row["description"], is_active=row["is_active"])
