from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.agent_statuses import is_onboarding_tracking_exempt
from app.core.resources import SOCIAL_MEDIA_POLICY_TYPE
from app.models.agent_profile import AgentProfile
from app.models.compliance import CompliancePolicy, PolicyAcceptance
from app.models.document import Document
from app.models.live_training import AttendanceLog, LiveTrainingSession
from app.models.membership import Membership
from app.models.onboarding import AgentOnboardingProgress, OnboardingStep
from app.models.training import AgentTrainingProgress, TrainingModule
from app.models.user import User
from app.services.audit import create_audit_log


APPROVED_AGENT_STATUSES = ("Approved to Trade", "Active Agent")
ADMIN_FINAL_APPROVAL_KEY = "admin_final_approval"
ADMIN_FINAL_APPROVAL_STEP_TITLE = "Admin final approval"
PASSING_ATTENDANCE_STATUSES = ("Attended", "Watched Recording")


def build_final_approval_status(db: Session, agent_profile: AgentProfile) -> dict:
    if is_onboarding_tracking_exempt(agent_profile.status):
        return {
            "agent_id": agent_profile.id,
            "agent_name": f"{agent_profile.first_name} {agent_profile.last_name}",
            "current_status": agent_profile.status,
            "ready_for_approval": False,
            "approved_to_trade": False,
            "tracking_exempt": True,
            "missing_requirements": [],
            "requirements": [
                _requirement(
                    "tracking_exempt",
                    "Onboarding and training tracking switched off",
                    True,
                    "This status is used for existing agents or head office/admin staff, so the portal does not chase onboarding or mandatory training.",
                )
            ],
        }

    requirements = [
        _membership_active(db, agent_profile.id),
        _payment_setup_complete(db, agent_profile.id),
        _contract_signed(db, agent_profile.id),
        _document_verified(db, agent_profile.id, "ID Document", "ID document verified"),
        _document_verified(db, agent_profile.id, "Proof of Address", "Proof of address verified"),
        _call_attended(db, agent_profile.id, "Welcome Call", "Welcome call attended"),
        _call_attended(db, agent_profile.id, "Compliance Call", "Compliance call attended"),
        _mandatory_training_complete(db, agent_profile.id),
        _final_assessment_passed(db, agent_profile.id),
        _social_media_policy_accepted(db, agent_profile.id),
        _admin_final_approval_complete(db, agent_profile),
    ]
    blocking_missing = [
        requirement["label"]
        for requirement in requirements
        if not requirement["complete"] and requirement["key"] != ADMIN_FINAL_APPROVAL_KEY
    ]
    approved_to_trade = agent_profile.status in APPROVED_AGENT_STATUSES

    return {
        "agent_id": agent_profile.id,
        "agent_name": f"{agent_profile.first_name} {agent_profile.last_name}",
        "current_status": agent_profile.status,
        "ready_for_approval": not blocking_missing and not approved_to_trade,
        "approved_to_trade": approved_to_trade,
        "tracking_exempt": False,
        "missing_requirements": blocking_missing,
        "requirements": requirements,
    }


def approve_agent_to_trade(db: Session, agent_profile: AgentProfile, admin_user: User) -> dict:
    previous_status = agent_profile.status
    _complete_admin_final_approval(db, agent_profile.id, admin_user.id)
    agent_profile.status = "Approved to Trade"

    create_audit_log(
        db,
        action_type="Agent approved to trade",
        description=f"{agent_profile.first_name} {agent_profile.last_name} was approved to trade.",
        created_by=admin_user.id,
        user_id=agent_profile.user_id,
        agent_id=agent_profile.id,
        previous_value=previous_status,
        new_value="Approved to Trade",
    )
    db.commit()
    db.refresh(agent_profile)
    return build_final_approval_status(db, agent_profile)


def _requirement(key: str, label: str, complete: bool, detail: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "complete": complete,
        "detail": detail,
    }


def _membership_active(db: Session, agent_id: int) -> dict:
    membership = _get_membership(db, agent_id)
    complete = membership is not None and membership.membership_status == "Active"
    detail = "Membership status must be Active." if not complete else "Membership is active."
    return _requirement("membership_active", "Membership active", complete, detail)


def _payment_setup_complete(db: Session, agent_id: int) -> dict:
    membership = _get_membership(db, agent_id)
    complete = membership is not None and (
        membership.payment_status == "Paid"
        or bool(membership.payment_method)
        or bool(membership.stripe_subscription_id)
    )
    detail = "Payment must be marked paid or have a saved payment method." if not complete else "Payment setup is complete."
    return _requirement("payment_setup_complete", "Payment setup complete", complete, detail)


def _get_membership(db: Session, agent_id: int) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.agent_id == agent_id))


def _contract_signed(db: Session, agent_id: int) -> dict:
    document = _get_latest_document(db, agent_id, "Contractor Agreement")
    complete = document is not None and document.signed
    detail = "Contractor agreement must be signed." if not complete else "Contractor agreement is signed."
    return _requirement("contract_signed", "Contract signed", complete, detail)


def _document_verified(db: Session, agent_id: int, document_type: str, label: str) -> dict:
    document = _get_latest_document(db, agent_id, document_type)
    complete = document is not None and document.verified and document.status == "Verified"
    detail = f"{document_type} must be verified by admin." if not complete else f"{document_type} is verified."
    return _requirement(_key_from_label(label), label, complete, detail)


def _get_latest_document(db: Session, agent_id: int, document_type: str) -> Document | None:
    return db.scalar(
        select(Document)
        .where(Document.agent_id == agent_id, Document.document_type == document_type)
        .order_by(Document.updated_at.desc())
        .limit(1)
    )


