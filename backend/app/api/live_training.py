from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.live_training import AttendanceLog, LiveTrainingSession
from app.models.training import TrainingModule
from app.models.user import User
from app.schemas.live_training import (
    AttendanceBulkRequest,
    AttendanceLogCreate,
    AttendanceLogRead,
    LiveSessionAssignRequest,
    LiveTrainingSessionCreate,
    LiveTrainingSessionRead,
    LiveTrainingSessionUpdate,
)


router = APIRouter(tags=["Live Calls and Attendance"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage live sessions and attendance.",
        )


def get_live_session_or_404(db: Session, session_id: int) -> LiveTrainingSession:
    live_session = db.get(LiveTrainingSession, session_id)
    if live_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Live session not found.",
        )
    return live_session


def get_attendance_log(db: Session, session_id: int, agent_id: int) -> AttendanceLog | None:
    return db.scalar(
        select(AttendanceLog).where(
            AttendanceLog.session_id == session_id,
            AttendanceLog.agent_id == agent_id,
        )
    )


def get_attendance_log_with_session(db: Session, attendance_log_id: int) -> AttendanceLog:
    attendance_log = db.scalar(
        select(AttendanceLog)
        .options(selectinload(AttendanceLog.session))
        .where(AttendanceLog.id == attendance_log_id)
    )
    if attendance_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance log not found.",
        )
    return attendance_log


def check_related_training_module(db: Session, training_module_id: int | None) -> None:
    if training_module_id is None:
        return
    if db.get(TrainingModule, training_module_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related training module not found.",
        )


def upsert_attendance_log(
    db: Session,
    live_session: LiveTrainingSession,
    agent_profile: AgentProfile,
    current_user: User,
    request: AttendanceLogCreate,
) -> AttendanceLog:
    attendance_log = get_attendance_log(db, live_session.id, agent_profile.id)
    if attendance_log is None:
        attendance_log = AttendanceLog(
            session_id=live_session.id,
            agent_id=agent_profile.id,
        )
        db.add(attendance_log)
        db.flush()

    attendance_log.attendance_status = request.attendance_status
    attendance_log.join_time = request.join_time
    attendance_log.leave_time = request.leave_time
    attendance_log.duration_attended = request.duration_attended
    attendance_log.marked_by = current_user.id
    attendance_log.marked_date = request.marked_date or date.today()
    attendance_log.notes = request.notes
    attendance_log.follow_up_required = request.follow_up_required
    attendance_log.watched_recording = request.watched_recording
    attendance_log.recording_completed_date = request.recording_completed_date
    return attendance_log


@router.post("/live-sessions", response_model=LiveTrainingSessionRead, status_code=status.HTTP_201_CREATED)
def create_live_session(
    request: LiveTrainingSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LiveTrainingSession:
    require_admin_user(current_user)
    check_related_training_module(db, request.related_training_module_id)

    live_session = LiveTrainingSession(**request.model_dump())
    db.add(live_session)
    db.commit()
    db.refresh(live_session)
    return live_session


@router.get("/live-sessions", response_model=list[LiveTrainingSessionRead])
def list_live_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[LiveTrainingSession]:
    return list(
        db.scalars(
            select(LiveTrainingSession).order_by(
                LiveTrainingSession.date,
                LiveTrainingSession.start_time,
                LiveTrainingSession.id,
            )
        )
    )


@router.get("/live-sessions/{session_id}", response_model=LiveTrainingSessionRead)
def get_live_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LiveTrainingSession:
    return get_live_session_or_404(db, session_id)


@router.put("/live-sessions/{session_id}", response_model=LiveTrainingSessionRead)
def update_live_session(
    session_id: int,
    request: LiveTrainingSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LiveTrainingSession:
    require_admin_user(current_user)
    live_session = get_live_session_or_404(db, session_id)
    update_data = request.model_dump(exclude_unset=True)
    if "related_training_module_id" in update_data:
        check_related_training_module(db, update_data["related_training_module_id"])

    for field, value in update_data.items():
        setattr(live_session, field, value)

    db.commit()
    db.refresh(live_session)
    return live_session


@router.post("/live-sessions/{session_id}/assign", response_model=AttendanceLogRead, status_code=status.HTTP_201_CREATED)
def assign_live_session(
    session_id: int,
    request: LiveSessionAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AttendanceLog:
    require_admin_user(current_user)
    live_session = get_live_session_or_404(db, session_id)
    agent_profile = get_agent_or_404(db, request.agent_id)
    attendance_log = get_attendance_log(db, live_session.id, agent_profile.id)

    if attendance_log is None:
        attendance_log = AttendanceLog(
            session_id=live_session.id,
            agent_id=agent_profile.id,
            marked_by=current_user.id,
            marked_date=date.today(),
            notes=request.notes,
        )
        db.add(attendance_log)
    else:
        attendance_log.marked_by = current_user.id
        attendance_log.marked_date = date.today()
        if request.notes is not None:
            attendance_log.notes = request.notes

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This agent is already assigned to this live session.",
        ) from None

    db.refresh(attendance_log)
    return get_attendance_log_with_session(db, attendance_log.id)


@router.post("/live-sessions/{session_id}/attendance", response_model=AttendanceLogRead)
def mark_live_session_attendance(
    session_id: int,
    request: AttendanceLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AttendanceLog:
    require_admin_user(current_user)
    live_session = get_live_session_or_404(db, session_id)
    agent_profile = get_agent_or_404(db, request.agent_id)
    attendance_log = upsert_attendance_log(db, live_session, agent_profile, current_user, request)
    db.commit()
    db.refresh(attendance_log)
    return get_attendance_log_with_session(db, attendance_log.id)


@router.post("/live-sessions/{session_id}/attendance/bulk", response_model=list[AttendanceLogRead])
def mark_live_session_attendance_bulk(
    session_id: int,
    request: AttendanceBulkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AttendanceLog]:
    require_admin_user(current_user)
    live_session = get_live_session_or_404(db, session_id)
    attendance_logs: list[AttendanceLog] = []

    for item in request.items:
        agent_profile = get_agent_or_404(db, item.agent_id)
        attendance_logs.append(upsert_attendance_log(db, live_session, agent_profile, current_user, item))

    db.commit()
    return [get_attendance_log_with_session(db, attendance_log.id) for attendance_log in attendance_logs]


@router.get("/agents/{agent_profile_id}/attendance", response_model=list[AttendanceLogRead])
def list_agent_attendance(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AttendanceLog]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return list(
        db.scalars(
            select(AttendanceLog)
            .options(selectinload(AttendanceLog.session))
            .join(LiveTrainingSession)
            .where(AttendanceLog.agent_id == agent_profile.id)
            .order_by(
                LiveTrainingSession.date,
                LiveTrainingSession.start_time,
                LiveTrainingSession.id,
            )
        )
    )
