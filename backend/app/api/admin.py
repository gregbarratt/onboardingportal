from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from app.api.agents import is_admin_user
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.compliance import REQUIRED_COMPLIANCE_DOCUMENT_TYPES
from app.core.roles import PAYMENT_ADMIN_ROLE_NAMES
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.certificate import Certificate
from app.models.compliance import PolicyAcceptance
from app.models.document import Document
from app.models.live_training import AttendanceLog, LiveTrainingSession
from app.models.membership import Membership
from app.models.onboarding import AgentOnboardingProgress, OnboardingStep
from app.models.training import AgentTrainingProgress, TrainingModule
from app.models.user import User
from app.services.email import send_test_email, smtp_is_configured
from app.services.organizations import can_manage_all_organizations
from app.services.render_usage import get_render_usage_overview


router = APIRouter(prefix="/admin", tags=["Admin"])


class EmailTestRequest(BaseModel):
    to_email: str = Field(min_length=3, max_length=255)

    @field_validator("to_email")
    @classmethod
    def email_must_look_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned


class EmailTestResponse(BaseModel):
    message: str
    smtp_host: str
    from_email: str


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this admin area.",
        )


def require_payment_admin_user(current_user: User) -> None:
    if current_user.role.name not in PAYMENT_ADMIN_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can access payment records.",
        )


def apply_agent_scope(query, current_user: User):
    if can_manage_all_organizations(current_user):
        return query
    if current_user.organization_id is None:
        return query.where(false())
    return query.where(AgentProfile.organization_id == current_user.organization_id)


def money_value(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


@router.post("/email-test", response_model=EmailTestResponse)
def send_email_test(
    request: EmailTestRequest,
    current_user: User = Depends(get_current_active_user),
) -> EmailTestResponse:
    require_admin_user(current_user)

    if not smtp_is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not configured yet. Check SMTP_HOST and SMTP_FROM_EMAIL in Render.",
        )

    try:
        email_sent = send_test_email(to_email=request.to_email)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email test failed: {exc}",
        ) from exc

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email could not be sent because SMTP settings are incomplete.",
        )

    return EmailTestResponse(
        message=f"Test email sent to {request.to_email}.",
        smtp_host=settings.smtp_host,
        from_email=settings.smtp_from_email,
    )


def agent_summary(agent: AgentProfile) -> dict[str, Any]:
    return {
        "id": agent.id,
        "user_id": agent.user_id,
        "organization_id": agent.organization_id,
        "agent_id": agent.agent_id,
        "first_name": agent.first_name,
        "last_name": agent.last_name,
        "email": agent.email,
        "personal_email": agent.personal_email,
        "company_email": agent.company_email,
        "phone": agent.phone,
        "business_name": agent.business_name,
        "status": agent.status,
        "joining_date": agent.joining_date,
        "portal_access_enabled": agent.portal_access_enabled,
    }


def membership_summary(membership: Membership, agent: AgentProfile) -> dict[str, Any]:
    return {
        "id": membership.id,
        "agent_id": membership.agent_id,
        "membership_type": membership.membership_type,
        "setup_fee_amount": money_value(membership.setup_fee_amount),
        "monthly_fee_amount": money_value(membership.monthly_fee_amount),
        "membership_status": membership.membership_status,
        "payment_status": membership.payment_status,
        "payment_method": membership.payment_method,
        "stripe_customer_id": membership.stripe_customer_id,
        "stripe_subscription_id": membership.stripe_subscription_id,
        "stripe_last_synced_at": membership.stripe_last_synced_at,
        "stripe_sync_status": membership.stripe_sync_status,
        "stripe_sync_error": membership.stripe_sync_error,
        "last_payment_date": membership.last_payment_date,
        "next_payment_date": membership.next_payment_date,
        "failed_payment_count": membership.failed_payment_count,
        "access_level": membership.access_level,
        "cancellation_date": membership.cancellation_date,
        "suspension_date": membership.suspension_date,
        "internal_notes": membership.internal_notes,
        "created_at": membership.created_at,
        "updated_at": membership.updated_at,
        "agent": agent_summary(agent),
    }


