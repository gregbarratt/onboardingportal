from __future__ import annotations

from datetime import date as date_type, datetime, time as time_type
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.live_training import DEFAULT_ATTENDANCE_STATUS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.training import TrainingModule
    from app.models.user import User


class LiveTrainingSession(Base):
    __tablename__ = "live_training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    session_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    start_time: Mapped[time_type | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time_type | None] = mapped_column(Time, nullable=True)
    trainer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recording_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attendance_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    related_training_module_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_modules.id"),
        index=True,
        nullable=True,
    )
    follow_up_quiz_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    related_training_module: Mapped[TrainingModule | None] = relationship()
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    __table_args__ = (
        UniqueConstraint("session_id", "agent_id", name="uq_attendance_logs_session_agent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_training_sessions.id"), index=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    attendance_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_ATTENDANCE_STATUS,
        server_default=DEFAULT_ATTENDANCE_STATUS,
        index=True,
        nullable=False,
    )
    join_time: Mapped[time_type | None] = mapped_column(Time, nullable=True)
    leave_time: Mapped[time_type | None] = mapped_column(Time, nullable=True)
    duration_attended: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    marked_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    watched_recording: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    recording_completed_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session: Mapped[LiveTrainingSession] = relationship(back_populates="attendance_logs")
    agent: Mapped[AgentProfile] = relationship(back_populates="attendance_logs")
    marked_by_user: Mapped[User | None] = relationship(foreign_keys=[marked_by])
