"""create auth tables

Revision ID: f3a7b9c2d4e6
Revises: eee912b7e91c
Create Date: 2026-05-12 14:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3a7b9c2d4e6"
down_revision: str | Sequence[str] | None = "eee912b7e91c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


roles_table = sa.table(
    "roles",
    sa.column("name", sa.String()),
    sa.column("description", sa.String()),
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.bulk_insert(
        roles_table,
        [
            {
                "name": "Super Admin",
                "description": "Full access to the whole system.",
            },
            {
                "name": "Admin",
                "description": "Can manage agents, onboarding, payments, and approvals.",
            },
            {
                "name": "Training Manager",
                "description": "Can manage training modules and training progress.",
            },
            {
                "name": "Compliance Manager",
                "description": "Can manage compliance checks, policies, and documents.",
            },
            {
                "name": "Agent",
                "description": "Independent travel agent portal access.",
            },
        ],
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
