import json
from pathlib import Path

from src.infrastructure.database import connect, ingest_csv_data


DATA_DIR = Path(__file__).parents[1] / "data"


def test_ingestion_loads_all_source_records(tmp_path: Path) -> None:
    connection = connect(tmp_path / "emporio.sqlite3")
    summary = ingest_csv_data(connection, DATA_DIR)

    assert summary.products == 65
    assert summary.categories == 9
    assert summary.promotions == 25
    assert summary.orders == 20
    assert summary.order_items == 22
    assert summary.customers == 50


def test_ingestion_parses_product_specs_and_relations(tmp_path: Path) -> None:
    connection = connect(tmp_path / "emporio.sqlite3")
    ingest_csv_data(connection, DATA_DIR)

    product = connection.execute("SELECT specs, category_id FROM products WHERE product_id = 81").fetchone()
    assert json.loads(product["specs"])["strings"] == "nylon"
    assert product["category_id"] == 5
    assert connection.execute("SELECT count(*) FROM order_items").fetchone()[0] == 22
