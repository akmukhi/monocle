"""Add normalized cloud + AI cost tables.

Revision ID: 0002_cost_tables
Revises: 0001_auth_orgs
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0002_cost_tables"
down_revision = "0001_auth_orgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE cloud_provider AS ENUM ('AWS', 'GCP')")
    op.execute("CREATE TYPE ai_provider AS ENUM ('OPENAI', 'ANTHROPIC')")

    op.create_table(
        "cloud_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.Enum(name="cloud_provider"), nullable=False),
        sa.Column("account_or_project", sa.String(length=128), nullable=True),
        sa.Column("service_key", sa.String(length=200), nullable=True),
        sa.Column("usage_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("source_key", sa.String(length=200), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "raw_source",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "provider", "source_key", name="uq_cloud_costs_org_provider_source_key"),
    )
    op.create_index("ix_cloud_costs_org_id", "cloud_costs", ["org_id"])
    op.create_index("ix_cloud_costs_usage_start", "cloud_costs", ["usage_start"])
    op.create_index("ix_cloud_costs_provider_usage_start", "cloud_costs", ["provider", "usage_start"])
    op.create_index("ix_cloud_costs_org_time", "cloud_costs", ["org_id", "usage_start"])
    op.create_index("ix_cloud_costs_account_or_project", "cloud_costs", ["account_or_project"])
    op.create_index("ix_cloud_costs_service_key", "cloud_costs", ["service_key"])
    op.create_index("ix_cloud_costs_tags_gin", "cloud_costs", ["tags"], postgresql_using="gin")

    op.create_table(
        "ai_usage_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.Enum(name="ai_provider"), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("usage_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("feature_key", sa.String(length=120), nullable=True),
        sa.Column("source_key", sa.String(length=200), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "raw_source",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "provider", "source_key", name="uq_ai_usage_costs_org_provider_source_key"),
    )
    op.create_index("ix_ai_usage_costs_org_id", "ai_usage_costs", ["org_id"])
    op.create_index("ix_ai_usage_costs_usage_start", "ai_usage_costs", ["usage_start"])
    op.create_index("ix_ai_usage_costs_provider_usage_start", "ai_usage_costs", ["provider", "usage_start"])
    op.create_index("ix_ai_usage_costs_org_time", "ai_usage_costs", ["org_id", "usage_start"])
    op.create_index("ix_ai_usage_costs_model", "ai_usage_costs", ["model"])
    op.create_index("ix_ai_usage_costs_feature_key", "ai_usage_costs", ["feature_key"])
    op.create_index("ix_ai_usage_costs_tags_gin", "ai_usage_costs", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_ai_usage_costs_tags_gin", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_feature_key", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_model", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_org_time", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_provider_usage_start", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_usage_start", table_name="ai_usage_costs")
    op.drop_index("ix_ai_usage_costs_org_id", table_name="ai_usage_costs")
    op.drop_table("ai_usage_costs")

    op.drop_index("ix_cloud_costs_tags_gin", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_service_key", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_account_or_project", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_org_time", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_provider_usage_start", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_usage_start", table_name="cloud_costs")
    op.drop_index("ix_cloud_costs_org_id", table_name="cloud_costs")
    op.drop_table("cloud_costs")

    op.execute("DROP TYPE ai_provider")
    op.execute("DROP TYPE cloud_provider")

