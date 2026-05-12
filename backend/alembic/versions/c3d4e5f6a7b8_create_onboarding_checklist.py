"""create onboarding checklist

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-12 16:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.core.onboarding_statuses import DEFAULT_ONBOARDING_STEPS


revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "onboarding_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("approval_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_steps_sort_order"), "onboarding_steps", ["sort_order"], unique=True)

    onboarding_steps_table = sa.table(
        "onboarding_steps",
        sa.column("sort_order", sa.Integer),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("required", sa.Boolean),
        sa.column("approval_required", sa.Boolean),
    )
    op.bulk_insert(onboarding_steps_table, list(DEFAULT_ONBOARDING_STEPS))

    op.create_table(
        "agent_onboarding_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("completion_status", sa.String(length=50), server_default="Not Started", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("completed_by", sa.Integer(), nullable=True),
        sa.Column("evidence_file_or_link", sa.String(length=500), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("agent_notes", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["step_id"], ["onboarding_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "step_id", name="uq_agent_onboarding_progress_agent_step"),
    )
    op.create_index(op.f("ix_agent_onboarding_progress_agent_id"), "agent_onboarding_progress", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_agent_onboarding_progress_completion_status"),
        "agent_onboarding_progress",
        ["completion_status"],
        unique=False,
    )
    op.create_index(op.f("ix_agent_onboarding_progress_step_id"), "agent_onboarding_progress", ["step_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_onboarding_progress_step_id"), table_name="agent_onboarding_progress")
    op.drop_index(op.f("ix_agent_onboarding_progress_completion_status"), table_name="agent_onboarding_progress")
    op.drop_index(op.f("ix_agent_onboarding_progress_agent_id"), table_name="agent_onboarding_progress")
    op.drop_table("agent_onboarding_progress")
    op.drop_index(op.f("ix_onboarding_steps_sort_order"), table_name="onboarding_steps")
    op.drop_table("onboarding_steps")
