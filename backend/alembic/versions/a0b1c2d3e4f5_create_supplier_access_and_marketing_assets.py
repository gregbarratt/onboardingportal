"""create supplier access and marketing assets

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-05-13 11:15:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: str | Sequence[str] | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("supplier_type", sa.String(length=100), nullable=False),
        sa.Column("portal_url", sa.String(length=500), nullable=True),
        sa.Column("login_instructions", sa.Text(), nullable=True),
        sa.Column("access_notes", sa.Text(), nullable=True),
        sa.Column("training_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("related_training_module", sa.Integer(), nullable=True),
        sa.Column("visible_to_agents", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["related_training_module"], ["training_modules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_access_supplier_type"), "supplier_access", ["supplier_type"], unique=False)

    op.create_table(
        "marketing_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("resource_url", sa.String(length=500), nullable=True),
        sa.Column("approved_offer_wording", sa.Text(), nullable=True),
        sa.Column("access_notes", sa.Text(), nullable=True),
        sa.Column("visible_to_agents", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketing_assets_asset_type"), "marketing_assets", ["asset_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_marketing_assets_asset_type"), table_name="marketing_assets")
    op.drop_table("marketing_assets")
    op.drop_index(op.f("ix_supplier_access_supplier_type"), table_name="supplier_access")
    op.drop_table("supplier_access")
