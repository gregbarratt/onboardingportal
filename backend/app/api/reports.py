from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.agents import is_admin_user
from app.api.deps import get_current_active_user
from app.core.agent_statuses import is_onboarding_tracking_exempt
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.certificate import Certificate
from app.models.document import Document
from app.models.live_training import AttendanceLog
from app.models.membership import Membership
from app.models.training import AgentTrainingProgress, TrainingAssignment, TrainingModule
from app.models.user import User
from app.schemas.reports import (
    AdminReportsRead,
    AgentsByStatusReportRow,
    AttendanceReportRow,
    ComplianceExpiryReportRow,
    DocumentsAwaitingReviewReportRow,
    FinalApprovalQueueReportRow,
    OverdueTrainingReportRow,
    PaymentStatusReportRow,
    TrainingCompletionReportRow,
)
from app.services.final_approval import build_final_approval_status
from app.services.organizations import can_manage_all_organizations


router = APIRouter(prefix="/admin/reports", tags=["Admin Reports"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view reports.",
        )


@router.get("", response_model=AdminReportsRead)
def get_admin_reports(
    expiry_days: int = Query(default=60, ge=0, le=730),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AdminReportsRead:
    require_admin_user(current_user)

    agents = get_visible_agents(db, current_user)
    agent_ids = [agent.id for agent in agents]
    tracked_agents = [agent for agent in agents if not is_onboarding_tracking_exempt(agent.status)]
    tracked_agent_ids = [agent.id for agent in tracked_agents]
    return AdminReportsRead(
        agents_by_status=build_agents_by_status_report(agents),
        payment_status_report=build_payment_status_report(db, agents),
        training_completion_report=build_training_completion_report(db, tracked_agents),
        overdue_training_report=build_overdue_training_report(db, tracked_agent_ids),
        attendance_report=build_attendance_report(db, agent_ids),
        compliance_expiry_report=build_compliance_expiry_report(db, expiry_days, tracked_agent_ids),
        documents_awaiting_review=build_documents_awaiting_review_report(db, agent_ids),
        final_approval_queue=build_final_approval_queue_report(db, tracked_agents),
    )


def get_visible_agents(db: Session, current_user: User) -> list[AgentProfile]:
    query = select(AgentProfile).order_by(AgentProfile.last_name, AgentProfile.first_name)
    if not can_manage_all_organizations(current_user):
        if current_user.organization_id is None:
            return []
        query = query.where(AgentProfile.organization_id == current_user.organization_id)
    return list(db.scalars(query))


def build_agents_by_status_report(agents: list[AgentProfile]) -> list[AgentsByStatusReportRow]:
    totals: dict[str, int] = {}
    for agent in agents:
        totals[agent.status] = totals.get(agent.status, 0) + 1
    return [
        AgentsByStatusReportRow(id=status_text.lower().replace(" ", "-"), status=status_text, total=total)
        for status_text, total in sorted(totals.items())
    ]


def build_payment_status_report(db: Session, agents: list[AgentProfile]) -> list[PaymentStatusReportRow]:
    memberships = {
        membership.agent_id: membership
        for membership in db.scalars(select(Membership))
    }

    rows = []
    for agent in agents:
        membership = memberships.get(agent.id)
        rows.append(
            PaymentStatusReportRow(
                id=agent.id,
                agent_id=agent.id,
                agent_name=agent_name(agent),
                agent_status=agent.status,
                membership_status=membership.membership_status if membership else "Not set",
                payment_status=membership.payment_status if membership else "Not set",
                next_payment_date=membership.next_payment_date if membership else None,
                failed_payment_count=membership.failed_payment_count if membership else 0,
            )
        )
    return rows


def build_training_completion_report(db: Session, agents: list[AgentProfile]) -> list[TrainingCompletionReportRow]:
    mandatory_modules = list(
        db.scalars(
            select(TrainingModule)
            .where(
                TrainingModule.training_track == "Onboarding",
                TrainingModule.published_status == "Published",
                TrainingModule.mandatory.is_(True),
            )
            .order_by(TrainingModule.id)
        )
    )
    module_ids = [module.id for module in mandatory_modules]
    modules_by_id = {module.id: module for module in mandatory_modules}
    progress_records = list(
        db.scalars(
            select(AgentTrainingProgress)
            .where(AgentTrainingProgress.training_module_id.in_(module_ids or [0]))
        )
    )
    progress_by_agent: dict[int, list[AgentTrainingProgress]] = {}
    for progress in progress_records:
        progress_by_agent.setdefault(progress.agent_id, []).append(progress)

    rows = []
    for agent in agents:
        completed = 0
        failed = 0
        for progress in progress_by_agent.get(agent.id, []):
            module = modules_by_id.get(progress.training_module_id)
            if module is None:
                continue
            if is_training_complete(module, progress):
                completed += 1
            elif progress.progress_status == "Failed" or progress.passed is False:
                failed += 1

        total = len(mandatory_modules)
        percent = round((completed / total) * 100) if total else 0
        rows.append(
            TrainingCompletionReportRow(
                id=agent.id,
                agent_id=agent.id,
                agent_name=agent_name(agent),
                agent_status=agent.status,
                total_mandatory_modules=total,
                completed_mandatory_modules=completed,
                failed_modules=failed,
                completion_percent=percent,
            )
        )
    return rows


def build_overdue_training_report(db: Session, agent_ids: list[int]) -> list[OverdueTrainingReportRow]:
    today = date.today()
    if not agent_ids:
        return []
    assignments = list(
        db.scalars(
            select(TrainingAssignment)
            .options(
                selectinload(TrainingAssignment.agent),
                selectinload(TrainingAssignment.training_module),
                selectinload(TrainingAssignment.progress),
            )
            .where(TrainingAssignment.due_date.is_not(None), TrainingAssignment.due_date < today)
            .where(TrainingAssignment.agent_id.in_(agent_ids))
            .order_by(TrainingAssignment.due_date)
        )
    )
    rows = []
    for assignment in assignments:
        progress_status = assignment.progress.progress_status if assignment.progress else "Not Started"
        if progress_status == "Complete":
            continue
        rows.append(
            OverdueTrainingReportRow(
                id=assignment.id,
                agent_id=assignment.agent_id,
                agent_name=agent_name(assignment.agent),
                module_title=assignment.training_module.title,
                due_date=assignment.due_date,
                days_overdue=(today - assignment.due_date).days,
                progress_status=progress_status,
            )
        )
    return rows


def build_attendance_report(db: Session, agent_ids: list[int]) -> list[AttendanceReportRow]:
    if not agent_ids:
        return []
    attendance_rows = list(
        db.scalars(
            select(AttendanceLog)
            .options(
                selectinload(AttendanceLog.agent),
                selectinload(AttendanceLog.session),
            )
            .where(AttendanceLog.agent_id.in_(agent_ids))
            .join(AttendanceLog.session)
            .order_by(AttendanceLog.id.desc())
            .limit(100)
        )
    )
    return [
        AttendanceReportRow(
            id=attendance.id,
            agent_id=attendance.agent_id,
            agent_name=agent_name(attendance.agent),
            session_title=attendance.session.title,
            session_type=attendance.session.session_type,
            session_date=attendance.session.date,
            attendance_status=attendance.attendance_status,
            follow_up_required=attendance.follow_up_required,
        )
        for attendance in attendance_rows
    ]


def build_compliance_expiry_report(db: Session, expiry_days: int, agent_ids: list[int]) -> list[ComplianceExpiryReportRow]:
    today = date.today()
    cutoff = today + timedelta(days=expiry_days)
    rows: list[ComplianceExpiryReportRow] = []
    if not agent_ids:
        return rows

    certificates = list(
        db.scalars(
            select(Certificate)
            .options(
                selectinload(Certificate.agent),
                selectinload(Certificate.training_module),
            )
            .where(Certificate.expiry_date.is_not(None), Certificate.expiry_date <= cutoff)
            .where(Certificate.agent_id.in_(agent_ids))
            .order_by(Certificate.expiry_date)
        )
    )
    for certificate in certificates:
        rows.append(
            ComplianceExpiryReportRow(
                id=f"certificate-{certificate.id}",
                agent_id=certificate.agent_id,
                agent_name=agent_name(certificate.agent),
                item_type="Certificate",
                item_name=certificate.certificate_name,
                expiry_date=certificate.expiry_date,
                days_until_expiry=(certificate.expiry_date - today).days,
                status=certificate.status,
            )
        )

    documents = list(
        db.scalars(
            select(Document)
            .options(selectinload(Document.agent))
            .where(Document.expiry_date.is_not(None), Document.expiry_date <= cutoff)
            .where(Document.agent_id.in_(agent_ids))
            .order_by(Document.expiry_date)
        )
    )
    for document in documents:
        rows.append(
            ComplianceExpiryReportRow(
                id=f"document-{document.id}",
                agent_id=document.agent_id,
                agent_name=agent_name(document.agent),
                item_type="Document",
                item_name=document.document_type,
                expiry_date=document.expiry_date,
                days_until_expiry=(document.expiry_date - today).days,
                status=document.status,
            )
        )

    return rows


def build_documents_awaiting_review_report(db: Session, agent_ids: list[int]) -> list[DocumentsAwaitingReviewReportRow]:
    if not agent_ids:
        return []
    documents = list(
        db.scalars(
            select(Document)
            .options(selectinload(Document.agent))
            .where(Document.status.in_(("Uploaded", "Awaiting Review")))
            .where(Document.agent_id.in_(agent_ids))
            .order_by(Document.uploaded_date, Document.id)
        )
    )
    return [
        DocumentsAwaitingReviewReportRow(
            id=document.id,
            agent_id=document.agent_id,
            agent_name=agent_name(document.agent),
            document_type=document.document_type,
            file_name=document.file_name,
            uploaded_date=document.uploaded_date,
            status=document.status,
        )
        for document in documents
    ]


def build_final_approval_queue_report(db: Session, agents: list[AgentProfile]) -> list[FinalApprovalQueueReportRow]:
    rows = []
    for agent in agents:
        approval = build_final_approval_status(db, agent)
        if not approval["ready_for_approval"] and agent.status != "Awaiting Final Approval":
            continue

        rows.append(
            FinalApprovalQueueReportRow(
                id=agent.id,
                agent_id=agent.id,
                agent_name=agent_name(agent),
                agent_status=agent.status,
                ready_for_approval=approval["ready_for_approval"],
                missing_requirements=approval["missing_requirements"],
            )
        )
    return rows


def is_training_complete(module: TrainingModule, progress: AgentTrainingProgress) -> bool:
    if progress.progress_status != "Complete":
        return False
    if module.quiz_required and progress.passed is not True:
        return False
    return True


def agent_name(agent: AgentProfile | None) -> str:
    if agent is None:
        return "Agent"
    return " ".join(part for part in (agent.first_name, agent.last_name) if part) or agent.email or f"Agent {agent.id}"