def document_summary(document: Document, agent: AgentProfile) -> dict[str, Any]:
    return {
        "id": document.id,
        "agent_id": document.agent_id,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "file_url": document.file_url,
        "uploaded_by": document.uploaded_by,
        "uploaded_date": document.uploaded_date,
        "requires_signature": document.requires_signature,
        "signed": document.signed,
        "signed_date": document.signed_date,
        "verified": document.verified,
        "verified_by": document.verified_by,
        "verified_date": document.verified_date,
        "expiry_date": document.expiry_date,
        "status": document.status,
        "notes": document.notes,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "agent": agent_summary(agent),
    }


def agent_name(agent: AgentProfile) -> str:
    return f"{agent.first_name} {agent.last_name}".strip() or agent.agent_id


def approval_queue_item(
    item_id: str,
    item_type: str,
    title: str,
    agent: AgentProfile,
    status: str,
    detail: str,
    link_url: str,
    created_at,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "item_type": item_type,
        "title": title,
        "agent_id": agent.id,
        "agent_reference": agent.agent_id,
        "agent_name": agent_name(agent),
        "agent_email": agent.email,
        "status": status,
        "detail": detail,
        "link_url": link_url,
        "created_at": created_at,
    }


def build_approval_queue(db: Session, current_user: User, agents: list[AgentProfile]) -> list[dict[str, Any]]:
    agent_ids = [agent.id for agent in agents]
    if not agent_ids:
        return []

    document_rows = db.execute(
        apply_agent_scope(
            select(Document, AgentProfile)
            .join(AgentProfile, Document.agent_id == AgentProfile.id)
            .where(Document.status.in_(["Uploaded", "Awaiting Review"]))
            .order_by(Document.created_at.desc(), Document.id.desc()),
            current_user,
        )
    ).all()
    document_items = [
        approval_queue_item(
            item_id=f"document-{document.id}",
            item_type="Document Review",
            title=document.document_type,
            agent=agent,
            status=document.status,
            detail=f"{document.file_name or 'Document'} needs verifying or rejecting.",
            link_url="/admin/documents",
            created_at=document.created_at,
        )
        for document, agent in document_rows
    ]

    onboarding_rows = db.execute(
        apply_agent_scope(
            select(AgentOnboardingProgress, OnboardingStep, AgentProfile)
            .join(OnboardingStep, AgentOnboardingProgress.step_id == OnboardingStep.id)
            .join(AgentProfile, AgentOnboardingProgress.agent_id == AgentProfile.id)
            .where(AgentOnboardingProgress.completion_status == "Awaiting Review")
            .order_by(AgentOnboardingProgress.updated_at.desc(), AgentOnboardingProgress.id.desc()),
            current_user,
        )
    ).all()
    onboarding_items = [
        approval_queue_item(
            item_id=f"onboarding-{progress.id}",
            item_type="Onboarding Approval",
            title=step.title,
            agent=agent,
            status=progress.completion_status,
            detail="Checklist item is waiting for admin approval.",
            link_url=f"/admin/agents/{agent.id}/onboarding",
            created_at=progress.updated_at,
        )
        for progress, step, agent in onboarding_rows
    ]

    final_approval_items = [
        approval_queue_item(
            item_id=f"final-approval-{agent.id}",
            item_type="Final Approval",
            title="Approve to Trade",
            agent=agent,
            status=agent.status,
            detail="Agent is waiting for the final trading approval decision.",
            link_url=f"/admin/agents/{agent.id}",
            created_at=agent.updated_at,
        )
        for agent in agents
        if agent.status == "Awaiting Final Approval"
    ]

    approval_items = document_items + onboarding_items + final_approval_items
    approval_items.sort(key=lambda item: item["created_at"].isoformat() if item["created_at"] else "", reverse=True)
    return approval_items


