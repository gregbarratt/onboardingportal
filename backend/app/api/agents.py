import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.agent_statuses import DEFAULT_AGENT_STATUS
from app.core.roles import ADMIN_ROLE_NAMES, DEFAULT_ROLES
from app.core.payment_statuses import DEFAULT_MEMBERSHIP_PAYMENT_STATUS
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.role import Role
from app.models.user import User
from app.schemas.agent import (
    AgentCsvImportRequest,
    AgentCsvImportResponse,
    ManualAgentCreate,
    ManualAgentCreateResponse,
    AgentProfileCreate,
    AgentProfileRead,
    AgentStripeSyncBatchRequest,
    AgentStripeSyncBatchResponse,
    AgentProfileUpdate,
    FinalApprovalStatusRead,
)
from app.services.agent_ids import generate_next_agent_id
from app.services.agent_import import AgentImportRowError, import_agents_from_csv, sync_imported_agent_stripe
from app.services.audit import create_audit_log
from app.services.email import send_password_reset_email
from app.services.final_approval import approve_agent_to_trade, build_final_approval_status
from app.services.organizations import (
    can_manage_all_organizations,
    organization_id_for_new_record,
    user_can_access_organization,
)
from app.services.onboarding_sync import sync_agent_onboarding_progress
from app.services.password_reset import build_password_reset_url, create_password_reset_token
from app.services.passwords import hash_password


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
    if is_admin_user(current_user) and user_can_access_organization(current_user, agent_profile.organization_id):
        return
    if is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access agents in your organisation.",
        )
    if agent_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own agent profile.",
        )


def get_existing_profile_for_user(db: Session, user_id: int) -> AgentProfile | None:
    return db.scalar(select(AgentProfile).where(AgentProfile.user_id == user_id))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def ensure_agent_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.name == "Agent"))
    if role is not None:
        return role

    role_descriptions = dict(DEFAULT_ROLES)
    role = Role(name="Agent", description=role_descriptions.get("Agent"))
    db.add(role)
    db.flush()
    return role


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

    if not can_manage_all_organizations(current_user) and request.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can choose another organisation.",
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

    organization_id = organization_id_for_new_record(db, current_user, request.organization_id)
    if target_user.organization_id is not None and not user_can_access_organization(current_user, target_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create profiles for users in your organisation.",
        )
    target_user.organization_id = organization_id

    agent_profile = AgentProfile(
        user_id=target_user_id,
        organization_id=organization_id,
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
    db.flush()
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)

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


@router.post("/manual", response_model=ManualAgentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_manual_agent(
    request: ManualAgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manually add agents.",
        )

    if not can_manage_all_organizations(current_user) and request.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can choose another organisation.",
        )

    if get_user_by_email(db, request.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A portal user already exists with this login email.",
        )

    organization_id = organization_id_for_new_record(db, current_user, request.organization_id)
    agent_role = ensure_agent_role(db)
    password_reset_url: str | None = None
    password_reset_email_sent = False
    password_reset_error: str | None = None

    user = User(
        email=request.email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        role_id=agent_role.id,
        organization_id=organization_id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    agent_profile = AgentProfile(
        user_id=user.id,
        organization_id=organization_id,
        agent_id=request.agent_id or generate_next_agent_id(db),
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        personal_email=request.personal_email or request.email,
        company_email=request.company_email,
        portal_access_enabled=request.portal_access_enabled,
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
    db.flush()

    membership = Membership(
        agent_id=agent_profile.id,
        membership_type="Standard",
        membership_status="Invited",
        payment_status=DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
        payment_method="Manual",
        failed_payment_count=0,
    )
    db.add(membership)
    db.flush()
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)

    create_audit_log(
        db,
        action_type="Account created",
        description=f"Admin manually created agent account for {agent_profile.first_name} {agent_profile.last_name}.",
        created_by=current_user.id,
        user_id=user.id,
        agent_id=agent_profile.id,
    )

    if request.portal_access_enabled and request.send_password_reset_email:
        _, raw_token = create_password_reset_token(db, user)
        password_reset_url = build_password_reset_url(raw_token)
        create_audit_log(
            db,
            action_type="Password reset requested",
            description="Password setup email created for manually added agent.",
            created_by=current_user.id,
            user_id=user.id,
            agent_id=agent_profile.id,
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent could not be created because it conflicts with an existing record.",
        ) from None

    db.refresh(agent_profile)

    if password_reset_url:
        try:
            password_reset_email_sent = send_password_reset_email(
                to_email=user.email,
                reset_url=password_reset_url,
            )
        except Exception as exc:
            password_reset_error = str(exc)

    message = "Agent created."
    if password_reset_email_sent:
        message = "Agent created and password setup email sent."
    elif password_reset_url and password_reset_error:
        message = "Agent created, but the password setup email could not be sent."

    return {
        "agent": agent_profile,
        "password_reset_email_sent": password_reset_email_sent,
        "password_reset_error": password_reset_error,
        "message": message,
    }


@router.get("", response_model=list[AgentProfileRead])
def list_agent_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AgentProfile]:
    if is_admin_user(current_user):
        query = select(AgentProfile).order_by(AgentProfile.id)
        if not can_manage_all_organizations(current_user):
            if current_user.organization_id is None:
                return []
            query = query.where(AgentProfile.organization_id == current_user.organization_id)
        return list(db.scalars(query))

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

    result = import_agents_from_csv(db, request, current_user=current_user)
    stripe_sync_agent_ids = result.pop("_stripe_sync_agent_ids", [])
    result["stripe_sync_queued"] = len(stripe_sync_agent_ids)
    result["stripe_sync_agent_ids"] = stripe_sync_agent_ids
    return result


