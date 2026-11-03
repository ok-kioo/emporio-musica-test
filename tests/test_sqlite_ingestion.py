from pathlib import Path

from sqlalchemy import func, select

from src.infrastructure.database import create_database_engine, ingest_csv_data
from src.infrastructure.database.schema import order_items, products


DATA_DIR = Path(__file__).parents[1] / "data"


def test_database_engine_accepts_a_sqlalchemy_url() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    assert engine.dialect.name == "sqlite"


def test_ingestion_loads_all_source_records(tmp_path: Path) -> None:
    engine = create_database_engine(tmp_path / "emporio.sqlite3")
    summary = ingest_csv_data(engine, DATA_DIR)

    assert summary.products == 65
    assert summary.categories == 9
    assert summary.promotions == 25
    assert summary.orders == 20
    assert summary.order_items == 22
    assert summary.customers == 50


def test_ingestion_parses_product_specs_and_relations(tmp_path: Path) -> None:
    engine = create_database_engine(tmp_path / "emporio.sqlite3")
    ingest_csv_data(engine, DATA_DIR)

    with engine.connect() as connection:
        product = connection.execute(select(products.c.specs, products.c.category_id).where(products.c.product_id == 81)).mappings().one()
        item_count = connection.execute(select(func.count()).select_from(order_items)).scalar_one()
    assert product["specs"]["strings"] == "nylon"
    assert product["category_id"] == 5
    assert item_count == 22
