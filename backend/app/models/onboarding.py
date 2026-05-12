from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, true, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.onboarding_statuses import DEFAULT_ONBOARDING_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
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

    progress_records: Mapped[list[AgentOnboardingProgress]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
    )


class AgentOnboardingProgress(Base):
    __tablename__ = "agent_onboarding_progress"
    __table_args__ = (
        UniqueConstraint("agent_id", "step_id", name="uq_agent_onboarding_progress_agent_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    step_id: Mapped[int] = mapped_column(ForeignKey("onboarding_steps.id"), index=True, nullable=False)
    completion_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_ONBOARDING_STATUS,
        server_default=DEFAULT_ONBOARDING_STATUS,
        index=True,
        nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    evidence_file_or_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    agent: Mapped[AgentProfile] = relationship(back_populates="onboarding_progress")
    step: Mapped[OnboardingStep] = relationship(back_populates="progress_records")
    completed_by_user: Mapped[User | None] = relationship(
        foreign_keys=[completed_by],
    )
    approved_by_user: Mapped[User | None] = relationship(
        foreign_keys=[approved_by],
    )
