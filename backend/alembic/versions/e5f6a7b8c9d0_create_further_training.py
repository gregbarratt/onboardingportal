"""create further training

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-12 18:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.core.training import DEFAULT_FURTHER_TRAINING_MODULES, FURTHER_TRAINING_TRACK


revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FURTHER_TRAINING_CATEGORY_IDS = {
    "Marketing": 6,
    "Luxury Travel": 9,
    "Group Bookings": 10,
    "Sales Development": 101,
    "Destination Knowledge": 102,
    "Supplier Training": 103,
    "Cruise Training": 104,
    "Disney Training": 105,
    "Compliance Refreshers": 106,
    "Leadership Training": 107,
    "Systems Refreshers": 108,
}

NEW_FURTHER_TRAINING_CATEGORIES = (
    "Sales Development",
    "Destination Knowledge",
    "Supplier Training",
    "Cruise Training",
    "Disney Training",
    "Compliance Refreshers",
    "Leadership Training",
    "Systems Refreshers",
)


def upgrade() -> None:
    op.add_column(
        "training_modules",
        sa.Column(
            "training_track",
            sa.String(length=50),
            server_default="Onboarding",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_training_modules_training_track"),
        "training_modules",
        ["training_track"],
        unique=False,
    )

    training_categories_table = sa.table(
        "training_categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    op.bulk_insert(
        training_categories_table,
        [
            {"id": FURTHER_TRAINING_CATEGORY_IDS[category_name], "name": category_name}
            for category_name in NEW_FURTHER_TRAINING_CATEGORIES
        ],
    )
    op.execute("SELECT setval('training_categories_id_seq', (SELECT MAX(id) FROM training_categories))")

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
        sa.column("training_track", sa.String),
        sa.column("published_status", sa.String),
    )
    op.bulk_insert(
        training_modules_table,
        [
            {
                "title": module["title"],
                "description": module["description"],
                "category_id": FURTHER_TRAINING_CATEGORY_IDS[module["category_name"]],
                "level": module.get("level"),
                "mandatory": module["mandatory"],
                "estimated_completion_time": module.get("estimated_completion_time"),
                "content_type": module.get("content_type"),
                "quiz_required": module["quiz_required"],
                "pass_mark": module.get("pass_mark"),
                "certificate_issued": module["certificate_issued"],
                "renewal_required": module["renewal_required"],
                "renewal_period_months": module.get("renewal_period_months"),
                "training_track": FURTHER_TRAINING_TRACK,
                "published_status": module["published_status"],
            }
            for module in DEFAULT_FURTHER_TRAINING_MODULES
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM agent_training_progress "
        "WHERE training_module_id IN ("
        "SELECT id FROM training_modules WHERE training_track = 'Further Training'"
        ")"
    )
    op.execute(
        "DELETE FROM training_assignments "
        "WHERE training_module_id IN ("
        "SELECT id FROM training_modules WHERE training_track = 'Further Training'"
        ")"
    )
    op.execute("DELETE FROM training_modules WHERE training_track = 'Further Training'")
    op.drop_index(op.f("ix_training_modules_training_track"), table_name="training_modules")
    op.drop_column("training_modules", "training_track")
    op.execute(
        "DELETE FROM training_categories "
        "WHERE id IN (101, 102, 103, 104, 105, 106, 107, 108)"
    )
