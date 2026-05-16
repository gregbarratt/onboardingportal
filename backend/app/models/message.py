from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.messages import DEFAULT_MESSAGE_TICKET_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.organization import Organization
    from app.models.user import User


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_MESSAGE_TICKET_STATUS,
        server_default=DEFAULT_MESSAGE_TICKET_STATUS,
        index=True,
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization | None] = relationship()
    agent: Mapped[AgentProfile | None] = relationship()
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    messages: Mapped[list[SupportTicketMessage]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportTicketMessage.created_at",
    )


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), index=True, nullable=False)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    internal_note: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship(foreign_keys=[sender_user_id])
