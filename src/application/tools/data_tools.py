"""Catalog and order lookups with explicit, source-backed result states."""

import re
import unicodedata

from src.domain import AccessLevel, Session, Source, ToolResult, ToolStatus
from src.domain.repositories import OrderRepository, ProductRepository, PromotionRepository


class DataTools:
    def __init__(self, products: ProductRepository, promotions: PromotionRepository, orders: OrderRepository) -> None:
        self._products = products
        self._promotions = promotions
        self._orders = orders

    def product_by_name(self, query: str) -> ToolResult:
        normalized_query = _normalize(query)
        candidates = [product for product in self._products.search(in_stock=False, limit=100) if normalized_query in _normalize(product.name)]
        if not candidates:
            return ToolResult(ToolStatus.NOT_FOUND, message="No product matched the supplied name.")
        if len(candidates) > 1:
            return ToolResult(ToolStatus.AMBIGUOUS, data=[{"id": product.id, "name": product.name} for product in candidates[:5]], message="More than one product matched.")
        product = candidates[0]
        active_promotions = self._promotions.active_for_product(product.id)
        data = {
            "product_id": product.id,
            "name": product.name,
            "price_brl": str(product.price_brl),
            "stock_quantity": product.stock_quantity,
            "status": product.status.value,
            "available": product.is_available,
            "promotions": [{"discount_percent": str(item.discount_percent), "description": item.description} for item in active_promotions],
        }
        return ToolResult(ToolStatus.SUCCESS, data=data, sources=(Source(source="products.csv", record_id=product.id),))

    def order_status(self, order_id: int, session: Session) -> ToolResult:
        if session.access_level < AccessLevel.VERIFIED_CHANNEL or session.customer_id is None:
            return ToolResult(ToolStatus.NOT_FOUND, message="Order lookup requires a verified channel.")
        order = self._orders.get_for_customer(order_id, session.customer_id)
        if not order:
            return ToolResult(ToolStatus.NOT_FOUND, message="Order was not found for this channel.")
        return ToolResult(
            ToolStatus.SUCCESS,
            data={
                "order_id": order.id, "status": order.status.value, "estimated_delivery": str(order.estimated_delivery) if order.estimated_delivery else None,
                "order_date": str(order.order_date), "tracking_code": _mask_tracking(order.tracking_code), "notes": order.notes,
            },
            sources=(Source(source="orders.csv", record_id=order.id),),
        )


def _normalize(value: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(character) != "Mn")


def _mask_tracking(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:2]}***{value[-2:]}"
