from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.compliance import DEFAULT_COMPLIANCE_POLICY_STATUS, DEFAULT_COMPLIANCE_POLICY_VERSION
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_COMPLIANCE_POLICY_VERSION,
        server_default=DEFAULT_COMPLIANCE_POLICY_VERSION,
        nullable=False,
    )
    requires_acceptance: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    published_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_COMPLIANCE_POLICY_STATUS,
        server_default=DEFAULT_COMPLIANCE_POLICY_STATUS,
        index=True,
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])
    acceptances: Mapped[list[PolicyAcceptance]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class PolicyAcceptance(Base):
    __tablename__ = "policy_acceptances"
    __table_args__ = (
        UniqueConstraint("agent_id", "policy_id", "policy_version", name="uq_policy_acceptances_agent_policy_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("compliance_policies.id"), index=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    accepted_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    accepted_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acceptance_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    policy: Mapped[CompliancePolicy] = relationship(back_populates="acceptances")
    agent: Mapped[AgentProfile] = relationship(back_populates="policy_acceptances")
    accepted_by_user: Mapped[User] = relationship(foreign_keys=[accepted_by])

    @property
    def agent_name(self) -> str | None:
        if self.agent is None:
            return None
        return f"{self.agent.first_name} {self.agent.last_name}"

    @property
    def accepted_by_email(self) -> str | None:
        if self.accepted_by_user is None:
            return None
        return self.accepted_by_user.email
