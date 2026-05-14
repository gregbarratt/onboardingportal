from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.onboarding_statuses import DEFAULT_ONBOARDING_STATUS
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.onboarding import AgentOnboardingProgress, OnboardingStep
from app.models.user import User
from app.schemas.onboarding import (
    AdminOnboardingSummaryRead,
    AgentOnboardingProgressRead,
    AgentOnboardingProgressUpdate,
    OnboardingApprovalRequest,
    OnboardingStepCreate,
    OnboardingStepRead,
    OnboardingStepUpdate,
)
from app.services.organizations import can_manage_all_organizations


router = APIRouter(tags=["Onboarding"])


def get_step_or_404(db: Session, step_id: int) -> OnboardingStep:
    step = db.get(OnboardingStep, step_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding step not found.",
        )
    return step


def get_progress_or_404(db: Session, progress_id: int) -> AgentOnboardingProgress:
    progress = db.scalar(
        select(AgentOnboardingProgress)
        .options(selectinload(AgentOnboardingProgress.step))
        .where(AgentOnboardingProgress.id == progress_id)
    )
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding progress item not found.",
        )
    return progress


def ensure_agent_onboarding_progress(db: Session, agent_profile: AgentProfile) -> None:
    steps = list(db.scalars(select(OnboardingStep).order_by(OnboardingStep.sort_order)))
    existing_step_ids = set(
        db.scalars(
            select(AgentOnboardingProgress.step_id)
            .where(AgentOnboardingProgress.agent_id == agent_profile.id)
        )
    )

    for step in steps:
        if step.id not in existing_step_ids:
            db.add(
                AgentOnboardingProgress(
                    agent_id=agent_profile.id,
                    step_id=step.id,
                    completion_status=DEFAULT_ONBOARDING_STATUS,
                )
            )
    db.commit()


@router.get("/onboarding/steps", response_model=list[OnboardingStepRead])
def list_onboarding_steps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OnboardingStep]:
    return list(db.scalars(select(OnboardingStep).order_by(OnboardingStep.sort_order)))


@router.post("/onboarding/steps", response_model=OnboardingStepRead, status_code=status.HTTP_201_CREATED)
def create_onboarding_step(
    request: OnboardingStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OnboardingStep:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create onboarding steps.",
        )

    step = OnboardingStep(
        title=request.title,
        description=request.description,
        required=request.required,
        approval_required=request.approval_required,
        sort_order=request.sort_order,
    )
    db.add(step)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding step could not be created because it conflicts with an existing record.",
        ) from None

    db.refresh(step)
    return step


@router.put("/onboarding/steps/{step_id}", response_model=OnboardingStepRead)
def update_onboarding_step(
    step_id: int,
    request: OnboardingStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OnboardingStep:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update onboarding steps.",
        )

    step = get_step_or_404(db, step_id)
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding step could not be updated because it conflicts with an existing record.",
        ) from None

    db.refresh(step)
    return step


@router.get("/admin/onboarding-summary", response_model=list[AdminOnboardingSummaryRead])
def list_admin_onboarding_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view onboarding summaries.",
        )

    agent_query = select(AgentProfile).order_by(AgentProfile.id)
    if not can_manage_all_organizations(current_user):
        if current_user.organization_id is None:
            return []
        agent_query = agent_query.where(AgentProfile.organization_id == current_user.organization_id)

    agents = list(db.scalars(agent_query))
    agent_ids = [agent.id for agent in agents]
    total_steps = db.scalar(select(func.count(OnboardingStep.id))) or 0
    counts_by_agent: dict[int, dict[str, int]] = {
        agent.id: {"complete_steps": 0, "awaiting_review": 0}
        for agent in agents
    }

    if agent_ids:
        rows = db.execute(
            select(
                AgentOnboardingProgress.agent_id,
                AgentOnboardingProgress.completion_status,
                func.count(AgentOnboardingProgress.id),
            )
            .where(AgentOnboardingProgress.agent_id.in_(agent_ids))
            .group_by(AgentOnboardingProgress.agent_id, AgentOnboardingProgress.completion_status)
        )
        for agent_id, completion_status, count in rows:
            if completion_status == "Complete":
                counts_by_agent[agent_id]["complete_steps"] = count
            elif completion_status == "Awaiting Review":
                counts_by_agent[agent_id]["awaiting_review"] = count

    return [
        {
            "id": agent.id,
            "agent_id": agent.agent_id,
            "first_name": agent.first_name,
            "last_name": agent.last_name,
            "email": agent.email,
            "business_name": agent.business_name,
            "status": agent.status,
            "total_steps": total_steps,
            "complete_steps": counts_by_agent[agent.id]["complete_steps"],
            "awaiting_review": counts_by_agent[agent.id]["awaiting_review"],
        }
        for agent in agents
    ]


@router.get("/agents/{agent_profile_id}/onboarding", response_model=list[AgentOnboardingProgressRead])
def list_agent_onboarding(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AgentOnboardingProgress]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    ensure_agent_onboarding_progress(db, agent_profile)
    return list(
        db.scalars(
            select(AgentOnboardingProgress)
            .options(selectinload(AgentOnboardingProgress.step))
            .where(AgentOnboardingProgress.agent_id == agent_profile.id)
            .join(OnboardingStep)
            .order_by(OnboardingStep.sort_order)
        )
    )


@router.put("/agents/{agent_profile_id}/onboarding/{progress_id}", response_model=AgentOnboardingProgressRead)
def update_agent_onboarding_progress(
    agent_profile_id: int,
    progress_id: int,
    request: AgentOnboardingProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentOnboardingProgress:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    progress = get_progress_or_404(db, progress_id)

    if progress.agent_id != agent_profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding progress item not found for this agent.",
        )

    admin_user = is_admin_user(current_user)
    update_data = request.model_dump(exclude_unset=True)

    admin_only_fields = {"due_date", "completed_date", "completed_by", "admin_notes"}
    if not admin_user and admin_only_fields.intersection(update_data):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update admin onboarding fields.",
        )

    if not admin_user and update_data.get("completion_status") == "Complete" and progress.step.approval_required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This step needs admin approval before it can be completed.",
        )

    if "completion_status" in update_data and update_data["completion_status"] == "Complete":
        if update_data.get("completed_date") is None and progress.completed_date is None:
            progress.completed_date = date.today()
        if update_data.get("completed_by") is None and progress.completed_by is None:
            progress.completed_by = current_user.id

    for field, value in update_data.items():
        setattr(progress, field, value)

    db.commit()
    db.refresh(progress)
    return progress


@router.post("/agents/{agent_profile_id}/onboarding/{progress_id}/approve", response_model=AgentOnboardingProgressRead)
def approve_agent_onboarding_progress(
    agent_profile_id: int,
    progress_id: int,
    request: OnboardingApprovalRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentOnboardingProgress:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve onboarding items.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    progress = get_progress_or_404(db, progress_id)
    if progress.agent_id != agent_profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding progress item not found for this agent.",
        )

    progress.completion_status = "Complete"
    progress.completed_date = progress.completed_date or date.today()
    progress.completed_by = progress.completed_by or current_user.id
    progress.approved_by = current_user.id
    progress.approved_date = date.today()
    if request is not None and request.admin_notes is not None:
        progress.admin_notes = request.admin_notes

    db.commit()
    db.refresh(progress)
    return progress
