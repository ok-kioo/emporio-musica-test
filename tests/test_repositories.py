from decimal import Decimal
from pathlib import Path

from src.domain import OrderStatus, ProductStatus
from src.infrastructure.database import (
    SQLAlchemyCustomerRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyProductRepository,
    SQLAlchemyPromotionRepository,
    create_database_engine,
    ingest_csv_data,
)


DATA_DIR = Path(__file__).parents[1] / "data"


def _database(tmp_path: Path):
    engine = create_database_engine(tmp_path / "emporio.sqlite3")
    ingest_csv_data(engine, DATA_DIR)
    return engine


def test_product_repository_returns_domain_entity(tmp_path: Path) -> None:
    products = SQLAlchemyProductRepository(_database(tmp_path))

    product = products.get(81)

    assert product is not None
    assert product.status is ProductStatus.ACTIVE
    assert product.price_brl == Decimal("599.9")
    assert product.is_available


def test_catalog_query_is_filtered_by_typed_criteria(tmp_path: Path) -> None:
    products = SQLAlchemyProductRepository(_database(tmp_path))

    matches = products.search(category_id=5, max_price=Decimal("1000"), query="yamaha")

    assert matches
    assert all(product.category_id == 5 for product in matches)
    assert all(product.price_brl <= Decimal("1000") for product in matches)


def test_order_repository_always_scopes_order_to_customer(tmp_path: Path) -> None:
    orders = SQLAlchemyOrderRepository(_database(tmp_path))

    own_order = orders.get_for_customer(order_id=1, customer_id=3)
    foreign_order = orders.get_for_customer(order_id=1, customer_id=7)

    assert own_order is not None
    assert own_order.status is OrderStatus.DELIVERED
    assert foreign_order is None


def test_customer_and_promotion_repositories_map_entities(tmp_path: Path) -> None:
    connection = _database(tmp_path)
    customer = SQLAlchemyCustomerRepository(connection).find_by_phone("(67) 99812-3456")
    promotions = SQLAlchemyPromotionRepository(connection).active_for_product(102)

    assert customer is not None
    assert customer.id == 1
    assert all(promotion.is_active for promotion in promotions)
