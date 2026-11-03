"""Database engine setup and deterministic CSV ingestion."""

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url

from .schema import categories, customers, metadata, order_items, orders, products, promotions

PRODUCT_STATUSES = {"active", "discontinued", "coming_soon"}
ORDER_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}
PAYMENT_METHODS = {"pix", "debit", "boleto", "credit_3x", "credit_6x", "credit_12x"}


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    categories: int
    products: int
    promotions: int
    customers: int
    orders: int
    order_items: int


def create_database_engine(database_url: str | Path) -> Engine:
    """Create an engine from a portable SQLAlchemy URL or a local SQLite path."""
    engine = create_engine(_database_url(database_url))
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    initialize_schema(engine)
    return engine


def initialize_schema(engine: Engine) -> None:
    metadata.create_all(engine)


def ingest_csv_data(engine: Engine, data_dir: Path) -> IngestionSummary:
    """Replace operational data with validated CSV data from ``data_dir``."""
    initialize_schema(engine)
    with engine.begin() as connection:
        for table in (order_items, orders, promotions, products, customers, categories):
            connection.execute(table.delete())
        counts = (
            _ingest_categories(connection, data_dir / "categories.csv"),
            _ingest_products(connection, data_dir / "products.csv"),
            _ingest_promotions(connection, data_dir / "promotions.csv"),
            _ingest_customers(connection, data_dir / "customers.csv"),
            _ingest_orders(connection, data_dir / "orders.csv"),
            _ingest_order_items(connection, data_dir / "order_items.csv"),
        )
    return IngestionSummary(*counts)


def _database_url(database_url: str | Path) -> str:
    if isinstance(database_url, Path):
        return URL.create("sqlite+pysqlite", database=str(database_url)).render_as_string(hide_password=False)
    try:
        return str(make_url(database_url))
    except Exception as error:
        raise ValueError("database_url must be a SQLAlchemy URL or filesystem path") from error


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Data file was not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _ingest_categories(connection, path: Path) -> int:
    rows = [_typed(row, path, line, category_id=int) for line, row in enumerate(_rows(path), 2)]
    connection.execute(categories.insert(), rows)
    return len(rows)


def _ingest_products(connection, path: Path) -> int:
    rows = []
    for line, row in enumerate(_rows(path), 2):
        typed = _typed(row, path, line, product_id=int, category_id=int, stock_quantity=int)
        _require(typed["status"] in PRODUCT_STATUSES, path, line, "invalid product status")
        try:
            typed["price_brl"] = float(row["price_brl"])
            typed["specs"] = json.loads(row["specs"])
            typed["created_at"] = date.fromisoformat(row["created_at"])
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"{path}:{line}: invalid product data") from error
        rows.append(typed)
    connection.execute(products.insert(), rows)
    return len(rows)


def _ingest_promotions(connection, path: Path) -> int:
    rows = [_typed(row, path, line, promotion_id=int, product_id=int, discount_percent=float, is_active=_to_bool) for line, row in enumerate(_rows(path), 2)]
    connection.execute(promotions.insert(), rows)
    return len(rows)


def _ingest_customers(connection, path: Path) -> int:
    rows = [_typed(row, path, line, customer_id=int) for line, row in enumerate(_rows(path), 2)]
    connection.execute(customers.insert(), rows)
    return len(rows)


def _ingest_orders(connection, path: Path) -> int:
    rows = []
    for line, row in enumerate(_rows(path), 2):
        typed = _typed(row, path, line, order_id=int, customer_id=int)
        _require(typed["status"] in ORDER_STATUSES, path, line, "invalid order status")
        _require(typed["payment_method"] in PAYMENT_METHODS, path, line, "invalid payment method")
        try:
            typed["total_brl"] = float(row["total_brl"])
            typed["order_date"] = date.fromisoformat(row["order_date"])
            typed["estimated_delivery"] = date.fromisoformat(row["estimated_delivery"]) if row["estimated_delivery"] else None
        except ValueError as error:
            raise ValueError(f"{path}:{line}: invalid order data") from error
        rows.append(typed)
    connection.execute(orders.insert(), rows)
    return len(rows)


def _ingest_order_items(connection, path: Path) -> int:
    rows = [_typed(row, path, line, order_id=int, product_id=int, quantity=int) for line, row in enumerate(_rows(path), 2)]
    connection.execute(order_items.insert(), rows)
    return len(rows)


def _typed(row: dict[str, str], path: Path, line: int, **converters: object) -> dict[str, object]:
    typed: dict[str, object] = dict(row)
    for field, converter in converters.items():
        try:
            typed[field] = converter(row[field])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{path}:{line}: invalid {field}") from error
    return typed


def _to_bool(value: str) -> bool:
    if value not in {"0", "1"}:
        raise ValueError("must be 0 or 1")
    return value == "1"


def _require(condition: bool, path: Path, line: int, message: str) -> None:
    if not condition:
        raise ValueError(f"{path}:{line}: {message}")
