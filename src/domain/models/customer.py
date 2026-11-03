"""Customer entity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str
    city: str
