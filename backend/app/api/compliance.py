from datetime import date, datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
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
from app.models.training import AgentTrainingProgress, TrainingCategory, TrainingModule
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
        if acceptance.policy_id in accepted_policy_ids
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
        )
    )
    if acceptance is None:
        acceptance = PolicyAcceptance(
            policy_id=policy.id,
            agent_id=agent_profile.id,
            accepted_by=current_user.id,
            accepted_date=datetime.now(timezone.utc),
            policy_version=policy.version,
            notes=request.notes if request is not None else None,
        )
        db.add(acceptance)
    else:
        acceptance.accepted_by = current_user.id
        acceptance.accepted_date = datetime.now(timezone.utc)
        acceptance.policy_version = policy.version
        if request is not None:
            acceptance.notes = request.notes

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
        .where(PolicyAcceptance.id == acceptance.id)
    )
    if acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy acceptance was saved but could not be loaded.",
        )
    return acceptance


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
    agents = list(db.scalars(select(AgentProfile).order_by(AgentProfile.id)))
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

    documents_awaiting_review = len(
        list(
            db.scalars(
                select(Document).where(Document.status == "Awaiting Review")
            )
        )
    )
    acceptances = list(
        db.scalars(
            select(PolicyAcceptance)
            .options(selectinload(PolicyAcceptance.policy))
            .order_by(PolicyAcceptance.accepted_date.desc(), PolicyAcceptance.id.desc())
        )
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
