from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User


DEFAULT_ORGANIZATION_NAME = "One Travel Club"
DEFAULT_ORGANIZATION_SLUG = "one-travel-club"
SUPER_ADMIN_ROLE = "Super Admin"


def slugify_organization_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or DEFAULT_ORGANIZATION_SLUG


def ensure_default_organization(db: Session) -> Organization:
    organization = db.scalar(select(Organization).where(Organization.slug == DEFAULT_ORGANIZATION_SLUG))
    if organization is None:
        organization = Organization(
            name=DEFAULT_ORGANIZATION_NAME,
            slug=DEFAULT_ORGANIZATION_SLUG,
            status="Active",
        )
        db.add(organization)
        db.flush()
    return organization


def can_manage_all_organizations(user: User) -> bool:
    return user.role.name == SUPER_ADMIN_ROLE


def organization_id_for_new_record(db: Session, current_user: User, requested_organization_id: int | None = None) -> int:
    if can_manage_all_organizations(current_user) and requested_organization_id is not None:
        return requested_organization_id

    if current_user.organization_id is not None:
        return current_user.organization_id

    return ensure_default_organization(db).id


def user_can_access_organization(current_user: User, organization_id: int | None) -> bool:
    if can_manage_all_organizations(current_user):
        return True
    return organization_id is not None and organization_id == current_user.organization_id
