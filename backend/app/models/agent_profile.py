from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.agent_statuses import DEFAULT_AGENT_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.audit import AdminNote, AuditLog
    from app.models.certificate import Certificate
    from app.models.compliance import PolicyAcceptance
    from app.models.document import Document
    from app.models.live_training import AttendanceLog
    from app.models.notification import Notification
    from app.models.onboarding import AgentOnboardingProgress
    from app.models.membership import Membership
    from app.models.organization import Organization
    from app.models.payment import Payment
    from app.models.training import AgentTrainingProgress, TrainingAssignment
    from app.models.user import User


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    personal_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portal_access_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_AGENT_STATUS,
        server_default=DEFAULT_AGENT_STATUS,
        index=True,
        nullable=False,
    )
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    commission_bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commission_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commission_sort_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    commission_account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
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

    user: Mapped[User] = relationship(back_populates="agent_profile")
    organization: Mapped[Organization | None] = relationship(back_populates="agent_profiles")
    membership: Mapped[Membership | None] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        uselist=False,
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    onboarding_progress: Mapped[list[AgentOnboardingProgress]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    training_assignments: Mapped[list[TrainingAssignment]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    training_progress: Mapped[list[AgentTrainingProgress]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    policy_acceptances: Mapped[list[PolicyAcceptance]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    certificates: Mapped[list[Certificate]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    admin_notes: Mapped[list[AdminNote]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )
