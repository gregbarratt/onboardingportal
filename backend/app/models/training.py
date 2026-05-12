from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.training import (
    DEFAULT_TRAINING_PROGRESS_STATUS,
    DEFAULT_TRAINING_PUBLISHED_STATUS,
    DEFAULT_TRAINING_TRACK,
)
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class TrainingCategory(Base):
    __tablename__ = "training_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    modules: Mapped[list[TrainingModule]] = relationship(back_populates="category")


class TrainingModule(Base):
    __tablename__ = "training_modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("training_categories.id"), index=True, nullable=False)
    level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    estimated_completion_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    quiz_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    pass_mark: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    renewal_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    renewal_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_track: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_TRAINING_TRACK,
        server_default=DEFAULT_TRAINING_TRACK,
        index=True,
        nullable=False,
    )
    published_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_TRAINING_PUBLISHED_STATUS,
        server_default=DEFAULT_TRAINING_PUBLISHED_STATUS,
        index=True,
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped[TrainingCategory] = relationship(back_populates="modules")
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])
    assignments: Mapped[list[TrainingAssignment]] = relationship(
        back_populates="training_module",
        cascade="all, delete-orphan",
    )
    progress_records: Mapped[list[AgentTrainingProgress]] = relationship(
        back_populates="training_module",
        cascade="all, delete-orphan",
    )


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"
    __table_args__ = (
        UniqueConstraint("agent_id", "training_module_id", name="uq_training_assignments_agent_module"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    training_module_id: Mapped[int] = mapped_column(ForeignKey("training_modules.id"), index=True, nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent: Mapped[AgentProfile] = relationship(back_populates="training_assignments")
    training_module: Mapped[TrainingModule] = relationship(back_populates="assignments")
    assigned_by_user: Mapped[User | None] = relationship(foreign_keys=[assigned_by])
    progress: Mapped[AgentTrainingProgress | None] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AgentTrainingProgress(Base):
    __tablename__ = "agent_training_progress"
    __table_args__ = (
        UniqueConstraint("agent_id", "training_module_id", name="uq_agent_training_progress_agent_module"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("training_assignments.id"), unique=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), index=True, nullable=False)
    training_module_id: Mapped[int] = mapped_column(ForeignKey("training_modules.id"), index=True, nullable=False)
    progress_status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_TRAINING_PROGRESS_STATUS,
        server_default=DEFAULT_TRAINING_PROGRESS_STATUS,
        index=True,
        nullable=False,
    )
    started_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assignment: Mapped[TrainingAssignment] = relationship(back_populates="progress")
    agent: Mapped[AgentProfile] = relationship(back_populates="training_progress")
    training_module: Mapped[TrainingModule] = relationship(back_populates="progress_records")
