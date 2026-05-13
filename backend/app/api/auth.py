from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_active_user
from app.core.roles import DEFAULT_ROLES
from app.db.session import get_db
from app.models.role import Role
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterUserRequest, TokenResponse, UserRead
from app.services.passwords import hash_password, verify_password
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
