"""create compliance centre

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-13 09:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.core.compliance import DEFAULT_COMPLIANCE_POLICIES


revision: str = "f8a9b0c1d2e3"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("policy_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=50), server_default="1.0", nullable=False),
        sa.Column("requires_acceptance", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("published_status", sa.String(length=50), server_default="Published", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compliance_policies_policy_type"), "compliance_policies", ["policy_type"], unique=False)
    op.create_index(
        op.f("ix_compliance_policies_published_status"),
        "compliance_policies",
        ["published_status"],
        unique=False,
    )

    compliance_policies_table = sa.table(
        "compliance_policies",
        sa.column("title", sa.String),
        sa.column("policy_type", sa.String),
        sa.column("content", sa.Text),
        sa.column("version", sa.String),
        sa.column("requires_acceptance", sa.Boolean),
        sa.column("published_status", sa.String),
    )
    op.bulk_insert(compliance_policies_table, list(DEFAULT_COMPLIANCE_POLICIES))

    op.create_table(
        "policy_acceptances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("accepted_by", sa.Integer(), nullable=False),
        sa.Column("accepted_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["compliance_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "policy_id", name="uq_policy_acceptances_agent_policy"),
    )
    op.create_index(op.f("ix_policy_acceptances_accepted_by"), "policy_acceptances", ["accepted_by"], unique=False)
    op.create_index(op.f("ix_policy_acceptances_agent_id"), "policy_acceptances", ["agent_id"], unique=False)
    op.create_index(op.f("ix_policy_acceptances_policy_id"), "policy_acceptances", ["policy_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_policy_acceptances_policy_id"), table_name="policy_acceptances")
    op.drop_index(op.f("ix_policy_acceptances_agent_id"), table_name="policy_acceptances")
    op.drop_index(op.f("ix_policy_acceptances_accepted_by"), table_name="policy_acceptances")
    op.drop_table("policy_acceptances")
    op.drop_index(op.f("ix_compliance_policies_published_status"), table_name="compliance_policies")
    op.drop_index(op.f("ix_compliance_policies_policy_type"), table_name="compliance_policies")
    op.drop_table("compliance_policies")
