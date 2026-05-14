"""Add Stripe sync cache fields

Revision ID: a6b7c8d9e0f1
Revises: e2f3a4b5c6d7
Create Date: 2026-05-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a6b7c8d9e0f1"
down_revision: str | Sequence[str] | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("memberships", sa.Column("stripe_last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("memberships", sa.Column("stripe_sync_status", sa.String(length=50), nullable=True))
    op.add_column("memberships", sa.Column("stripe_sync_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("memberships", "stripe_sync_error")
    op.drop_column("memberships", "stripe_sync_status")
    op.drop_column("memberships", "stripe_last_synced_at")
