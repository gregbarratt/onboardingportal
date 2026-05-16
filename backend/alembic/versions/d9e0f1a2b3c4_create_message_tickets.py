"""create message tickets

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-05-16 09:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d9e0f1a2b3c4"
down_revision: str | Sequence[str] | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="Open", nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_tickets_agent_id"), "support_tickets", ["agent_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_created_by_user_id"), "support_tickets", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_last_message_at"), "support_tickets", ["last_message_at"], unique=False)
    op.create_index(op.f("ix_support_tickets_organization_id"), "support_tickets", ["organization_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_status"), "support_tickets", ["status"], unique=False)

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("internal_note", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_ticket_messages_sender_user_id"), "support_ticket_messages", ["sender_user_id"], unique=False)
    op.create_index(op.f("ix_support_ticket_messages_ticket_id"), "support_ticket_messages", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_support_ticket_messages_ticket_id"), table_name="support_ticket_messages")
    op.drop_index(op.f("ix_support_ticket_messages_sender_user_id"), table_name="support_ticket_messages")
    op.drop_table("support_ticket_messages")
    op.drop_index(op.f("ix_support_tickets_status"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_organization_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_last_message_at"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_created_by_user_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_agent_id"), table_name="support_tickets")
    op.drop_table("support_tickets")
