from __future__ import annotations

from datetime import date as date_type, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.certificates import DEFAULT_CERTIFICATE_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.training import TrainingModule


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    training_module_id: Mapped[int] = mapped_column(ForeignKey("training_modules.id"), index=True, nullable=False)
    certificate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_url: Mapped[str] = mapped_column(String(500), nullable=False)
    issued_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    renewal_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_CERTIFICATE_STATUS,
        server_default=DEFAULT_CERTIFICATE_STATUS,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    agent: Mapped[AgentProfile] = relationship(back_populates="certificates")
    training_module: Mapped[TrainingModule] = relationship()