def _call_attended(db: Session, agent_id: int, session_type: str, label: str) -> dict:
    attendance = db.scalar(
        select(AttendanceLog)
        .join(LiveTrainingSession)
        .where(
            AttendanceLog.agent_id == agent_id,
            LiveTrainingSession.session_type == session_type,
            or_(
                AttendanceLog.attendance_status.in_(PASSING_ATTENDANCE_STATUSES),
                AttendanceLog.watched_recording.is_(True),
            ),
        )
        .limit(1)
    )
    complete = attendance is not None
    detail = f"{session_type} must be attended or completed by recording." if not complete else f"{session_type} is complete."
    return _requirement(_key_from_label(label), label, complete, detail)


def _mandatory_training_complete(db: Session, agent_id: int) -> dict:
    modules = _mandatory_onboarding_modules(db)
    if not modules:
        return _requirement(
            "mandatory_training_complete",
            "Mandatory training complete",
            False,
            "Mandatory onboarding modules need to be created first.",
        )

    progress_by_module = _training_progress_by_module(db, agent_id)
    incomplete_modules = [
        module.title
        for module in modules
        if not _training_module_complete(module, progress_by_module.get(module.id))
    ]
    complete = not incomplete_modules
    detail = "All mandatory onboarding modules are complete." if complete else "Missing: " + ", ".join(incomplete_modules)
    return _requirement("mandatory_training_complete", "Mandatory training complete", complete, detail)


def _final_assessment_passed(db: Session, agent_id: int) -> dict:
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
        return _requirement(
            "final_assessment_passed",
            "Final assessment passed",
            False,
            "The Final Assessment training module needs to be created first.",
        )

    progress = _training_progress_by_module(db, agent_id).get(final_assessment.id)
    complete = _training_module_complete(final_assessment, progress) and progress is not None and progress.passed is True
    detail = "Final assessment has been passed." if complete else "Final assessment must be completed with a passing result."
    return _requirement("final_assessment_passed", "Final assessment passed", complete, detail)


def _mandatory_onboarding_modules(db: Session) -> list[TrainingModule]:
    return list(
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


def _training_progress_by_module(db: Session, agent_id: int) -> dict[int, AgentTrainingProgress]:
    progress_rows = db.scalars(
        select(AgentTrainingProgress).where(AgentTrainingProgress.agent_id == agent_id)
    )
    return {progress.training_module_id: progress for progress in progress_rows}


def _training_module_complete(module: TrainingModule, progress: AgentTrainingProgress | None) -> bool:
    if progress is None or progress.progress_status != "Complete":
        return False
    if module.quiz_required and progress.passed is not True:
        return False
    return True


def _social_media_policy_accepted(db: Session, agent_id: int) -> dict:
    policy = db.scalar(
        select(CompliancePolicy)
        .where(
            CompliancePolicy.policy_type == SOCIAL_MEDIA_POLICY_TYPE,
            CompliancePolicy.requires_acceptance.is_(True),
            CompliancePolicy.published_status == "Published",
        )
        .order_by(CompliancePolicy.updated_at.desc())
        .limit(1)
    )
    if policy is None:
        return _requirement(
            "social_media_policy_accepted",
            "Social media policy accepted",
            False,
            "A published social media policy needs to exist first.",
        )

    acceptance = db.scalar(
        select(PolicyAcceptance)
        .where(
            PolicyAcceptance.agent_id == agent_id,
            PolicyAcceptance.policy_id == policy.id,
            PolicyAcceptance.policy_version == policy.version,
        )
        .limit(1)
    )
    complete = acceptance is not None
    detail = "Current social media policy is accepted." if complete else "Current social media policy must be accepted."
    return _requirement("social_media_policy_accepted", "Social media policy accepted", complete, detail)


def _admin_final_approval_complete(db: Session, agent_profile: AgentProfile) -> dict:
    progress = _get_admin_final_approval_progress(db, agent_profile.id)
    complete = agent_profile.status in APPROVED_AGENT_STATUSES or (
        progress is not None
        and progress.completion_status == "Complete"
        and progress.approved_by is not None
    )
    detail = "Admin final approval is complete." if complete else "Ready once an admin presses Approve to Trade."
    return _requirement(ADMIN_FINAL_APPROVAL_KEY, "Admin final approval completed", complete, detail)


def _complete_admin_final_approval(db: Session, agent_id: int, admin_user_id: int) -> None:
    step = db.scalar(
        select(OnboardingStep)
        .where(func.lower(OnboardingStep.title) == ADMIN_FINAL_APPROVAL_STEP_TITLE.lower())
        .limit(1)
    )
    if step is None:
        return

    progress = _get_admin_final_approval_progress(db, agent_id)
    if progress is None:
        progress = AgentOnboardingProgress(agent_id=agent_id, step_id=step.id)
        db.add(progress)

    today = date.today()
    progress.completion_status = "Complete"
    progress.completed_date = progress.completed_date or today
    progress.completed_by = progress.completed_by or admin_user_id
    progress.approved_by = admin_user_id
    progress.approved_date = today


def _get_admin_final_approval_progress(db: Session, agent_id: int) -> AgentOnboardingProgress | None:
    return db.scalar(
        select(AgentOnboardingProgress)
        .join(OnboardingStep)
        .where(
            AgentOnboardingProgress.agent_id == agent_id,
            func.lower(OnboardingStep.title) == ADMIN_FINAL_APPROVAL_STEP_TITLE.lower(),
        )
        .limit(1)
    )


def _key_from_label(label: str) -> str:
    return label.lower().replace(" ", "_")
