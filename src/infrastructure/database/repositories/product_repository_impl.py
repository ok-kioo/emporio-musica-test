"""SQLAlchemy Core implementation of the product repository port."""

from decimal import Decimal

from sqlalchemy import Engine, func, select

from src.domain import Product, ProductStatus
from src.infrastructure.database.schema import products


class SQLAlchemyProductRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, product_id: int) -> Product | None:
        with self._engine.connect() as connection:
            row = connection.execute(select(products).where(products.c.product_id == product_id)).mappings().first()
        return _to_product(row) if row else None

    def search(self, *, category_id: int | None = None, max_price: Decimal | None = None, in_stock: bool = True, query: str | None = None, limit: int = 5) -> list[Product]:
        conditions = []
        if category_id is not None:
            conditions.append(products.c.category_id == category_id)
        if max_price is not None:
            conditions.append(products.c.price_brl <= max_price)
        if in_stock:
            conditions.extend((products.c.status == ProductStatus.ACTIVE.value, products.c.stock_quantity > 0))
        if query:
            conditions.append(func.lower(products.c.name).like(f"%{query.casefold()}%"))
        with self._engine.connect() as connection:
            rows = connection.execute(select(products).where(*conditions).order_by(products.c.name).limit(limit)).mappings().all()
        return [_to_product(row) for row in rows]


def _to_product(row) -> Product:
    return Product(id=row["product_id"], name=row["name"], price_brl=Decimal(str(row["price_brl"])), category_id=row["category_id"], description=row["description"], stock_quantity=row["stock_quantity"], status=ProductStatus(row["status"]), specs=row["specs"], created_at=row["created_at"])
