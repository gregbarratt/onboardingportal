from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.agent_statuses import is_onboarding_tracking_exempt
from app.models.agent_profile import AgentProfile
from app.models.document import Document
from app.models.membership import Membership
from app.models.onboarding import AgentOnboardingProgress, OnboardingStep
from app.models.training import AgentTrainingProgress, TrainingModule


PROFILE_STEP_TITLE = "Complete personal profile"
BANK_STEP_TITLE = "Add bank details for commission payments"
ID_DOCUMENT_STEP_TITLE = "Upload ID document"
PROOF_OF_ADDRESS_STEP_TITLE = "Upload proof of address"
CONTRACT_STEP_TITLE = "Sign contractor agreement"
MEMBERSHIP_TERMS_STEP_TITLE = "Accept membership terms"
FINAL_ASSESSMENT_STEP_TITLE = "Complete final assessment"
ADMIN_FINAL_APPROVAL_STEP_TITLE = "Admin final approval"

APPROVED_AGENT_STATUSES = {"Approved to Trade", "Active Agent"}
REQUIRED_PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "personal_email",
    "company_email",
    "phone",
    "business_name",
    "joining_date",
    "address",
    "postcode",
)
REQUIRED_BANK_FIELDS = (
    "commission_bank_name",
    "commission_account_name",
    "commission_sort_code",
    "commission_account_number",
)


def sync_agent_onboarding_progress(
    db: Session,
    agent_profile: AgentProfile,
    *,
    actor_user_id: int | None = None,
) -> None:
    """Keep visible checklist rows aligned with work completed elsewhere."""
    if is_onboarding_tracking_exempt(agent_profile.status):
        return

    _sync_profile_step(db, agent_profile, actor_user_id)
    _sync_bank_details_step(db, agent_profile, actor_user_id)
    _sync_document_upload_step(db, agent_profile, ID_DOCUMENT_STEP_TITLE, "ID Document", actor_user_id)
    _sync_document_upload_step(db, agent_profile, PROOF_OF_ADDRESS_STEP_TITLE, "Proof of Address", actor_user_id)
    _sync_contract_step(db, agent_profile, actor_user_id)
    _sync_membership_terms_step(db, agent_profile, actor_user_id)
    _sync_final_assessment_step(db, agent_profile, actor_user_id)
    _sync_admin_final_approval_step(db, agent_profile, actor_user_id)


def _sync_profile_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    if not _text_present(agent_profile.business_name):
        agent_profile.business_name = "N/A"
    status = "Complete" if _all_fields_present(agent_profile, REQUIRED_PROFILE_FIELDS) else "In Progress"
    _set_step_status(db, agent_profile.id, PROFILE_STEP_TITLE, status, actor_user_id=actor_user_id)


def _sync_bank_details_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    status = "Complete" if _all_fields_present(agent_profile, REQUIRED_BANK_FIELDS) else "Not Started"
    _set_step_status(db, agent_profile.id, BANK_STEP_TITLE, status, actor_user_id=actor_user_id)


def _sync_document_upload_step(
    db: Session,
    agent_profile: AgentProfile,
    step_title: str,
    document_type: str,
    actor_user_id: int | None,
) -> None:
    document = _latest_document(db, agent_profile.id, document_type)
    if document is None:
        _set_step_status(db, agent_profile.id, step_title, "Not Started")
        return

    if document.status == "Rejected":
        _set_step_status(db, agent_profile.id, step_title, "Rejected", evidence_file_or_link=document.file_url)
        return

    _set_step_status(
        db,
        agent_profile.id,
        step_title,
        "Complete",
        actor_user_id=actor_user_id or document.uploaded_by,
        evidence_file_or_link=document.file_url,
        approved_by=document.verified_by if document.verified else None,
        approved_date=document.verified_date if document.verified else None,
    )


def _sync_contract_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    document = _latest_document(db, agent_profile.id, "Contractor Agreement")
    if document is None:
        _set_step_status(db, agent_profile.id, CONTRACT_STEP_TITLE, "Not Started")
        return

    if document.status == "Rejected":
        _set_step_status(db, agent_profile.id, CONTRACT_STEP_TITLE, "Rejected", evidence_file_or_link=document.file_url)
        return

    status = "Complete" if document.signed or document.verified else "Awaiting Review"
    _set_step_status(
        db,
        agent_profile.id,
        CONTRACT_STEP_TITLE,
        status,
        actor_user_id=actor_user_id or document.uploaded_by,
        evidence_file_or_link=document.file_url,
        approved_by=document.verified_by if document.verified else None,
        approved_date=document.verified_date if document.verified else None,
    )


