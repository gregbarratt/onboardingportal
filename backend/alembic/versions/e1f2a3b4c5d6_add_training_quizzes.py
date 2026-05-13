"""Add training quizzes

Revision ID: e1f2a3b4c5d6
Revises: d2e3f4a5b6c7
Create Date: 2026-05-13 19:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_quiz_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_module_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_quiz_questions_training_module_id"),
        "training_quiz_questions",
        ["training_module_id"],
        unique=False,
    )

    op.create_table(
        "training_quiz_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["training_quiz_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_quiz_options_question_id"),
        "training_quiz_options",
        ["question_id"],
        unique=False,
    )

    op.create_table(
        "training_quiz_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("training_module_id", sa.Integer(), nullable=False),
        sa.Column("progress_id", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="Submitted", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("redo_requested_by", sa.Integer(), nullable=True),
        sa.Column("redo_requested_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["progress_id"], ["agent_training_progress.id"]),
        sa.ForeignKeyConstraint(["redo_requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_quiz_attempts_agent_id"),
        "training_quiz_attempts",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_quiz_attempts_training_module_id"),
        "training_quiz_attempts",
        ["training_module_id"],
        unique=False,
    )

    op.create_table(
        "training_quiz_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("selected_option_id", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["training_quiz_attempts.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["training_quiz_questions.id"]),
        sa.ForeignKeyConstraint(["selected_option_id"], ["training_quiz_options.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_quiz_answers_attempt_id"),
        "training_quiz_answers",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_quiz_answers_question_id"),
        "training_quiz_answers",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_quiz_answers_selected_option_id"),
        "training_quiz_answers",
        ["selected_option_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_training_quiz_answers_selected_option_id"), table_name="training_quiz_answers")
    op.drop_index(op.f("ix_training_quiz_answers_question_id"), table_name="training_quiz_answers")
    op.drop_index(op.f("ix_training_quiz_answers_attempt_id"), table_name="training_quiz_answers")
    op.drop_table("training_quiz_answers")
    op.drop_index(op.f("ix_training_quiz_attempts_training_module_id"), table_name="training_quiz_attempts")
    op.drop_index(op.f("ix_training_quiz_attempts_agent_id"), table_name="training_quiz_attempts")
    op.drop_table("training_quiz_attempts")
    op.drop_index(op.f("ix_training_quiz_options_question_id"), table_name="training_quiz_options")
    op.drop_table("training_quiz_options")
    op.drop_index(op.f("ix_training_quiz_questions_training_module_id"), table_name="training_quiz_questions")
    op.drop_table("training_quiz_questions")
