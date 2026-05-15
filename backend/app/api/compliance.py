from datetime import date, datetime, timezone
from textwrap import wrap

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.compliance import REQUIRED_COMPLIANCE_DOCUMENT_TYPES
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.compliance import CompliancePolicy, PolicyAcceptance
from app.models.document import Document
from app.models.training import AgentTrainingProgress, TrainingModule
from app.models.user import User
from app.schemas.compliance import (
    AdminComplianceDashboardRead,
    AgentComplianceStatusRead,
    ComplianceAgentIssue,
    CompliancePolicyCreate,
    CompliancePolicyRead,
    PolicyAcceptanceRead,
    PolicyAcceptanceRequest,
)
from app.services.organizations import can_manage_all_organizations
from app.services.audit import create_audit_log


router = APIRouter(tags=["Compliance Centre"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage the compliance centre.",
        )


def get_policy_or_404(db: Session, policy_id: int) -> CompliancePolicy:
    policy = db.get(CompliancePolicy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance policy not found.",
        )
    return policy


def get_own_agent_profile_or_404(db: Session, current_user: User) -> AgentProfile:
    agent_profile = db.scalar(select(AgentProfile).where(AgentProfile.user_id == current_user.id))
    if agent_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found for this user.",
        )
    return agent_profile


def get_required_policies(db: Session) -> list[CompliancePolicy]:
    return list(
        db.scalars(
            select(CompliancePolicy)
            .where(
                CompliancePolicy.published_status == "Published",
                CompliancePolicy.requires_acceptance.is_(True),
            )
            .order_by(CompliancePolicy.id)
        )
    )


def get_policy_acceptances(db: Session, agent_profile: AgentProfile) -> list[PolicyAcceptance]:
    return list(
        db.scalars(
            select(PolicyAcceptance)
            .options(selectinload(PolicyAcceptance.policy))
            .options(selectinload(PolicyAcceptance.agent))
            .options(selectinload(PolicyAcceptance.accepted_by_user))
            .where(PolicyAcceptance.agent_id == agent_profile.id)
            .order_by(PolicyAcceptance.accepted_date.desc(), PolicyAcceptance.id.desc())
        )
    )


def get_missing_document_types(db: Session, agent_profile: AgentProfile) -> list[str]:
    documents = list(db.scalars(select(Document).where(Document.agent_id == agent_profile.id)))
    verified_document_types = {
        document.document_type
        for document in documents
        if document.verified and document.status == "Verified"
    }
    return [
        document_type
        for document_type in REQUIRED_COMPLIANCE_DOCUMENT_TYPES
        if document_type not in verified_document_types
    ]


def get_document_review_lists(db: Session, agent_profile: AgentProfile) -> tuple[list[str], list[str]]:
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.agent_id == agent_profile.id)
            .order_by(Document.uploaded_date.desc(), Document.id.desc())
        )
    )
    awaiting_review = [
        document.file_name
        for document in documents
        if document.status == "Awaiting Review"
    ]
    rejected = [
        document.file_name
        for document in documents
        if document.status == "Rejected"
    ]
    return awaiting_review, rejected


def is_compliance_training_module(training_module: TrainingModule) -> bool:
    category_name = training_module.category.name if training_module.category is not None else ""
    title = training_module.title.lower()
    return (
        category_name == "Compliance"
        or "compliance" in title
        or "gdpr" in title
        or "atol" in title
        or "tta" in title
    )


def get_compliance_training_issues(db: Session, agent_profile: AgentProfile) -> tuple[list[str], list[str]]:
    training_modules = list(
        db.scalars(
            select(TrainingModule)
            .options(selectinload(TrainingModule.category))
            .where(
                TrainingModule.mandatory.is_(True),
                TrainingModule.published_status == "Published",
            )
            .order_by(TrainingModule.id)
        )
    )
    compliance_modules = [
        training_module
        for training_module in training_modules
        if is_compliance_training_module(training_module)
    ]
    progress_records = list(
        db.scalars(
            select(AgentTrainingProgress).where(
                AgentTrainingProgress.agent_id == agent_profile.id,
                AgentTrainingProgress.training_module_id.in_([module.id for module in compliance_modules] or [0]),
            )
        )
    )
    progress_by_module_id = {
        progress.training_module_id: progress
        for progress in progress_records
    }

    missing_training = []
    expired_training = []
    today = date.today()
    for training_module in compliance_modules:
        progress = progress_by_module_id.get(training_module.id)
        if progress is None or progress.progress_status != "Complete":
            missing_training.append(training_module.title)
            continue
        if training_module.quiz_required and progress.passed is not True:
            missing_training.append(training_module.title)
            continue
        if progress.expiry_date is not None and progress.expiry_date < today:
            expired_training.append(training_module.title)

    return expired_training, missing_training