def session_summary(session: LiveTrainingSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "session_type": session.session_type,
        "description": session.description,
        "date": session.date,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "trainer_host": session.trainer_host,
        "meeting_link": session.meeting_link,
        "recording_link": session.recording_link,
        "attendance_required": session.attendance_required,
        "related_training_module_id": session.related_training_module_id,
        "follow_up_quiz_required": session.follow_up_quiz_required,
        "certificate_issued": session.certificate_issued,
        "notes": session.notes,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def attendance_summary(attendance: AttendanceLog, agent: AgentProfile, session: LiveTrainingSession) -> dict[str, Any]:
    return {
        "id": attendance.id,
        "session_id": attendance.session_id,
        "agent_id": attendance.agent_id,
        "attendance_status": attendance.attendance_status,
        "join_time": attendance.join_time,
        "leave_time": attendance.leave_time,
        "duration_attended": attendance.duration_attended,
        "marked_by": attendance.marked_by,
        "marked_date": attendance.marked_date,
        "notes": attendance.notes,
        "follow_up_required": attendance.follow_up_required,
        "watched_recording": attendance.watched_recording,
        "recording_completed_date": attendance.recording_completed_date,
        "created_at": attendance.created_at,
        "updated_at": attendance.updated_at,
        "agent": agent_summary(agent),
        "session": session_summary(session),
    }


def certificate_summary(certificate: Certificate, agent: AgentProfile) -> dict[str, Any]:
    return {
        "id": certificate.id,
        "agent_id": certificate.agent_id,
        "training_module_id": certificate.training_module_id,
        "certificate_name": certificate.certificate_name,
        "certificate_url": certificate.certificate_url,
        "issued_date": certificate.issued_date,
        "expiry_date": certificate.expiry_date,
        "renewal_required": certificate.renewal_required,
        "status": certificate.status,
        "created_at": certificate.created_at,
        "updated_at": certificate.updated_at,
        "agent": agent_summary(agent),
    }


@router.get("/dashboard-summary")
def get_admin_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    require_admin_user(current_user)
    agents = list(db.scalars(apply_agent_scope(select(AgentProfile).order_by(AgentProfile.id), current_user)))
    agent_ids = [agent.id for agent in agents]

    if not agent_ids:
        return {
            "total_agents": 0,
            "active_agents": 0,
            "in_onboarding": 0,
            "awaiting_payment": 0,
            "final_approval": 0,
            "failed_payments": 0,
            "overdue_training": 0,
            "missed_calls": 0,
            "compliance_hold": 0,
            "suspended_agents": 0,
            "documents_awaiting_review": 0,
            "policy_acceptance_count": 0,
            "missing_document_agents_count": 0,
            "expired_compliance_training_count": 0,
            "approval_queue": [],
            "approval_queue_total": 0,
        }

    failed_payments = db.scalar(
        apply_agent_scope(
            select(func.count(Membership.id))
            .select_from(Membership)
            .join(AgentProfile, Membership.agent_id == AgentProfile.id)
            .where(Membership.payment_status.in_(["Failed", "Overdue"])),
            current_user,
        )
    ) or 0
    overdue_training = db.scalar(
        apply_agent_scope(
            select(func.count(AgentTrainingProgress.id))
            .select_from(AgentTrainingProgress)
            .join(AgentProfile, AgentTrainingProgress.agent_id == AgentProfile.id)
            .where(AgentTrainingProgress.progress_status.in_(["Overdue", "Expired", "Failed"])),
            current_user,
        )
    ) or 0
    missed_calls = db.scalar(
        apply_agent_scope(
            select(func.count(AttendanceLog.id))
            .select_from(AttendanceLog)
            .join(AgentProfile, AttendanceLog.agent_id == AgentProfile.id)
            .where(AttendanceLog.attendance_status == "Missed"),
            current_user,
        )
    ) or 0
    documents_awaiting_review = db.scalar(
        apply_agent_scope(
            select(func.count(Document.id))
            .select_from(Document)
            .join(AgentProfile, Document.agent_id == AgentProfile.id)
            .where(Document.status.in_(["Uploaded", "Awaiting Review", "Requested"])),
            current_user,
        )
    ) or 0
    policy_acceptance_count = db.scalar(
        apply_agent_scope(
            select(func.count(PolicyAcceptance.id))
            .select_from(PolicyAcceptance)
            .join(AgentProfile, PolicyAcceptance.agent_id == AgentProfile.id),
            current_user,
        )
    ) or 0

    verified_documents = db.execute(
        select(Document.agent_id, Document.document_type)
        .where(Document.agent_id.in_(agent_ids))
        .where(Document.verified.is_(True))
        .where(Document.status == "Verified")
        .where(Document.document_type.in_(REQUIRED_COMPLIANCE_DOCUMENT_TYPES))
    ).all()
    verified_document_types_by_agent: dict[int, set[str]] = {agent_id: set() for agent_id in agent_ids}
    for agent_id, document_type in verified_documents:
        verified_document_types_by_agent.setdefault(agent_id, set()).add(document_type)
    missing_document_agents_count = sum(
        1
        for agent_id in agent_ids
        if any(document_type not in verified_document_types_by_agent.get(agent_id, set()) for document_type in REQUIRED_COMPLIANCE_DOCUMENT_TYPES)
    )

    expired_compliance_training_count = db.scalar(
        apply_agent_scope(
            select(func.count(func.distinct(AgentTrainingProgress.agent_id)))
            .select_from(AgentTrainingProgress)
            .join(AgentProfile, AgentTrainingProgress.agent_id == AgentProfile.id)
            .join(TrainingModule, AgentTrainingProgress.training_module_id == TrainingModule.id)
            .where(AgentTrainingProgress.expiry_date.is_not(None))
            .where(AgentTrainingProgress.expiry_date < date.today())
            .where(TrainingModule.mandatory.is_(True)),
            current_user,
        )
    ) or 0

    approval_queue = build_approval_queue(db, current_user, agents)

    return {
        "total_agents": len(agents),
        "active_agents": sum(1 for agent in agents if agent.status in {"Approved to Trade", "Active Agent"}),
        "in_onboarding": sum(1 for agent in agents if "Onboarding" in agent.status or "Training" in agent.status),
        "awaiting_payment": sum(1 for agent in agents if agent.status in {"Payment Pending", "Payment Overdue"}),
        "final_approval": sum(1 for agent in agents if agent.status == "Awaiting Final Approval"),
        "failed_payments": failed_payments,
        "overdue_training": overdue_training,
        "missed_calls": missed_calls,
        "compliance_hold": sum(1 for agent in agents if agent.status == "Compliance Hold"),
        "suspended_agents": sum(1 for agent in agents if agent.status == "Suspended"),
        "documents_awaiting_review": documents_awaiting_review,
        "policy_acceptance_count": policy_acceptance_count,
        "missing_document_agents_count": missing_document_agents_count,
        "expired_compliance_training_count": expired_compliance_training_count,
        "approval_queue": approval_queue[:12],
        "approval_queue_total": len(approval_queue),
    }


@router.get("/render-usage")
def get_admin_render_usage(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    require_admin_user(current_user)
    return get_render_usage_overview()


@router.get("/memberships")
def list_admin_memberships(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    require_payment_admin_user(current_user)
    rows = db.execute(
        apply_agent_scope(
            select(Membership, AgentProfile)
            .join(AgentProfile, Membership.agent_id == AgentProfile.id)
            .order_by(AgentProfile.id),
            current_user,
        )
    ).all()
    return [membership_summary(membership, agent) for membership, agent in rows]


@router.get("/documents")
def list_admin_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    require_admin_user(current_user)
    rows = db.execute(
        apply_agent_scope(
            select(Document, AgentProfile)
            .join(AgentProfile, Document.agent_id == AgentProfile.id)
            .order_by(Document.uploaded_date.desc(), Document.id.desc()),
            current_user,
        )
    ).all()
    return [document_summary(document, agent) for document, agent in rows]


@router.get("/attendance")
def list_admin_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    require_admin_user(current_user)
    rows = db.execute(
        apply_agent_scope(
            select(AttendanceLog, AgentProfile, LiveTrainingSession)
            .join(AgentProfile, AttendanceLog.agent_id == AgentProfile.id)
            .join(LiveTrainingSession, AttendanceLog.session_id == LiveTrainingSession.id)
            .order_by(LiveTrainingSession.date, LiveTrainingSession.start_time, LiveTrainingSession.id),
            current_user,
        )
    ).all()
    return [attendance_summary(attendance, agent, session) for attendance, agent, session in rows]


@router.get("/certificates")
def list_admin_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    require_admin_user(current_user)
    rows = db.execute(
        apply_agent_scope(
            select(Certificate, AgentProfile)
            .join(AgentProfile, Certificate.agent_id == AgentProfile.id)
            .order_by(Certificate.issued_date.desc(), Certificate.id.desc()),
            current_user,
        )
    ).all()
    return [certificate_summary(certificate, agent) for certificate, agent in rows]
