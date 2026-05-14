from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.agents import is_admin_user
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services.organizations import (
    can_manage_all_organizations,
    ensure_default_organization,
    slugify_organization_name,
)


router = APIRouter(prefix="/organizations", tags=["Organizations"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view organisations.",
        )


def require_super_admin(current_user: User) -> None:
    if not can_manage_all_organizations(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can manage organisations.",
        )


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Organization]:
    require_admin_user(current_user)
    ensure_default_organization(db)

    if can_manage_all_organizations(current_user):
        return list(db.scalars(select(Organization).order_by(Organization.name)))

    if current_user.organization_id is None:
        return []

    organization = db.get(Organization, current_user.organization_id)
    return [organization] if organization is not None else []


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Organization:
    require_super_admin(current_user)
    organization = Organization(
        name=request.name,
        slug=request.slug or slugify_organization_name(request.name),
        status=request.status,
        contact_email=request.contact_email,
        notes=request.notes,
    )
    db.add(organization)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation could not be created because the name or slug is already used.",
        ) from None

    db.refresh(organization)
    return organization


@router.put("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: int,
    request: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Organization:
    require_super_admin(current_user)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    update_data = request.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] is None:
        update_data["slug"] = slugify_organization_name(organization.name)

    for field, value in update_data.items():
        setattr(organization, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation could not be updated because the name or slug is already used.",
        ) from None

    db.refresh(organization)
    return organization
