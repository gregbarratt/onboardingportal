from __future__ import annotations

from datetime import date as date_type, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.documents import DEFAULT_DOCUMENT_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    uploaded_date: Mapped[date_type] = mapped_column(Date, default=date_type.today, nullable=False)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    signed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    signed_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    verified_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_DOCUMENT_STATUS,
        server_default=DEFAULT_DOCUMENT_STATUS,
        index=True,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    agent: Mapped[AgentProfile] = relationship(back_populates="documents")
    uploaded_by_user: Mapped[User] = relationship(foreign_keys=[uploaded_by])
    verified_by_user: Mapped[User | None] = relationship(foreign_keys=[verified_by])
