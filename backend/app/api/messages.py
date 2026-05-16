from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_active_user
from app.core.messages import DEFAULT_MESSAGE_TICKET_STATUS
from app.core.roles import ADMIN_ROLE_NAMES
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.message import SupportTicket, SupportTicketMessage
from app.models.user import User
from app.schemas.message import (
    SupportTicketCreate,
    SupportTicketRead,
    SupportTicketReplyCreate,
    SupportTicketStatusUpdate,
)
from app.core.config import settings
from app.services.audit import create_audit_log
from app.services.email import send_agent_message_to_accounts, send_ticket_update_to_agent
from app.services.notifications import add_notification_if_missing, agent_display_name, create_admin_review_notifications
from app.services.organizations import SUPER_ADMIN_ROLE, user_can_access_organization


router = APIRouter(prefix="/messages", tags=["Messages"])


def is_admin_user(user: User) -> bool:
    return user.role.name in ADMIN_ROLE_NAMES


def ticket_options():
    return (
        selectinload(SupportTicket.agent).selectinload(AgentProfile.user),
        selectinload(SupportTicket.created_by_user).selectinload(User.role),
        selectinload(SupportTicket.messages).selectinload(SupportTicketMessage.sender).selectinload(User.role),
    )


def ticket_query():
    return select(SupportTicket).options(*ticket_options())


def agent_email_for_ticket(ticket: SupportTicket) -> str:
    if ticket.agent is not None:
        return ticket.agent.personal_email or ticket.agent.email or ticket.agent.user.email
    return ticket.created_by_user.email


def agent_name_for_ticket(ticket: SupportTicket) -> str:
    if ticket.agent is not None:
        return agent_display_name(ticket.agent)
    return ticket.created_by_user.email


def frontend_link(path: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}"


def send_safely(callback) -> bool:
    try:
        return bool(callback())
    except Exception:
        return False


def serialize_ticket(ticket: SupportTicket) -> dict:
    messages = [
        {
            "id": message.id,
            "ticket_id": message.ticket_id,
            "sender_user_id": message.sender_user_id,
            "sender_email": message.sender.email,
            "sender_role": message.sender.role.name,
            "message": message.message,
            "internal_note": message.internal_note,
            "created_at": message.created_at,
        }
        for message in ticket.messages
    ]

    return {
        "id": ticket.id,
        "organization_id": ticket.organization_id,
        "agent_id": ticket.agent_id,
        "agent_name": agent_name_for_ticket(ticket),
        "agent_email": agent_email_for_ticket(ticket),
        "created_by_user_id": ticket.created_by_user_id,
        "subject": ticket.subject,
        "status": ticket.status,
        "message_count": len(messages),
        "last_message_at": ticket.last_message_at,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages": messages,
    }


def get_ticket_or_404(db: Session, ticket_id: int) -> SupportTicket:
    ticket = db.scalar(ticket_query().where(SupportTicket.id == ticket_id))
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message ticket not found.",
        )
    return ticket


def check_ticket_access(ticket: SupportTicket, current_user: User) -> None:
    if is_admin_user(current_user):
        if user_can_access_organization(current_user, ticket.organization_id):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access messages in your organisation.",
        )

    if ticket.created_by_user_id == current_user.id:
        return
    if ticket.agent is not None and ticket.agent.user_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only access your own messages.",
    )


def notify_admin_team(db: Session, ticket: SupportTicket, message: str, created_by: int | None) -> None:
    if ticket.agent is None:
        return

    create_admin_review_notifications(
        db=db,
        agent_profile=ticket.agent,
        notification_type="Agent message",
        title="Agent message received",
        message=message,
        link_url="/admin/messages",
        created_by=created_by,
    )


def notify_agent(db: Session, ticket: SupportTicket, *, notification_type: str, title: str, message: str, created_by: int | None) -> None:
    recipient_user_id = ticket.agent.user_id if ticket.agent is not None else ticket.created_by_user_id
    add_notification_if_missing(
        db=db,
        recipient_user_id=recipient_user_id,
        agent_id=ticket.agent_id,
        notification_type=notification_type,
        title=title,
        message=message,
        link_url="/messages",
        created_by=created_by,
    )


@router.get("", response_model=list[SupportTicketRead])
def list_message_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    query = ticket_query().order_by(SupportTicket.last_message_at.desc(), SupportTicket.id.desc())

    if is_admin_user(current_user):
        if current_user.role.name != SUPER_ADMIN_ROLE:
            if current_user.organization_id is None:
                return []
            query = query.where(SupportTicket.organization_id == current_user.organization_id)
    else:
        own_agent_id = current_user.agent_profile.id if current_user.agent_profile is not None else None
        query = query.where(
            or_(
                SupportTicket.created_by_user_id == current_user.id,
                SupportTicket.agent_id == own_agent_id,
            )
        )

    return [serialize_ticket(ticket) for ticket in db.scalars(query)]


