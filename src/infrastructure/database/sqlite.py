"""SQLite database infrastructure and ingestion"""

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .schema import _SCHEMA

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

def connect(database_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def ingest_csv_data(connection: sqlite3.Connection, data_dir: Path) -> IngestionSummary:
    """Substitui o conteúdo operacional pelos CSVs validados de ``data_dir``."""
    connection.executescript(_SCHEMA)
    _clear_tables(connection)

    categories = _ingest_categories(connection, data_dir / "categories.csv")
    products = _ingest_products(connection, data_dir / "products.csv")
    promotions = _ingest_promotions(connection, data_dir / "promotions.csv")
    customers = _ingest_customers(connection, data_dir / "customers.csv")
    orders = _ingest_orders(connection, data_dir / "orders.csv")
    order_items = _ingest_order_items(connection, data_dir / "order_items.csv")
    connection.commit()
    return IngestionSummary(categories, products, promotions, customers, orders, order_items)


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {path}")
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _ingest_categories(connection: sqlite3.Connection, path: Path) -> int:
    rows = [_typed(row, path, line, category_id=int) for line, row in enumerate(_rows(path), 2)]
    connection.executemany("INSERT INTO categories VALUES (:category_id, :name, :description)", rows)
    return len(rows)


def _ingest_products(connection: sqlite3.Connection, path: Path) -> int:
    rows = []
    for line, row in enumerate(_rows(path), 2):
        row = _typed(row, path, line, product_id=int, price_brl=float, category_id=int, stock_quantity=int)
        _require(row["status"] in PRODUCT_STATUSES, path, line, "status de produto inválido")
        try:
            row["specs"] = json.dumps(json.loads(row["specs"]), ensure_ascii=False, sort_keys=True)
            date.fromisoformat(str(row["created_at"]))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"{path}:{line}: specs ou created_at inválido") from error
        rows.append(row)
    connection.executemany(
        """INSERT INTO products
        (product_id, price_brl, name, category_id, description, stock_quantity, status, specs, created_at)
        VALUES (:product_id, :price_brl, :name, :category_id, :description, :stock_quantity, :status, :specs, :created_at)""",
        rows,
    )
    return len(rows)


def _ingest_promotions(connection: sqlite3.Connection, path: Path) -> int:
    rows = [_typed(row, path, line, promotion_id=int, product_id=int, discount_percent=float, is_active=int)
            for line, row in enumerate(_rows(path), 2)]
    if any(row["is_active"] not in (0, 1) for row in rows):
        raise ValueError(f"{path}: is_active deve ser 0 ou 1")
    connection.executemany(
        "INSERT INTO promotions VALUES (:promotion_id, :product_id, :discount_percent, :description, :is_active)", rows
    )
    return len(rows)


def _ingest_customers(connection: sqlite3.Connection, path: Path) -> int:
    rows = [_typed(row, path, line, customer_id=int) for line, row in enumerate(_rows(path), 2)]
    connection.executemany("INSERT INTO customers VALUES (:customer_id, :name, :phone, :email, :city)", rows)
    return len(rows)


def _ingest_orders(connection: sqlite3.Connection, path: Path) -> int:
    rows = []
    for line, row in enumerate(_rows(path), 2):
        row = _typed(row, path, line, order_id=int, customer_id=int, total_brl=float)
        _require(row["status"] in ORDER_STATUSES, path, line, "status de pedido inválido")
        _require(row["payment_method"] in PAYMENT_METHODS, path, line, "forma de pagamento inválida")
        try:
            date.fromisoformat(str(row["order_date"]))
            if row["estimated_delivery"]:
                date.fromisoformat(str(row["estimated_delivery"]))
        except ValueError as error:
            raise ValueError(f"{path}:{line}: data inválida") from error
        rows.append(row)
    connection.executemany(
        """INSERT INTO orders
        (order_id, customer_id, order_date, status, total_brl, payment_method, tracking_code, estimated_delivery, notes)
        VALUES (:order_id, :customer_id, :order_date, :status, :total_brl, :payment_method, :tracking_code,
        :estimated_delivery, :notes)""",
        rows,
    )
    return len(rows)


def _ingest_order_items(connection: sqlite3.Connection, path: Path) -> int:
    rows = [_typed(row, path, line, order_id=int, product_id=int, quantity=int)
            for line, row in enumerate(_rows(path), 2)]
    connection.executemany("INSERT INTO order_items VALUES (:order_id, :product_id, :quantity)", rows)
    return len(rows)


def _typed(row: dict[str, str], path: Path, line: int, **converters: type) -> dict[str, object]:
    typed: dict[str, object] = dict(row)
    for field, converter in converters.items():
        try:
            typed[field] = converter(row[field])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{path}:{line}: {field} inválido") from error
    return typed


def _require(condition: bool, path: Path, line: int, message: str) -> None:
    if not condition:
        raise ValueError(f"{path}:{line}: {message}")


def _clear_tables(connection: sqlite3.Connection) -> None:
    for table in ("order_items", "orders", "promotions", "products", "customers", "categories"):
        connection.execute(f"DELETE FROM {table}")

