from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.agent_profile import AgentProfile
from app.models.document import Document
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User
from app.services.organizations import SUPER_ADMIN_ROLE


ADMIN_REVIEW_NOTIFICATION_ROLES = {
    "Super Admin",
    "Organisation Admin",
    "Admin",
    "Compliance Manager",
}


def agent_display_name(agent_profile: AgentProfile) -> str:
    return f"{agent_profile.first_name} {agent_profile.last_name}".strip() or agent_profile.agent_id


def document_review_message(agent_profile: AgentProfile, document_type: str) -> str:
    return f"{agent_display_name(agent_profile)} uploaded {document_type} for admin review."


def add_notification_if_missing(
    db: Session,
    recipient_user_id: int,
    agent_id: int | None,
    notification_type: str,
    title: str,
    message: str,
    link_url: str,
    created_by: int | None = None,
) -> Notification | None:
    existing_notification_id = db.scalar(
        select(Notification.id).where(
            Notification.recipient_user_id == recipient_user_id,
            Notification.agent_id == agent_id,
            Notification.notification_type == notification_type,
            Notification.title == title,
            Notification.message == message,
            Notification.link_url == link_url,
        )
    )
    if existing_notification_id is not None:
        return None

    notification = Notification(
        recipient_user_id=recipient_user_id,
        agent_id=agent_id,
        notification_type=notification_type,
        title=title,
        message=message,
        link_url=link_url,
        created_by=created_by,
    )
    db.add(notification)
    return notification


def create_admin_review_notifications(
    db: Session,
    agent_profile: AgentProfile,
    notification_type: str,
    title: str,
    message: str,
    link_url: str,
    created_by: int | None = None,
) -> list[Notification]:
    query = (
        select(User)
        .join(Role)
        .where(User.is_active.is_(True))
        .where(Role.name.in_(ADMIN_REVIEW_NOTIFICATION_ROLES))
    )

    if agent_profile.organization_id is None:
        query = query.where(Role.name == SUPER_ADMIN_ROLE)
    else:
        query = query.where(
            or_(
                Role.name == SUPER_ADMIN_ROLE,
                User.organization_id == agent_profile.organization_id,
            )
        )

    notifications: list[Notification] = []
    for recipient in db.scalars(query):
        notification = add_notification_if_missing(
            db=db,
            recipient_user_id=recipient.id,
            agent_id=agent_profile.id,
            notification_type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            created_by=created_by,
        )
        if notification is not None:
            notifications.append(notification)

    return notifications


def create_document_review_notifications(
    db: Session,
    agent_profile: AgentProfile,
    document: Document,
    created_by: int | None = None,
) -> list[Notification]:
    return create_admin_review_notifications(
        db=db,
        agent_profile=agent_profile,
        notification_type="Document awaiting review",
        title="Document awaiting review",
        message=document_review_message(agent_profile, document.document_type),
        link_url="/admin/documents",
        created_by=created_by,
    )


def ensure_pending_document_review_notifications_for_user(db: Session, current_user: User) -> list[Notification]:
    if current_user.role.name not in ADMIN_REVIEW_NOTIFICATION_ROLES:
        return []

    query = (
        select(Document, AgentProfile)
        .join(AgentProfile, Document.agent_id == AgentProfile.id)
        .where(Document.status.in_(["Uploaded", "Awaiting Review"]))
        .order_by(Document.created_at.desc(), Document.id.desc())
    )
    if current_user.role.name != SUPER_ADMIN_ROLE:
        if current_user.organization_id is None:
            return []
        query = query.where(AgentProfile.organization_id == current_user.organization_id)

    notifications: list[Notification] = []
    for document, agent_profile in db.execute(query):
        notification = add_notification_if_missing(
            db=db,
            recipient_user_id=current_user.id,
            agent_id=agent_profile.id,
            notification_type="Document awaiting review",
            title="Document awaiting review",
            message=document_review_message(agent_profile, document.document_type),
            link_url="/admin/documents",
            created_by=document.uploaded_by,
        )
        if notification is not None:
            notifications.append(notification)

    if notifications:
        db.commit()

    return notifications
