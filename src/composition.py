"""Composition root for versioned policy retrieval."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select

from src.application.auth_service import AuthService
from src.application.decisions import CompositeDecisionModel, LLMDecisionModel, RulesDecisionModel
from src.application.orchestrator import ChatOrchestrator
from src.application.response_generation import EvidenceResponseGenerator
from src.application.router import Router
from src.application.tools import DataTools
from src.domain.policies.policy_engine import PolicyEngine
from src.application.policies.ports import EmbeddingClient
from src.config import PolicyRuntimeSettings
from src.domain.repositories import PolicyVersionRegistryRepository
from src.infrastructure.database import (
    SQLAlchemyCustomerRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyPolicyVersionRegistryRepository,
    SQLAlchemyProductRepository,
    SQLAlchemyPromotionRepository,
    SQLAlchemySessionRepository,
    create_database_engine,
    ingest_csv_data,
)
from src.infrastructure.database.schema import products
from src.infrastructure.llm import OpenRouterDecisionClient, OpenRouterEmbeddingClient, OpenRouterTextClient
from src.infrastructure.policies import PolicyPublisher
from src.infrastructure.policies.rules_loader import load_ruleset
from src.infrastructure.retrieval import ChromaPolicyVectorStore, DeterministicHashEmbeddingClient, FilePolicyIndex, VectorPolicyIndex


@dataclass(frozen=True, slots=True)
class PolicyRuntime:
    publisher: PolicyPublisher
    registry: PolicyVersionRegistryRepository
    index: VectorPolicyIndex


@dataclass(frozen=True, slots=True)
class ChatRuntime:
    authenticator: AuthService
    orchestrator: ChatOrchestrator
    policy_version: str


def build_policy_runtime(settings: PolicyRuntimeSettings) -> PolicyRuntime:
    embeddings = _embeddings(settings)
    if settings.vector_backend == "file":
        store = FilePolicyIndex(settings.vector_directory, embeddings)
    elif settings.vector_backend == "chroma":
        store = ChromaPolicyVectorStore(settings.vector_directory)
    else:
        raise ValueError("POLICY_VECTOR_BACKEND must be 'file' or 'chroma'")
    index = VectorPolicyIndex(store, embeddings)
    registry = SQLAlchemyPolicyVersionRegistryRepository(create_database_engine(settings.database_url))
    return PolicyRuntime(PolicyPublisher(settings.policy_root, index, registry), registry, index)


def build_chat_runtime(settings: PolicyRuntimeSettings, data_directory: Path) -> ChatRuntime:
    """Compose the customer chat using local deterministic adapters by default."""
    engine = create_database_engine(settings.database_url)
    with engine.connect() as connection:
        has_products = bool(connection.scalar(select(func.count()).select_from(products)))
    if not has_products:
        ingest_csv_data(engine, data_directory)
    sessions = SQLAlchemySessionRepository(engine)
    authenticator = AuthService(SQLAlchemyCustomerRepository(engine), sessions)
    tools = DataTools(
        SQLAlchemyProductRepository(engine), SQLAlchemyPromotionRepository(engine), SQLAlchemyOrderRepository(engine)
    )
    policy_runtime = build_policy_runtime(settings)
    active = policy_runtime.registry.active()
    if active is None:
        policy_runtime.publisher.publish("2.1")
        active = policy_runtime.registry.active()
    version, ruleset = load_ruleset(settings.policy_root / f"v{active.version}" / "rules.yaml")
    rule_decision_model = RulesDecisionModel()
    decision_model = rule_decision_model
    if settings.decision_api_key:
        decision_model = CompositeDecisionModel(
            rule_decision_model,
            LLMDecisionModel(
                OpenRouterDecisionClient(api_key=settings.decision_api_key, model=settings.decision_model)
            ),
        )
    orchestrator = ChatOrchestrator(
        Router(decision_model), sessions, tools, policy_runtime.index, PolicyEngine({version: ruleset})
    )
    if settings.text_api_key:
        orchestrator.set_response_generator(
            EvidenceResponseGenerator(OpenRouterTextClient(api_key=settings.text_api_key, model=settings.text_model))
        )
    return ChatRuntime(authenticator, orchestrator, active.version)


def _embeddings(settings: PolicyRuntimeSettings) -> EmbeddingClient:
    if settings.embedding_provider == "hash":
        return DeterministicHashEmbeddingClient()
    if settings.embedding_provider == "openrouter":
        if not settings.embedding_api_key:
            raise ValueError("OPENROUTER_EMBEDDING_API_KEY is required for POLICY_EMBEDDING_PROVIDER=openrouter")
        return OpenRouterEmbeddingClient(api_key=settings.embedding_api_key)
    raise ValueError("POLICY_EMBEDDING_PROVIDER must be 'hash' or 'openrouter'")
