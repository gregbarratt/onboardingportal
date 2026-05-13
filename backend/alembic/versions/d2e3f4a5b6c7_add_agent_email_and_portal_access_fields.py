"""add agent email and portal access fields

Revision ID: d2e3f4a5b6c7
Revises: c2d3e4f5a6b7
Create Date: 2026-05-13 17:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_profiles", sa.Column("personal_email", sa.String(length=255), nullable=True))
    op.add_column("agent_profiles", sa.Column("company_email", sa.String(length=255), nullable=True))
    op.add_column(
        "agent_profiles",
        sa.Column("portal_access_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.execute("UPDATE agent_profiles SET personal_email = email WHERE personal_email IS NULL")


def downgrade() -> None:
    op.drop_column("agent_profiles", "portal_access_enabled")
    op.drop_column("agent_profiles", "company_email")
    op.drop_column("agent_profiles", "personal_email")