@router.post("/stripe/import-sync-batch", response_model=AgentStripeSyncBatchResponse)
def sync_imported_agents_stripe_batch(
    request: AgentStripeSyncBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can sync Stripe data.",
        )

    query = (
        select(AgentProfile)
        .join(Membership, Membership.agent_id == AgentProfile.id)
        .where(Membership.stripe_customer_id.is_not(None))
        .where(Membership.stripe_customer_id != "")
    )
    if request.agent_profile_ids:
        query = query.where(AgentProfile.id.in_(request.agent_profile_ids))
    if request.after_agent_id is not None:
        query = query.where(AgentProfile.id > request.after_agent_id)
    if not can_manage_all_organizations(current_user):
        if current_user.organization_id is None:
            return empty_stripe_batch_response(done=True)
        query = query.where(AgentProfile.organization_id == current_user.organization_id)

    agents = list(db.scalars(query.order_by(AgentProfile.id).limit(request.limit + 1)))
    selected_agents = agents[: request.limit]
    has_more = len(agents) > request.limit

    result = empty_stripe_batch_response(done=not has_more)
    result["processed"] = len(selected_agents)
    result["next_after_agent_id"] = selected_agents[-1].id if selected_agents else request.after_agent_id

    for agent_profile in selected_agents:
        try:
            sync_result = sync_imported_agent_stripe(
                db,
                agent_profile=agent_profile,
                current_user=current_user,
            )
            db.commit()
            result["stripe_synced"] += sync_result["stripe_synced"]
            result["stripe_profiles_synced"] += sync_result["stripe_profiles_synced"]
            result["stripe_profile_fields_synced"] += sync_result["stripe_profile_fields_synced"]
            result["stripe_invoices_synced"] += sync_result["stripe_invoices_synced"]
            result["stripe_subscriptions_synced"] += sync_result["stripe_subscriptions_synced"]
        except AgentImportRowError as exc:
            db.rollback()
            result["stripe_sync_failed"] += 1
            result["errors"].append(
                {
                    "agent_id": agent_profile.id,
                    "identifier": agent_profile.agent_id,
                    "message": str(exc),
                }
            )

    return result


def empty_stripe_batch_response(*, done: bool) -> dict:
    return {
        "processed": 0,
        "stripe_synced": 0,
        "stripe_sync_failed": 0,
        "stripe_profiles_synced": 0,
        "stripe_profile_fields_synced": 0,
        "stripe_invoices_synced": 0,
        "stripe_subscriptions_synced": 0,
        "next_after_agent_id": None,
        "has_more": not done,
        "done": done,
        "errors": [],
    }


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
    check_agent_access(agent_profile, current_user)
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

    if "organization_id" in update_data:
        if not can_manage_all_organizations(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can move an agent to another organisation.",
            )
        if agent_profile.user is not None:
            agent_profile.user.organization_id = update_data["organization_id"]

    for field, value in update_data.items():
        setattr(agent_profile, field, value)
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)

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
