from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, func, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# SQLAlchemy index dialect kwarg is named `postgresql_using`
POSTGRES_GIN = "gin"


class CloudProvider(str, enum.Enum):
    aws = "AWS"
    gcp = "GCP"


class AIProvider(str, enum.Enum):
    openai = "OPENAI"
    anthropic = "ANTHROPIC"


class CloudCost(Base):
    __tablename__ = "cloud_costs"
    __table_args__ = (
        Index("ix_cloud_costs_org_time", "org_id", "usage_start"),
        Index("ix_cloud_costs_provider_time", "provider", "usage_start"),
        Index("ix_cloud_costs_tags_gin", "tags", postgresql_using=POSTGRES_GIN),
        Index("ix_cloud_costs_source_key", "org_id", "provider", "source_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )

    provider: Mapped[CloudProvider] = mapped_column(Enum(CloudProvider, name="cloud_provider"), nullable=False)

    # AWS: account_id. GCP: project_id / billing_account (MVP: flexible).
    account_or_project: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Service name/key as a string for MVP; we’ll add a `services` FK later.
    service_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    usage_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    usage_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Idempotency key derived from provider payload (e.g., CE group keys + day).
    source_key: Mapped[str] = mapped_column(String(200), nullable=False)

    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_source: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIUsageCost(Base):
    __tablename__ = "ai_usage_costs"
    __table_args__ = (
        Index("ix_ai_usage_costs_org_time", "org_id", "usage_start"),
        Index("ix_ai_usage_costs_provider_time", "provider", "usage_start"),
        Index("ix_ai_usage_costs_tags_gin", "tags", postgresql_using=POSTGRES_GIN),
        Index("ix_ai_usage_costs_source_key", "org_id", "provider", "source_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )

    provider: Mapped[AIProvider] = mapped_column(Enum(AIProvider, name="ai_provider"), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    usage_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    usage_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Optional feature attribution (from app instrumentation / tags mapping).
    feature_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    # Idempotency key derived from provider payload (e.g., usage bucket + model).
    source_key: Mapped[str] = mapped_column(String(200), nullable=False)

    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_source: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