@router.post("", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
def create_message_ticket(
    request: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    agent_profile = current_user.agent_profile
    if agent_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please create your agent profile before sending a message.",
        )

    now = datetime.now(timezone.utc)
    ticket = SupportTicket(
        organization_id=agent_profile.organization_id or current_user.organization_id,
        agent=agent_profile,
        created_by_user_id=current_user.id,
        subject=request.subject,
        status=DEFAULT_MESSAGE_TICKET_STATUS,
        last_message_at=now,
    )
    db.add(ticket)
    db.flush()

    ticket_message = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=current_user.id,
        message=request.message,
    )
    db.add(ticket_message)
    notify_admin_team(
        db,
        ticket,
        f"{agent_display_name(agent_profile)} sent a new message: {request.subject}",
        current_user.id,
    )
    create_audit_log(
        db,
        action_type="Support ticket created",
        description=f"{agent_display_name(agent_profile)} sent a message to the admin team.",
        created_by=current_user.id,
        user_id=current_user.id,
        agent_id=agent_profile.id,
    )
    db.commit()

    ticket = get_ticket_or_404(db, ticket.id)
    send_safely(
        lambda: send_agent_message_to_accounts(
            agent_name=agent_name_for_ticket(ticket),
            agent_email=agent_email_for_ticket(ticket),
            subject=ticket.subject,
            message=request.message,
            ticket_url=frontend_link("/admin/messages"),
        )
    )
    return serialize_ticket(ticket)


@router.get("/{ticket_id}", response_model=SupportTicketRead)
def get_message_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    ticket = get_ticket_or_404(db, ticket_id)
    check_ticket_access(ticket, current_user)
    return serialize_ticket(ticket)


@router.post("/{ticket_id}/replies", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
def reply_to_message_ticket(
    ticket_id: int,
    request: SupportTicketReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    ticket = get_ticket_or_404(db, ticket_id)
    check_ticket_access(ticket, current_user)

    admin_reply = is_admin_user(current_user)
    now = datetime.now(timezone.utc)
    ticket.messages.append(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            message=request.message,
        )
    )
    ticket.last_message_at = now

    previous_status = ticket.status
    if admin_reply and ticket.status in {"Open", "In Progress", "Waiting for Admin"}:
        ticket.status = "Waiting for Agent"
    elif not admin_reply and ticket.status not in {"Closed", "Resolved"}:
        ticket.status = "Waiting for Admin"

    if admin_reply:
        notify_agent(
            db,
            ticket,
            notification_type="Message reply",
            title="Admin replied to your message",
            message=f"Your message about '{ticket.subject}' has a new reply.",
            created_by=current_user.id,
        )
    else:
        notify_admin_team(
            db,
            ticket,
            f"{agent_name_for_ticket(ticket)} replied to: {ticket.subject}",
            current_user.id,
        )

    create_audit_log(
        db,
        action_type="Support ticket replied",
        description=f"Message ticket reply added for {ticket.subject}.",
        created_by=current_user.id,
        user_id=ticket.created_by_user_id,
        agent_id=ticket.agent_id,
        previous_value=previous_status,
        new_value=ticket.status,
    )
    db.commit()

    ticket = get_ticket_or_404(db, ticket.id)
    if admin_reply:
        send_safely(
            lambda: send_ticket_update_to_agent(
                to_email=agent_email_for_ticket(ticket),
                subject=ticket.subject,
                message=request.message,
                ticket_url=frontend_link("/messages"),
            )
        )
    else:
        send_safely(
            lambda: send_agent_message_to_accounts(
                agent_name=agent_name_for_ticket(ticket),
                agent_email=agent_email_for_ticket(ticket),
                subject=ticket.subject,
                message=request.message,
                ticket_url=frontend_link("/admin/messages"),
            )
        )

    return serialize_ticket(ticket)


@router.put("/{ticket_id}/status", response_model=SupportTicketRead)
def update_message_ticket_status(
    ticket_id: int,
    request: SupportTicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update message status.",
        )

    ticket = get_ticket_or_404(db, ticket_id)
    check_ticket_access(ticket, current_user)
    previous_status = ticket.status
    if previous_status == request.status:
        return serialize_ticket(ticket)

    now = datetime.now(timezone.utc)
    ticket.status = request.status
    ticket.last_message_at = now
    ticket.messages.append(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            message=f"Status changed from {previous_status} to {request.status}.",
        )
    )
    notify_agent(
        db,
        ticket,
        notification_type="Message status changed",
        title="Message status updated",
        message=f"Your message about '{ticket.subject}' is now {request.status}.",
        created_by=current_user.id,
    )
    create_audit_log(
        db,
        action_type="Support ticket status changed",
        description=f"Message ticket status changed for {ticket.subject}.",
        created_by=current_user.id,
        user_id=ticket.created_by_user_id,
        agent_id=ticket.agent_id,
        previous_value=previous_status,
        new_value=request.status,
    )
    db.commit()

    ticket = get_ticket_or_404(db, ticket.id)
    send_safely(
        lambda: send_ticket_update_to_agent(
            to_email=agent_email_for_ticket(ticket),
            subject=ticket.subject,
            message=f"Your ticket status changed from {previous_status} to {request.status}.",
            ticket_url=frontend_link("/messages"),
        )
    )
    return serialize_ticket(ticket)
