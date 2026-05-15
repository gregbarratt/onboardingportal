"""Add policy acceptance evidence

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("policy_acceptances") as batch_op:
        batch_op.add_column(sa.Column("ip_address", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("user_agent", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("acceptance_statement", sa.Text(), nullable=True))
        batch_op.drop_constraint("uq_policy_acceptances_agent_policy", type_="unique")
        batch_op.create_unique_constraint(
            "uq_policy_acceptances_agent_policy_version",
            ["agent_id", "policy_id", "policy_version"],
        )


def downgrade() -> None:
    with op.batch_alter_table("policy_acceptances") as batch_op:
        batch_op.drop_constraint("uq_policy_acceptances_agent_policy_version", type_="unique")
        batch_op.create_unique_constraint("uq_policy_acceptances_agent_policy", ["agent_id", "policy_id"])
        batch_op.drop_column("acceptance_statement")
        batch_op.drop_column("user_agent")
        batch_op.drop_column("ip_address")