def get_agent_compliance_status(db: Session, agent_profile: AgentProfile) -> AgentComplianceStatusRead:
    required_policies = get_required_policies(db)
    acceptances = get_policy_acceptances(db, agent_profile)
    accepted_policy_ids = {
        acceptance.policy_id
        for acceptance in acceptances
        if acceptance.policy_version == acceptance.policy.version
    }
    accepted_policy_titles = [
        acceptance.policy.title
        for acceptance in acceptances
        if acceptance.policy_version == acceptance.policy.version
    ]
    missing_policy_titles = [
        policy.title
        for policy in required_policies
        if policy.id not in accepted_policy_ids
    ]
    missing_document_types = get_missing_document_types(db, agent_profile)
    documents_awaiting_review, rejected_documents = get_document_review_lists(db, agent_profile)
    expired_training, missing_training = get_compliance_training_issues(db, agent_profile)

    checklist = [
        "Accept all published compliance policies",
        "Complete compliance training",
        "Keep ID and proof of address verified",
        "Follow customer money handling rules",
        "Follow advertising and social media rules",
        "Follow the complaints process",
    ]
    policies_by_type = {
        policy_type: [
            policy.title
            for policy in required_policies
            if policy.policy_type == policy_type
        ]
        for policy_type in (
            "Customer Money Handling",
            "Advertising and Social Media",
            "Complaints Process",
        )
    }

    return AgentComplianceStatusRead(
        agent_id=agent_profile.id,
        agent_name=f"{agent_profile.first_name} {agent_profile.last_name}",
        agent_status=agent_profile.status,
        compliance_hold=agent_profile.status == "Compliance Hold",
        required_policy_count=len(required_policies),
        accepted_policy_count=len(accepted_policy_ids),
        accepted_policy_ids=sorted(accepted_policy_ids),
        missing_policy_titles=missing_policy_titles,
        accepted_policy_titles=accepted_policy_titles,
        missing_document_types=missing_document_types,
        documents_awaiting_review=documents_awaiting_review,
        rejected_documents=rejected_documents,
        expired_compliance_training=expired_training,
        missing_compliance_training=missing_training,
        compliance_checklist=checklist,
        customer_money_handling_rules=policies_by_type["Customer Money Handling"],
        advertising_and_social_media_rules=policies_by_type["Advertising and Social Media"],
        complaints_process=policies_by_type["Complaints Process"],
    )


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None
    return request.client.host if request.client else None


def build_acceptance_statement(policy: CompliancePolicy) -> str:
    return (
        f"I confirm that I have opened, read, understood, and accepted "
        f"{policy.title} version {policy.version}."
    )


@router.get("/compliance/policies", response_model=list[CompliancePolicyRead])
def list_compliance_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CompliancePolicy]:
    query = select(CompliancePolicy).order_by(CompliancePolicy.id)
    if not is_admin_user(current_user):
        query = query.where(CompliancePolicy.published_status == "Published")
    return list(db.scalars(query))