def _sync_membership_terms_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    document = _latest_document(db, agent_profile.id, "Membership Terms")
    if document is not None:
        if document.status == "Rejected":
            _set_step_status(db, agent_profile.id, MEMBERSHIP_TERMS_STEP_TITLE, "Rejected", evidence_file_or_link=document.file_url)
            return
        status = "Complete" if document.signed or document.verified else "Awaiting Review"
        _set_step_status(
            db,
            agent_profile.id,
            MEMBERSHIP_TERMS_STEP_TITLE,
            status,
            actor_user_id=actor_user_id or document.uploaded_by,
            evidence_file_or_link=document.file_url,
            approved_by=document.verified_by if document.verified else None,
            approved_date=document.verified_date if document.verified else None,
        )
        return

    membership = db.scalar(select(Membership).where(Membership.agent_id == agent_profile.id))
    status = "Complete" if membership is not None else "Not Started"
    _set_step_status(db, agent_profile.id, MEMBERSHIP_TERMS_STEP_TITLE, status, actor_user_id=actor_user_id)


def _sync_final_assessment_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    final_assessment = db.scalar(
        select(TrainingModule)
        .where(
            TrainingModule.training_track == "Onboarding",
            TrainingModule.published_status == "Published",
            func.lower(TrainingModule.title).like("%final assessment%"),
        )
        .order_by(TrainingModule.id)
        .limit(1)
    )
    if final_assessment is None:
        _set_step_status(db, agent_profile.id, FINAL_ASSESSMENT_STEP_TITLE, "Not Started")
        return

    progress = db.scalar(
        select(AgentTrainingProgress).where(
            AgentTrainingProgress.agent_id == agent_profile.id,
            AgentTrainingProgress.training_module_id == final_assessment.id,
        )
    )
    if progress is None:
        _set_step_status(db, agent_profile.id, FINAL_ASSESSMENT_STEP_TITLE, "Not Started")
        return

    if progress.progress_status == "Failed" or progress.passed is False:
        _set_step_status(db, agent_profile.id, FINAL_ASSESSMENT_STEP_TITLE, "Rejected", actor_user_id=actor_user_id)
        return

    if progress.progress_status == "Complete" and (not final_assessment.quiz_required or progress.passed is True):
        _set_step_status(
            db,
            agent_profile.id,
            FINAL_ASSESSMENT_STEP_TITLE,
            "Complete",
            actor_user_id=actor_user_id,
            completed_date=progress.completed_date,
        )
        return

    status = "In Progress" if progress.progress_status == "In Progress" else "Not Started"
    _set_step_status(db, agent_profile.id, FINAL_ASSESSMENT_STEP_TITLE, status, actor_user_id=actor_user_id)


def _sync_admin_final_approval_step(db: Session, agent_profile: AgentProfile, actor_user_id: int | None) -> None:
    if agent_profile.status in APPROVED_AGENT_STATUSES:
        _set_step_status(
            db,
            agent_profile.id,
            ADMIN_FINAL_APPROVAL_STEP_TITLE,
            "Complete",
            actor_user_id=actor_user_id,
            approved_by=actor_user_id,
        )
        return

    _set_step_status(db, agent_profile.id, ADMIN_FINAL_APPROVAL_STEP_TITLE, "Not Started")


def _set_step_status(
    db: Session,
    agent_id: int,
    step_title: str,
    status: str,
    *,
    actor_user_id: int | None = None,
    completed_date: date | None = None,
    evidence_file_or_link: str | None = None,
    approved_by: int | None = None,
    approved_date: date | None = None,
) -> None:
    progress = _get_or_create_progress(db, agent_id, step_title)
    if progress is None:
        return

    today = date.today()
    progress.completion_status = status
    if evidence_file_or_link is not None:
        progress.evidence_file_or_link = evidence_file_or_link

    if status == "Complete":
        progress.completed_date = progress.completed_date or completed_date or today
        progress.completed_by = progress.completed_by or actor_user_id
        if approved_by is not None:
            progress.approved_by = approved_by
        if approved_date is not None:
            progress.approved_date = approved_date
    else:
        progress.completed_date = None
        progress.completed_by = None
        if status in {"Not Started", "In Progress", "Rejected"}:
            progress.approved_by = None
            progress.approved_date = None


def _get_or_create_progress(db: Session, agent_id: int, step_title: str) -> AgentOnboardingProgress | None:
    step = db.scalar(
        select(OnboardingStep)
        .where(func.lower(OnboardingStep.title) == step_title.lower())
        .limit(1)
    )
    if step is None:
        return None

    progress = db.scalar(
        select(AgentOnboardingProgress).where(
            AgentOnboardingProgress.agent_id == agent_id,
            AgentOnboardingProgress.step_id == step.id,
        )
    )
    if progress is None:
        progress = AgentOnboardingProgress(agent_id=agent_id, step_id=step.id)
        db.add(progress)
        db.flush()
    return progress


def _latest_document(db: Session, agent_id: int, document_type: str) -> Document | None:
    return db.scalar(
        select(Document)
        .where(Document.agent_id == agent_id, Document.document_type == document_type)
        .order_by(Document.updated_at.desc(), Document.id.desc())
        .limit(1)
    )


def _all_fields_present(agent_profile: AgentProfile, field_names: tuple[str, ...]) -> bool:
    return all(_text_present(getattr(agent_profile, field_name, None)) for field_name in field_names)


def _text_present(value: object) -> bool:
    return value is not None and str(value).strip() != ""
