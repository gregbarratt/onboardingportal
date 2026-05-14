"""Add organizations

Revision ID: e2f3a4b5c6d7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="Active", nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=True)
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (name, slug, status)
            VALUES ('One Travel Club', 'one-travel-club', 'Active')
            """
        )
    )
    default_organization_id = bind.execute(
        sa.text("SELECT id FROM organizations WHERE slug = 'one-travel-club'")
    ).scalar_one()

    op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    if dialect_name != "sqlite":
        op.create_foreign_key(
            "fk_users_organization_id_organizations",
            "users",
            "organizations",
            ["organization_id"],
            ["id"],
        )
    op.execute(
        sa.text("UPDATE users SET organization_id = :organization_id").bindparams(
            organization_id=default_organization_id
        )
    )

    op.add_column("agent_profiles", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_agent_profiles_organization_id"), "agent_profiles", ["organization_id"], unique=False)
    if dialect_name != "sqlite":
        op.create_foreign_key(
            "fk_agent_profiles_organization_id_organizations",
            "agent_profiles",
            "organizations",
            ["organization_id"],
            ["id"],
        )
    op.execute(
        sa.text("UPDATE agent_profiles SET organization_id = :organization_id").bindparams(
            organization_id=default_organization_id
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO roles (name, description)
            SELECT 'Organisation Admin', 'Can manage one organisation and its agents.'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'Organisation Admin')
            """
        )
    )


def downgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name != "sqlite":
        op.drop_constraint("fk_agent_profiles_organization_id_organizations", "agent_profiles", type_="foreignkey")
    op.drop_index(op.f("ix_agent_profiles_organization_id"), table_name="agent_profiles")
    op.drop_column("agent_profiles", "organization_id")

    if dialect_name != "sqlite":
        op.drop_constraint("fk_users_organization_id_organizations", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_column("users", "organization_id")

    op.execute(sa.text("DELETE FROM roles WHERE name = 'Organisation Admin'"))
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")
