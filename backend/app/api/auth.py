from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_active_user
from app.core.roles import DEFAULT_ROLES
from app.db.session import get_db
from app.models.role import Role
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.user import User
from app.schemas.auth import (
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    LoginRequest,
    RegisterUserRequest,
    TokenResponse,
    UserRead,
)
from app.services.agent_ids import generate_next_agent_id
from app.services.audit import create_audit_log
from app.services.passwords import hash_password, verify_password
from app.services.stripe import (
    StripeIntegrationError,
    create_agent_registration_checkout_session,
    create_stripe_customer,
    ensure_agent_registration_checkout_ready,
)
from app.services.tokens import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


def ensure_default_roles(db: Session) -> dict[str, Role]:
    role_names = [name for name, _ in DEFAULT_ROLES]
    existing_roles = {
        role.name: role
        for role in db.scalars(select(Role).where(Role.name.in_(role_names)))
    }

    for name, description in DEFAULT_ROLES:
        if name not in existing_roles:
            role = Role(name=name, description=description)
            db.add(role)
            existing_roles[name] = role

    db.flush()
    return existing_roles


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.role))
        .where(User.email == email)
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    request: RegisterUserRequest,
    db: Session = Depends(get_db),
) -> User:
    if get_user_by_email(db, request.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    roles = ensure_default_roles(db)
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        role=roles["Agent"],
    )
    db.add(user)
    db.flush()
    user_id = user.id
    db.commit()

    created_user = get_user_by_id(db, user_id)
    if created_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User was created but could not be loaded.",
        )
    return created_user


@router.post("/register-agent", response_model=AgentRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_agent_and_start_payment(
    request: AgentRegistrationRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        ensure_agent_registration_checkout_ready()
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if get_user_by_email(db, request.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A portal account already exists for this email address.",
        )

    roles = ensure_default_roles(db)
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        role=roles["Agent"],
    )
    db.add(user)
    db.flush()

    agent_profile = AgentProfile(
        user_id=user.id,
        agent_id=generate_next_agent_id(db),
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        personal_email=request.email,
        phone=request.phone,
        business_name=request.business_name,
        status="Payment Pending",
        address=request.address,
        postcode=request.postcode,
        portal_access_enabled=False,
    )
    db.add(agent_profile)
    db.flush()

    membership = Membership(
        agent_id=agent_profile.id,
        membership_type="Standard",
        membership_status="Payment Pending",
        payment_status="Pending",
        payment_method="Stripe",
        failed_payment_count=0,
    )
    db.add(membership)
    db.flush()

    try:
        customer = create_stripe_customer(agent_profile)
        stripe_customer_id = customer.get("id")
        if not stripe_customer_id:
            raise StripeIntegrationError("Stripe did not return a customer ID.")

        membership.stripe_customer_id = stripe_customer_id
        checkout_session = create_agent_registration_checkout_session(
            agent_profile=agent_profile,
            membership=membership,
        )
        checkout_url = checkout_session.get("url")
        checkout_session_id = checkout_session.get("id")
        if not checkout_url or not checkout_session_id:
            raise StripeIntegrationError("Stripe did not return a checkout link.")

        create_audit_log(
            db,
            action_type="Account created",
            description=f"Agent registration started for {agent_profile.first_name} {agent_profile.last_name}.",
            created_by=None,
            user_id=user.id,
            agent_id=agent_profile.id,
        )
        create_audit_log(
            db,
            action_type="Payment setup completed",
            description="Stripe checkout session created for agent registration.",
            previous_value=None,
            new_value=stripe_customer_id,
            created_by=None,
            user_id=user.id,
            agent_id=agent_profile.id,
        )
        db.commit()
    except StripeIntegrationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration could not be completed because it conflicts with an existing record.",
        ) from None

    return {
        "agent_profile_id": agent_profile.id,
        "checkout_session_id": checkout_session_id,
        "checkout_url": checkout_url,
        "message": "Registration created. Continue to Stripe to complete payment.",
    }


@router.post("/login", response_model=TokenResponse)
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = get_user_by_email(db, request.email)
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive.",
        )

    if user.role.name == "Agent":
        agent_profile = db.scalar(select(AgentProfile).where(AgentProfile.user_id == user.id))
        if agent_profile is not None and not agent_profile.portal_access_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portal access is not enabled for this agent yet.",
            )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.name},
    )
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user
