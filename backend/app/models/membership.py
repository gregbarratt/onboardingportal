from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.payment_statuses import (
    DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
    DEFAULT_MEMBERSHIP_STATUS,
)
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agent_profiles.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    membership_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    setup_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    monthly_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    membership_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_MEMBERSHIP_STATUS,
        server_default=DEFAULT_MEMBERSHIP_STATUS,
        index=True,
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
        server_default=DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
        index=True,
        nullable=False,
    )
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stripe_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    failed_payment_count: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    access_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    suspension_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    agent: Mapped[AgentProfile] = relationship(back_populates="membership")
