from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.agent_statuses import DEFAULT_AGENT_STATUS
from app.core.roles import ADMIN_ROLE_NAMES
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.agent import (
    AgentCsvImportRequest,
    AgentCsvImportResponse,
    AgentProfileCreate,
    AgentProfileRead,
    AgentProfileUpdate,
    FinalApprovalStatusRead,
)
from app.services.agent_ids import generate_next_agent_id
from app.services.agent_import import import_agents_from_csv
from app.services.final_approval import approve_agent_to_trade, build_final_approval_status


router = APIRouter(prefix="/agents", tags=["Agents"])


def is_admin_user(user: User) -> bool:
    return user.role.name in ADMIN_ROLE_NAMES


def get_agent_or_404(db: Session, agent_profile_id: int) -> AgentProfile:
    agent_profile = db.get(AgentProfile, agent_profile_id)
    if agent_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found.",
        )
    return agent_profile


def check_agent_access(agent_profile: AgentProfile, current_user: User) -> None:
    if is_admin_user(current_user):
        return
    if agent_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own agent profile.",
        )


def get_existing_profile_for_user(db: Session, user_id: int) -> AgentProfile | None:
    return db.scalar(select(AgentProfile).where(AgentProfile.user_id == user_id))


@router.post("", response_model=AgentProfileRead, status_code=status.HTTP_201_CREATED)
def create_agent_profile(
    request: AgentProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentProfile:
    admin_user = is_admin_user(current_user)
    target_user_id = request.user_id or current_user.id

    if not admin_user and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create your own agent profile.",
        )

    if not admin_user and request.status is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can set an agent status.",
        )

    target_user = db.get(User, target_user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked user account not found.",
        )

    if get_existing_profile_for_user(db, target_user_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user already has an agent profile.",
        )

    agent_profile = AgentProfile(
        user_id=target_user_id,
        agent_id=request.agent_id or generate_next_agent_id(db),
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        personal_email=request.personal_email or request.email,
        company_email=request.company_email,
        portal_access_enabled=request.portal_access_enabled if admin_user and request.portal_access_enabled is not None else True,
        phone=request.phone,
        business_name=request.business_name,
        status=request.status or DEFAULT_AGENT_STATUS,
        joining_date=request.joining_date,
        address=request.address,
        postcode=request.postcode,
        commission_bank_name=request.commission_bank_name,
        commission_account_name=request.commission_account_name,
        commission_sort_code=request.commission_sort_code,
        commission_account_number=request.commission_account_number,
    )
    db.add(agent_profile)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent profile could not be created because it conflicts with an existing record.",
        ) from None

    db.refresh(agent_profile)
    return agent_profile


@router.get("", response_model=list[AgentProfileRead])
def list_agent_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AgentProfile]:
    if is_admin_user(current_user):
        return list(db.scalars(select(AgentProfile).order_by(AgentProfile.id)))

    own_profile = get_existing_profile_for_user(db, current_user.id)
    return [own_profile] if own_profile is not None else []


@router.post("/import/csv", response_model=AgentCsvImportResponse)
def import_agent_csv(
    request: AgentCsvImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can import agents.",
        )

    return import_agents_from_csv(db, request, current_user=current_user)


@router.get("/{agent_profile_id}", response_model=AgentProfileRead)
def get_agent_profile(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentProfile:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return agent_profile


@router.get("/{agent_profile_id}/final-approval", response_model=FinalApprovalStatusRead)
def get_agent_final_approval_status(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return build_final_approval_status(db, agent_profile)


@router.post("/{agent_profile_id}/approve-to-trade", response_model=FinalApprovalStatusRead)
def approve_agent_final_trade_status(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve an agent to trade.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    approval_status = build_final_approval_status(db, agent_profile)
    if approval_status["approved_to_trade"]:
        return approval_status

    if not approval_status["ready_for_approval"]:
        missing = ", ".join(approval_status["missing_requirements"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This agent is not ready for final approval yet. Missing: {missing}",
        )

    return approve_agent_to_trade(db, agent_profile, current_user)


@router.put("/{agent_profile_id}", response_model=AgentProfileRead)
def update_agent_profile(
    agent_profile_id: int,
    request: AgentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentProfile:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    update_data = request.model_dump(exclude_unset=True)
    for required_field in ("first_name", "last_name", "email"):
        if required_field in update_data and update_data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{required_field} cannot be blank.",
            )

    admin_user = is_admin_user(current_user)

    if not admin_user and "status" in update_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update an agent status.",
        )

    if not admin_user and "portal_access_enabled" in update_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update portal access.",
        )

    for field, value in update_data.items():
        setattr(agent_profile, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent profile could not be updated because it conflicts with an existing record.",
        ) from None

    db.refresh(agent_profile)
    return agent_profile
