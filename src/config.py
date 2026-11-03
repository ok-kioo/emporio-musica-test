"""Centralized and reproducible prototype configuration."""

from datetime import date
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

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


@dataclass(frozen=True, slots=True)
class PolicyRuntimeSettings:
    database_url: str
    policy_root: Path
    vector_backend: str
    vector_directory: Path
    embedding_provider: str
    embedding_api_key: str | None
    decision_api_key: str | None = None
    decision_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    text_api_key: str | None = None
    text_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    @classmethod
    def from_environment(cls, project_root: Path) -> "PolicyRuntimeSettings":
        load_dotenv(project_root / ".env", override=False)
        return cls(
            database_url=os.path.expandvars(
                os.getenv("DATABASE_URL", f"sqlite:///{project_root / 'data' / 'emporio.db'}")
            ),
            policy_root=project_root / "data" / "policies",
            vector_backend=os.getenv("POLICY_VECTOR_BACKEND", "file"),
            vector_directory=Path(os.path.expandvars(
                os.getenv("POLICY_VECTOR_DIRECTORY", str(project_root / "data" / "policy_vectors"))
            )),
            embedding_provider=os.getenv("POLICY_EMBEDDING_PROVIDER", "hash"),
            embedding_api_key=os.getenv("OPENROUTER_EMBEDDING_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            decision_api_key=os.getenv("OPENROUTER_DECISION_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            decision_model=os.getenv("OPENROUTER_DECISION_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
            text_api_key=os.getenv("OPENROUTER_TEXT_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            text_model=os.getenv("OPENROUTER_TEXT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
        )

ORDER_STATUS_LABELS = {
    "pending": "aguardando confirmação",
    "confirmed": "confirmado",
    "shipped": "a caminho",
    "delivered": "entregue",
    "cancelled": "cancelado",
}
