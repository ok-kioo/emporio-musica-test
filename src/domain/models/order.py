"""Order and OrderItem entity."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    PIX = "pix"
    DEBIT = "debit"
    BOLETO = "boleto"
    CREDIT_3X = "credit_3x"
    CREDIT_6X = "credit_6x"
    CREDIT_12X = "credit_12x"


@dataclass(frozen=True, slots=True)
class Order:
    id: int
    customer_id: int
    order_date: date
    status: OrderStatus
    total_brl: Decimal
    payment_method: PaymentMethod
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class OrderItem:
    order_id: int
    product_id: int
    quantity: int