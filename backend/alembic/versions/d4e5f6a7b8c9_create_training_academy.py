"""create training academy

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-12 17:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.core.training import DEFAULT_MANDATORY_MODULES, TRAINING_CATEGORIES


revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_categories_name"), "training_categories", ["name"], unique=True)

    training_categories_table = sa.table(
        "training_categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    category_ids = {
        category_name: index
        for index, category_name in enumerate(TRAINING_CATEGORIES, start=1)
    }
    op.bulk_insert(
        training_categories_table,
        [
            {"id": category_id, "name": category_name}
            for category_name, category_id in category_ids.items()
        ],
    )
    op.execute("SELECT setval('training_categories_id_seq', (SELECT MAX(id) FROM training_categories))")

    op.create_table(
        "training_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=100), nullable=True),
        sa.Column("mandatory", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("estimated_completion_time", sa.String(length=100), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("content_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("quiz_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("pass_mark", sa.Integer(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("renewal_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("renewal_period_months", sa.Integer(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("published_status", sa.String(length=50), server_default="Draft", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["training_categories.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_modules_category_id"), "training_modules", ["category_id"], unique=False)
    op.create_index(op.f("ix_training_modules_published_status"), "training_modules", ["published_status"], unique=False)

    training_modules_table = sa.table(
        "training_modules",
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category_id", sa.Integer),
        sa.column("level", sa.String),
        sa.column("mandatory", sa.Boolean),
        sa.column("estimated_completion_time", sa.String),
        sa.column("content_type", sa.String),
        sa.column("quiz_required", sa.Boolean),
        sa.column("pass_mark", sa.Integer),
        sa.column("certificate_issued", sa.Boolean),
        sa.column("renewal_required", sa.Boolean),
        sa.column("renewal_period_months", sa.Integer),
        sa.column("published_status", sa.String),
    )
    op.bulk_insert(
        training_modules_table,
        [
            {
                "title": module["title"],
                "description": module["description"],
                "category_id": category_ids[module["category_name"]],
                "level": module.get("level"),
                "mandatory": module["mandatory"],
                "estimated_completion_time": module.get("estimated_completion_time"),
                "content_type": module.get("content_type"),
                "quiz_required": module["quiz_required"],
                "pass_mark": module.get("pass_mark"),
                "certificate_issued": module["certificate_issued"],
                "renewal_required": module["renewal_required"],
                "renewal_period_months": module.get("renewal_period_months"),
                "published_status": module["published_status"],
            }
            for module in DEFAULT_MANDATORY_MODULES
        ],
    )

    op.create_table(
        "training_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("training_module_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.Column("assigned_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("mandatory", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "training_module_id", name="uq_training_assignments_agent_module"),
    )
    op.create_index(op.f("ix_training_assignments_agent_id"), "training_assignments", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_training_assignments_training_module_id"),
        "training_assignments",
        ["training_module_id"],
        unique=False,
    )

    op.create_table(
        "agent_training_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("training_module_id", sa.Integer(), nullable=False),
        sa.Column("progress_status", sa.String(length=50), server_default="Not Started", nullable=False),
        sa.Column("started_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["training_assignments.id"]),
        sa.ForeignKeyConstraint(["training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "training_module_id", name="uq_agent_training_progress_agent_module"),
    )
    op.create_index(op.f("ix_agent_training_progress_agent_id"), "agent_training_progress", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_agent_training_progress_assignment_id"),
        "agent_training_progress",
        ["assignment_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_agent_training_progress_progress_status"),
        "agent_training_progress",
        ["progress_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_training_progress_training_module_id"),
        "agent_training_progress",
        ["training_module_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_training_progress_training_module_id"), table_name="agent_training_progress")
    op.drop_index(op.f("ix_agent_training_progress_progress_status"), table_name="agent_training_progress")
    op.drop_index(op.f("ix_agent_training_progress_assignment_id"), table_name="agent_training_progress")
    op.drop_index(op.f("ix_agent_training_progress_agent_id"), table_name="agent_training_progress")
    op.drop_table("agent_training_progress")
    op.drop_index(op.f("ix_training_assignments_training_module_id"), table_name="training_assignments")
    op.drop_index(op.f("ix_training_assignments_agent_id"), table_name="training_assignments")
    op.drop_table("training_assignments")
    op.drop_index(op.f("ix_training_modules_published_status"), table_name="training_modules")
    op.drop_index(op.f("ix_training_modules_category_id"), table_name="training_modules")
    op.drop_table("training_modules")
    op.drop_index(op.f("ix_training_categories_name"), table_name="training_categories")
    op.drop_table("training_categories")
