"""create certificates

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-13 10:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f9a0b1c2d3e4"
down_revision: str | Sequence[str] | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("training_module_id", sa.Integer(), nullable=False),
        sa.Column("certificate_name", sa.String(length=255), nullable=False),
        sa.Column("certificate_url", sa.String(length=500), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("renewal_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="Active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"]),
        sa.ForeignKeyConstraint(["training_module_id"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_certificates_agent_id"), "certificates", ["agent_id"], unique=False)
    op.create_index(op.f("ix_certificates_status"), "certificates", ["status"], unique=False)
    op.create_index(
        op.f("ix_certificates_training_module_id"),
        "certificates",
        ["training_module_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_certificates_training_module_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_status"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_agent_id"), table_name="certificates")
    op.drop_table("certificates")