@router.post("/compliance/policies", response_model=CompliancePolicyRead, status_code=status.HTTP_201_CREATED)
def create_compliance_policy(
    request: CompliancePolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompliancePolicy:
    require_admin_user(current_user)
    policy = CompliancePolicy(
        title=request.title,
        policy_type=request.policy_type,
        content=request.content,
        version=request.version,
        requires_acceptance=request.requires_acceptance,
        published_status=request.published_status,
        created_by=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/compliance/policies/{policy_id}/accept", response_model=PolicyAcceptanceRead)
def accept_compliance_policy(
    policy_id: int,
    request_context: Request,
    request: PolicyAcceptanceRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PolicyAcceptance:
    policy = get_policy_or_404(db, policy_id)
    if policy.published_status != "Published":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only published policies can be accepted.",
        )

    agent_profile = get_own_agent_profile_or_404(db, current_user)
    acceptance = db.scalar(
        select(PolicyAcceptance).where(
            PolicyAcceptance.policy_id == policy.id,
            PolicyAcceptance.agent_id == agent_profile.id,
            PolicyAcceptance.policy_version == policy.version,
        )
    )
    accepted_at = datetime.now(timezone.utc)
    ip_address = get_client_ip(request_context)
    user_agent = request_context.headers.get("user-agent")
    acceptance_statement = build_acceptance_statement(policy)
    if acceptance is None:
        acceptance = PolicyAcceptance(
            policy_id=policy.id,
            agent_id=agent_profile.id,
            accepted_by=current_user.id,
            accepted_date=accepted_at,
            policy_version=policy.version,
            ip_address=ip_address,
            user_agent=user_agent,
            acceptance_statement=acceptance_statement,
            notes=request.notes if request is not None else None,
        )
        db.add(acceptance)
    else:
        acceptance.accepted_by = current_user.id
        acceptance.accepted_date = accepted_at
        acceptance.policy_version = policy.version
        acceptance.ip_address = ip_address
        acceptance.user_agent = user_agent
        acceptance.acceptance_statement = acceptance_statement
        if request is not None:
            acceptance.notes = request.notes

    create_audit_log(
        db,
        action_type="Policy accepted",
        description=f"{agent_profile.first_name} {agent_profile.last_name} accepted {policy.title} version {policy.version}.",
        created_by=current_user.id,
        user_id=current_user.id,
        agent_id=agent_profile.id,
        new_value=policy.title,
        ip_address=ip_address,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This policy acceptance could not be saved.",
        ) from None

    acceptance = db.scalar(
        select(PolicyAcceptance)
        .options(selectinload(PolicyAcceptance.policy))
        .options(selectinload(PolicyAcceptance.agent))
        .options(selectinload(PolicyAcceptance.accepted_by_user))
        .where(PolicyAcceptance.id == acceptance.id)
    )
    if acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy acceptance was saved but could not be loaded.",
        )
    return acceptance


@router.get("/policy-acceptances/{acceptance_id}/receipt.pdf")
def export_policy_acceptance_receipt(
    acceptance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    acceptance = db.scalar(
        select(PolicyAcceptance)
        .options(selectinload(PolicyAcceptance.policy))
        .options(selectinload(PolicyAcceptance.agent))
        .options(selectinload(PolicyAcceptance.accepted_by_user))
        .where(PolicyAcceptance.id == acceptance_id)
    )
    if acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy acceptance record not found.",
        )

    if not is_admin_user(current_user):
        agent_profile = get_own_agent_profile_or_404(db, current_user)
        if acceptance.agent_id != agent_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only export your own policy acceptance receipts.",
            )
    elif not can_manage_all_organizations(current_user):
        if current_user.organization_id is None or acceptance.agent.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only export receipts for your organisation.",
            )

    pdf_bytes = build_policy_acceptance_pdf(acceptance)
    filename = safe_pdf_filename(
        f"policy-acceptance-{acceptance.agent_name or acceptance.agent_id}-{acceptance.policy.title}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def build_policy_acceptance_pdf(acceptance: PolicyAcceptance) -> bytes:
    accepted_at = acceptance.accepted_date.astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    lines = [
        "One Travel Club",
        "Policy Acceptance Receipt",
        "",
        f"Agent: {acceptance.agent_name or 'Not shown'}",
        f"Policy: {acceptance.policy.title}",
        f"Policy type: {acceptance.policy.policy_type}",
        f"Policy version: {acceptance.policy_version}",
        f"Accepted date: {accepted_at}",
        f"Accepted by: {acceptance.accepted_by_email or acceptance.accepted_by}",
        f"IP address: {acceptance.ip_address or 'Not recorded'}",
        f"Browser/device: {acceptance.user_agent or 'Not recorded'}",
        "",
        "Acceptance statement:",
        acceptance.acceptance_statement or build_acceptance_statement(acceptance.policy),
        "",
        "Policy content at time of export:",
    ]
    lines.extend(policy_content_lines(acceptance.policy.content))
    return simple_pdf(lines)


def policy_content_lines(content: str) -> list[str]:
    lines: list[str] = []
    for paragraph in content.splitlines() or [content]:
        cleaned = paragraph.strip()
        if not cleaned:
            lines.append("")
            continue
        lines.extend(wrap(cleaned, width=90) or [""])
    return lines


def simple_pdf(lines: list[str]) -> bytes:
    page_line_limit = 46
    wrapped_lines = [
        line
        for raw_line in lines
        for line in (wrap(raw_line, width=90) if len(raw_line) > 90 else [raw_line])
    ]
    pages = [
        wrapped_lines[index : index + page_line_limit]
        for index in range(0, len(wrapped_lines), page_line_limit)
    ] or [[]]

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_refs = []
    for page_lines in pages:
        page_object_number = len(objects) + 1
        content_object_number = len(objects) + 2
        page_refs.append(f"{page_object_number} 0 R")
        content = pdf_page_content(page_lines)
        content_bytes = content.encode("latin-1", "replace")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_object_number} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(
            b"<< /Length "
            + str(len(content_bytes)).encode("ascii")
            + b" >>\nstream\n"
            + content_bytes
            + b"\nendstream"
        )

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>".encode("latin-1")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def pdf_page_content(lines: list[str]) -> str:
    commands = ["BT", "/F1 10 Tf", "13 TL", "50 750 Td"]
    for line in lines:
        commands.append(f"({pdf_escape(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands)


def pdf_escape(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def safe_pdf_filename(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in ("-", "_", ".") else "-" for character in value)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-") or "policy-acceptance.pdf"


@router.get("/agents/{agent_profile_id}/compliance-status", response_model=AgentComplianceStatusRead)
def get_agent_compliance_status_endpoint(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentComplianceStatusRead:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return get_agent_compliance_status(db, agent_profile)


@router.get("/admin/compliance-dashboard", response_model=AdminComplianceDashboardRead)
def get_admin_compliance_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AdminComplianceDashboardRead:
    require_admin_user(current_user)
    agent_query = select(AgentProfile).order_by(AgentProfile.id)
    if not can_manage_all_organizations(current_user):
        if current_user.organization_id is None:
            agents = []
        else:
            agents = list(db.scalars(agent_query.where(AgentProfile.organization_id == current_user.organization_id)))
    else:
        agents = list(db.scalars(agent_query))
    agent_ids = [agent.id for agent in agents]
    missing_document_agents = []
    expired_training_agents = []
    compliance_hold_agents = []

    for agent_profile in agents:
        missing_documents = get_missing_document_types(db, agent_profile)
        if missing_documents:
            missing_document_agents.append(
                ComplianceAgentIssue(
                    agent_id=agent_profile.id,
                    agent_name=f"{agent_profile.first_name} {agent_profile.last_name}",
                    status=agent_profile.status,
                    issues=missing_documents,
                )
            )

        expired_training, _missing_training = get_compliance_training_issues(db, agent_profile)
        if expired_training:
            expired_training_agents.append(
                ComplianceAgentIssue(
                    agent_id=agent_profile.id,
                    agent_name=f"{agent_profile.first_name} {agent_profile.last_name}",
                    status=agent_profile.status,
                    issues=expired_training,
                )
            )

        if agent_profile.status == "Compliance Hold":
            compliance_hold_agents.append(
                ComplianceAgentIssue(
                    agent_id=agent_profile.id,
                    agent_name=f"{agent_profile.first_name} {agent_profile.last_name}",
                    status=agent_profile.status,
                    issues=["Compliance Hold"],
                )
            )

    document_query = select(Document).where(Document.status == "Awaiting Review")
    if agent_ids:
        document_query = document_query.where(Document.agent_id.in_(agent_ids))
    elif not can_manage_all_organizations(current_user):
        document_query = document_query.where(Document.agent_id.in_([0]))
    documents_awaiting_review = len(list(db.scalars(document_query)))

    acceptance_query = (
        select(PolicyAcceptance)
        .options(selectinload(PolicyAcceptance.policy))
        .options(selectinload(PolicyAcceptance.agent))
        .options(selectinload(PolicyAcceptance.accepted_by_user))
        .order_by(PolicyAcceptance.accepted_date.desc(), PolicyAcceptance.id.desc())
    )
    if agent_ids:
        acceptance_query = acceptance_query.where(PolicyAcceptance.agent_id.in_(agent_ids))
    elif not can_manage_all_organizations(current_user):
        acceptance_query = acceptance_query.where(PolicyAcceptance.agent_id.in_([0]))
    acceptances = list(
        db.scalars(acceptance_query)
    )

    return AdminComplianceDashboardRead(
        total_agents=len(agents),
        agents_on_compliance_hold=len(compliance_hold_agents),
        documents_awaiting_review=documents_awaiting_review,
        policy_acceptance_count=len(acceptances),
        missing_document_agents=missing_document_agents,
        expired_compliance_training_agents=expired_training_agents,
        compliance_hold_agents=compliance_hold_agents,
        recent_policy_acceptances=acceptances[:20],
    )
