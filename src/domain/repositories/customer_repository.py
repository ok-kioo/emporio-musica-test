"""Customer repository interface."""

from typing import Protocol

from src.domain import Customer


class CustomerRepository(Protocol):
    def find_by_phone(self, phone: str) -> Customer | None: ...