"""create live calls and attendance

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-12 19:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_training_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("session_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("trainer_host", sa.String(length=255), nullable=True),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("recording_link", sa.String(length=500), nullable=True),
        sa.Column("attendance_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("related_training_module_id", sa.Integer(), nullable=True),
        sa.Column("follow_up_quiz_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("certificate_issued", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["related_training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_live_training_sessions_date"), "live_training_sessions", ["date"], unique=False)
    op.create_index(
        op.f("ix_live_training_sessions_related_training_module_id"),
        "live_training_sessions",
        ["related_training_module_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_live_training_sessions_session_type"),
        "live_training_sessions",
        ["session_type"],
        unique=False,
    )

    op.create_table(
        "attendance_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("attendance_status", sa.String(length=50), server_default="Invited", nullable=False),
        sa.Column("join_time", sa.Time(), nullable=True),
        sa.Column("leave_time", sa.Time(), nullable=True),
        sa.Column("duration_attended", sa.Integer(), nullable=True),
        sa.Column("marked_by", sa.Integer(), nullable=True),
        sa.Column("marked_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("watched_recording", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recording_completed_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["live_training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "agent_id", name="uq_attendance_logs_session_agent"),
    )
    op.create_index(op.f("ix_attendance_logs_agent_id"), "attendance_logs", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_attendance_logs_attendance_status"),
        "attendance_logs",
        ["attendance_status"],
        unique=False,
    )
    op.create_index(op.f("ix_attendance_logs_session_id"), "attendance_logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_attendance_logs_session_id"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_attendance_status"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_agent_id"), table_name="attendance_logs")
    op.drop_table("attendance_logs")
    op.drop_index(op.f("ix_live_training_sessions_session_type"), table_name="live_training_sessions")
    op.drop_index(op.f("ix_live_training_sessions_related_training_module_id"), table_name="live_training_sessions")
    op.drop_index(op.f("ix_live_training_sessions_date"), table_name="live_training_sessions")
    op.drop_table("live_training_sessions")
