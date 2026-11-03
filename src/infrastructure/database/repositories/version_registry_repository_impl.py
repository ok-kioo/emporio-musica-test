"""SQL-backed active-policy pointer and rollback history."""

from datetime import datetime, timezone

from sqlalchemy import Engine, insert, select, update

from src.domain import PolicyVersion
from src.infrastructure.database.schema import policy_versions


class SQLAlchemyPolicyVersionRegistryRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def active(self) -> PolicyVersion | None:
        with self._engine.connect() as connection:
            row = connection.execute(select(policy_versions).where(policy_versions.c.is_active.is_(True))).mappings().first()
        return _to_policy_version(row) if row else None

    def activate(self, version: str) -> PolicyVersion:
        now = datetime.now(timezone.utc)
        with self._engine.begin() as connection:
            connection.execute(update(policy_versions).values(is_active=False))
            exists = connection.execute(select(policy_versions.c.policy_version).where(policy_versions.c.policy_version == version)).scalar_one_or_none()
            if exists is None:
                connection.execute(insert(policy_versions).values(policy_version=version, is_active=True, activated_at=now))
            else:
                connection.execute(update(policy_versions).where(policy_versions.c.policy_version == version).values(is_active=True, activated_at=now))
        return PolicyVersion(version=version, is_active=True, activated_at=now)

    def rollback(self) -> PolicyVersion | None:
        current = self.active()
        with self._engine.begin() as connection:
            statement = select(policy_versions.c.policy_version).where(policy_versions.c.is_active.is_(False))
            if current is not None:
                statement = statement.where(policy_versions.c.policy_version != current)
            previous = connection.execute(statement.order_by(policy_versions.c.activated_at.desc()).limit(1)).scalar_one_or_none()
            if previous is None:
                return None
            now = datetime.now(timezone.utc)
            connection.execute(update(policy_versions).values(is_active=False))
            connection.execute(update(policy_versions).where(policy_versions.c.policy_version == previous).values(is_active=True, activated_at=now))
            return PolicyVersion(version=previous, is_active=True, activated_at=now)

    def list(self) -> list[PolicyVersion]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(policy_versions).order_by(policy_versions.c.activated_at.desc())).mappings().all()
        return [_to_policy_version(row) for row in rows]


def _to_policy_version(row) -> PolicyVersion:
    return PolicyVersion(version=row["policy_version"], is_active=row["is_active"], activated_at=row["activated_at"])
