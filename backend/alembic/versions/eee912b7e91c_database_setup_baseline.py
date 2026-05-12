"""database setup baseline

Revision ID: eee912b7e91c
Revises: 
Create Date: 2026-05-12 14:16:43.490431

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa



revision: str = 'eee912b7e91c'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

