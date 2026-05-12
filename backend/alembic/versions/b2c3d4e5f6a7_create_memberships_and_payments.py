"""create memberships and payments

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-12 15:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("membership_type", sa.String(length=100), nullable=True),
        sa.Column("setup_fee_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("monthly_fee_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column(
            "membership_status",
            sa.String(length=50),
            server_default="Payment Pending",
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.String(length=50),
            server_default="Not Started",
            nullable=False,
        ),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("last_payment_date", sa.Date(), nullable=True),
        sa.Column("next_payment_date", sa.Date(), nullable=True),
        sa.Column("failed_payment_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("access_level", sa.String(length=100), nullable=True),
        sa.Column("cancellation_date", sa.Date(), nullable=True),
        sa.Column("suspension_date", sa.Date(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memberships_agent_id"), "memberships", ["agent_id"], unique=True)
    op.create_index(op.f("ix_memberships_membership_status"), "memberships", ["membership_status"], unique=False)
    op.create_index(op.f("ix_memberships_payment_status"), "memberships", ["payment_status"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="GBP", nullable=False),
        sa.Column("payment_type", sa.String(length=100), nullable=False),
        sa.Column("payment_status", sa.String(length=50), server_default="Pending", nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("stripe_payment_id", sa.String(length=255), nullable=True),
        sa.Column("invoice_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_agent_id"), "payments", ["agent_id"], unique=False)
    op.create_index(op.f("ix_payments_payment_status"), "payments", ["payment_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_payment_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_agent_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_memberships_payment_status"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_membership_status"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_agent_id"), table_name="memberships")
    op.drop_table("memberships")

