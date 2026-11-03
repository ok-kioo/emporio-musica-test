"""Database infrastructure and SQLite adapters."""

from .sqlite import IngestionSummary, connect, ingest_csv_data
from .repositories import (
    SQLiteCustomerRepository,
    SQLiteOrderRepository,
    SQLiteProductRepository,
    SQLitePromotionRepository,
)

__all__ = [
    "IngestionSummary", "SQLiteCustomerRepository", "SQLiteOrderRepository", "SQLiteProductRepository",
    "SQLitePromotionRepository", "connect", "ingest_csv_data"
]
