"""Centralized and reproducible prototype configuration."""

from datetime import date


STORE_NAME = "Empório da Música"
STORE_SUPPORT_PHONE = "(67) 3341-4444"
ASSISTANT_PHONE = "(67) 3321-4500"
STORE_EMAIL = "contato@emporiodamusica.com.br"

REFERENCE_DATE = date(2025, 6, 16)
ROUTER_CONFIDENCE_THRESHOLD = 0.70
POLICY_RELEVANCE_THRESHOLD = 0.35
MAX_ORDER_LOOKUP_ATTEMPTS = 3
ORDER_LOOKUP_BLOCK_MINUTES = 15
DELIVERY_DATE_TOLERANCE_DAYS = 3

ORDER_STATUS_LABELS = {
    "pending": "aguardando confirmação",
    "confirmed": "confirmado",
    "shipped": "a caminho",
    "delivered": "entregue",
    "cancelled": "cancelado",
}
