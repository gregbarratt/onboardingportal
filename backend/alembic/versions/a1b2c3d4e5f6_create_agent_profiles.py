"""create agent profiles

Revision ID: a1b2c3d4e5f6
Revises: f3a7b9c2d4e6
Create Date: 2026-05-12 15:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f3a7b9c2d4e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="Registered",
            nullable=False,
        ),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postcode", sa.String(length=20), nullable=True),
        sa.Column("commission_bank_name", sa.String(length=255), nullable=True),
        sa.Column("commission_account_name", sa.String(length=255), nullable=True),
        sa.Column("commission_sort_code", sa.String(length=20), nullable=True),
        sa.Column("commission_account_number", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_profiles_agent_id"), "agent_profiles", ["agent_id"], unique=True)
    op.create_index(op.f("ix_agent_profiles_email"), "agent_profiles", ["email"], unique=False)
    op.create_index(op.f("ix_agent_profiles_status"), "agent_profiles", ["status"], unique=False)
    op.create_index(op.f("ix_agent_profiles_user_id"), "agent_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_profiles_user_id"), table_name="agent_profiles")
    op.drop_index(op.f("ix_agent_profiles_status"), table_name="agent_profiles")
    op.drop_index(op.f("ix_agent_profiles_email"), table_name="agent_profiles")
    op.drop_index(op.f("ix_agent_profiles_agent_id"), table_name="agent_profiles")
    op.drop_table("agent_profiles")
