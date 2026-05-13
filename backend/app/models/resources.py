from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.training import TrainingModule
    from app.models.user import User


class SupplierAccess(Base):
    __tablename__ = "supplier_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    login_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    related_training_module: Mapped[int | None] = mapped_column(ForeignKey("training_modules.id"), nullable=True)
    visible_to_agents: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    related_training: Mapped[TrainingModule | None] = relationship()
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])


class MarketingAsset(Base):
    __tablename__ = "marketing_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_offer_wording: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    visible_to_agents: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])
