from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationRead
from app.services.notifications import ensure_pending_document_review_notifications_for_user


router = APIRouter(tags=["Notifications"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create notifications.",
        )


def get_notification_or_404(db: Session, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return notification


def check_notification_access(notification: Notification, current_user: User) -> None:
    if is_admin_user(current_user):
        return
    if notification.recipient_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own notifications.",
        )


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Notification]:
    ensure_pending_document_review_notifications_for_user(db, current_user)
    query = (
        select(Notification)
        .where(Notification.recipient_user_id == current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return list(db.scalars(query))


@router.post("/notifications", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    request: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Notification:
    require_admin_user(current_user)

    recipient_user = db.get(User, request.recipient_user_id)
    if recipient_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient user not found.",
        )

    if request.agent_id is not None:
        agent_profile = get_agent_or_404(db, request.agent_id)
        check_agent_access(agent_profile, current_user)

    notification = Notification(
        recipient_user_id=recipient_user.id,
        agent_id=request.agent_id,
        notification_type=request.notification_type,
        title=request.title,
        message=request.message,
        link_url=request.link_url,
        created_by=current_user.id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Notification:
    notification = get_notification_or_404(db, notification_id)
    check_notification_access(notification, current_user)

    notification.read = True
    notification.read_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification
