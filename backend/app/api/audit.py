from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.audit import ADMIN_NOTE_ADDED_ACTION
from app.db.session import get_db
from app.models.audit import AdminNote, AuditLog
from app.models.user import User
from app.schemas.audit import AdminNoteCreate, AdminNoteRead, AuditLogRead
from app.services.audit import create_audit_log


router = APIRouter(tags=["Audit Logs and Admin Notes"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access audit logs and admin notes.",
        )


def get_request_ip_address(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AuditLog]:
    require_admin_user(current_user)
    return list(
        db.scalars(
            select(AuditLog).order_by(AuditLog.created_date.desc(), AuditLog.id.desc())
        )
    )


@router.get("/agents/{agent_profile_id}/audit-logs", response_model=list[AuditLogRead])
def list_agent_audit_logs(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AuditLog]:
    require_admin_user(current_user)
    agent_profile = get_agent_or_404(db, agent_profile_id)
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.agent_id == agent_profile.id)
            .order_by(AuditLog.created_date.desc(), AuditLog.id.desc())
        )
    )


@router.post("/agents/{agent_profile_id}/admin-notes", response_model=AdminNoteRead, status_code=status.HTTP_201_CREATED)
def create_agent_admin_note(
    agent_profile_id: int,
    request_data: AdminNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AdminNote:
    require_admin_user(current_user)
    agent_profile = get_agent_or_404(db, agent_profile_id)
    admin_note = AdminNote(
        agent_id=agent_profile.id,
        note=request_data.note,
        created_by=current_user.id,
    )
    db.add(admin_note)
    create_audit_log(
        db,
        action_type=ADMIN_NOTE_ADDED_ACTION,
        description=f"Admin note added for {agent_profile.first_name} {agent_profile.last_name}.",
        created_by=current_user.id,
        user_id=agent_profile.user_id,
        agent_id=agent_profile.id,
        new_value=request_data.note,
        ip_address=get_request_ip_address(request),
    )
    db.commit()
    db.refresh(admin_note)
    return admin_note


@router.get("/agents/{agent_profile_id}/admin-notes", response_model=list[AdminNoteRead])
def list_agent_admin_notes(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AdminNote]:
    require_admin_user(current_user)
    agent_profile = get_agent_or_404(db, agent_profile_id)
    return list(
        db.scalars(
            select(AdminNote)
            .where(AdminNote.agent_id == agent_profile.id)
            .order_by(AdminNote.created_date.desc(), AdminNote.id.desc())
        )
    )
