from __future__ import annotations

import base64
import csv
import io
import secrets
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.agent_statuses import AGENT_STATUSES, DEFAULT_AGENT_STATUS
from app.core.payment_statuses import (
    DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
    DEFAULT_MEMBERSHIP_STATUS,
    MEMBERSHIP_STATUSES,
    PAYMENT_STATUSES,
)
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.schemas.agent import AgentCsvImportRequest
from app.services.agent_ids import generate_next_agent_id
from app.services.audit import create_audit_log
from app.services.organizations import can_manage_all_organizations, ensure_default_organization
from app.services.passwords import hash_password
from app.services.stripe import (
    StripeIntegrationError,
    sync_stripe_cache_for_membership,
)


PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "personal_email",
    "company_email",
    "phone",
    "business_name",
    "status",
    "joining_date",
    "address",
    "postcode",
    "commission_bank_name",
    "commission_account_name",
    "commission_sort_code",
    "commission_account_number",
)


AGENT_STATUS_ALIASES = {
    "active": "Active Agent",
    "active agent": "Active Agent",
    "approved": "Approved to Trade",
    "approved to trade": "Approved to Trade",
    "awaiting approval": "Awaiting Final Approval",
    "awaiting final approval": "Awaiting Final Approval",
    "cancelled": "Archived",
    "canceled": "Archived",
    "closed": "Archived",
    "compliance hold": "Compliance Hold",
    "existing": "Existing Agent",
    "existing agent": "Existing Agent",
    "hold": "Compliance Hold",
    "head office": "Head Office / Admin Staff",
    "head office admin": "Head Office / Admin Staff",
    "head office admin staff": "Head Office / Admin Staff",
    "head office staff": "Head Office / Admin Staff",
    "inactive": "Archived",
    "live": "Active Agent",
    "onboarding": "Onboarding In Progress",
    "onboarding in progress": "Onboarding In Progress",
    "overdue": "Payment Overdue",
    "past due": "Payment Overdue",
    "past_due": "Payment Overdue",
    "payment active": "Payment Active",
    "payment overdue": "Payment Overdue",
    "payment pending": "Payment Pending",
    "pending": "Payment Pending",
    "registered": "Registered",
    "suspended": "Suspended",
    "terminated": "Terminated",
    "training": "Training In Progress",
    "training in progress": "Training In Progress",
    "trading": "Approved to Trade",
    "unpaid": "Payment Overdue",
}

MEMBERSHIP_STATUS_ALIASES = {
    "active": "Active",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "failed": "Failed Payment",
    "failed payment": "Failed Payment",
    "inactive": "Archived",
    "incomplete": "Payment Pending",
    "incomplete expired": "Failed Payment",
    "incomplete_expired": "Failed Payment",
    "invited": "Invited",
    "live": "Active",
    "overdue": "Overdue",
    "past due": "Overdue",
    "past_due": "Overdue",
    "payment pending": "Payment Pending",
    "pending": "Payment Pending",
    "suspended": "Suspended",
    "terminated": "Terminated",
    "trialing": "Active",
    "unpaid": "Overdue",
}

PAYMENT_STATUS_ALIASES = {
    "active": "Paid",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "failed": "Failed",
    "incomplete": "Pending",
    "incomplete expired": "Failed",
    "incomplete_expired": "Failed",
    "not started": "Not Started",
    "not_started": "Not Started",
    "overdue": "Overdue",
    "paid": "Paid",
    "past due": "Overdue",
    "past_due": "Overdue",
    "pending": "Pending",
    "refunded": "Refunded",
    "trialing": "Pending",
    "unpaid": "Overdue",
}


class AgentImportRowError(ValueError):
    pass


def import_agents_from_csv(
    db: Session,
    request: AgentCsvImportRequest,
    *,
    current_user: User,
) -> dict:
    try:
        rows = read_csv_rows(request)
    except AgentImportRowError as exc:
        return {
            "total_rows": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [{"row_number": 1, "identifier": request.file_name, "message": str(exc)}],
            "next_agent_id": generate_next_agent_id(db),
        }

    result = {
        "total_rows": len(rows),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "stripe_sync_queued": 0,
        "stripe_synced": 0,
        "stripe_sync_failed": 0,
        "stripe_profiles_synced": 0,
        "stripe_profile_fields_synced": 0,
        "stripe_invoices_synced": 0,
        "stripe_subscriptions_synced": 0,
        "errors": [],
        "_stripe_sync_agent_ids": [],
    }

    for row_number, row in rows:
        identifier = clean_text(row.get("agent_id")) or clean_text(row.get("login_email")) or clean_text(row.get("email"))
        try:
            with db.begin_nested():
                action, agent_profile = import_agent_row(
                    db,
                    row=row,
                    update_existing=request.update_existing,
                    current_user=current_user,
                )
                result[action] += 1

            if request.sync_stripe_after_import and action != "skipped":
                stripe_customer_id = db.scalar(
                    select(Membership.stripe_customer_id).where(Membership.agent_id == agent_profile.id)
                )
                if stripe_customer_id:
                    result["_stripe_sync_agent_ids"].append(agent_profile.id)
        except (AgentImportRowError, IntegrityError, ValueError) as exc:
            result["errors"].append(
                {
                    "row_number": row_number,
                    "identifier": identifier,
                    "message": clean_database_error(str(exc)),
                }
            )

    db.commit()
    result["_stripe_sync_agent_ids"] = list(dict.fromkeys(result["_stripe_sync_agent_ids"]))
    result["stripe_sync_queued"] = len(result["_stripe_sync_agent_ids"])
    result["next_agent_id"] = generate_next_agent_id(db)
    return result


def sync_imported_agent_stripe(
    db: Session,
    *,
    agent_profile: AgentProfile,
    current_user: User,
) -> dict[str, int]:
    membership = db.scalar(select(Membership).where(Membership.agent_id == agent_profile.id))
    if membership is None or not membership.stripe_customer_id:
        return {
            "stripe_synced": 0,
            "stripe_sync_failed": 0,
            "stripe_profiles_synced": 0,
            "stripe_profile_fields_synced": 0,
            "stripe_invoices_synced": 0,
            "stripe_subscriptions_synced": 0,
        }

    try:
        with db.begin_nested():
            sync_result = sync_stripe_cache_for_membership(
                db,
                agent_profile=agent_profile,
                membership=membership,
                current_user=current_user,
            )
    except StripeIntegrationError as exc:
        raise AgentImportRowError(f"Stripe sync did not complete: {exc}") from exc

    return {
        "stripe_synced": sync_result["stripe_synced"],
        "stripe_sync_failed": 0,
        "stripe_profiles_synced": sync_result["stripe_profiles_synced"],
        "stripe_profile_fields_synced": sync_result["stripe_profile_fields_synced"],
        "stripe_invoices_synced": sync_result["stripe_invoices_synced"],
        "stripe_subscriptions_synced": sync_result["stripe_subscriptions_synced"],
    }


def read_csv_rows(request: AgentCsvImportRequest) -> list[tuple[int, dict[str, str]]]:
    try:
        raw_base64 = request.file_content_base64.split(",", 1)[-1]
        decoded = base64.b64decode(raw_base64)
        csv_text = decoded.decode("utf-8-sig")
    except Exception as exc:
        raise AgentImportRowError(f"The CSV file could not be read: {exc}") from exc

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise AgentImportRowError("The CSV file needs a header row.")

    rows: list[tuple[int, dict[str, str]]] = []
    for index, row in enumerate(reader, start=2):
        if any(clean_text(value) for value in row.values()):
            rows.append((index, row))
    return rows


def import_agent_row(
    db: Session,
    *,
    row: dict[str, str],
    update_existing: bool,
    current_user: User,
) -> tuple[str, AgentProfile]:
    login_email = clean_email(row.get("login_email") or row.get("email"))
    first_name = required_text(row, "first_name")
    last_name = required_text(row, "last_name")
    agent_id = clean_text(row.get("agent_id"))
    temporary_password = clean_text(row.get("temporary_password"))
    portal_access_enabled = parse_bool(row.get("portal_access_enabled"))
    organization_id = resolve_import_organization_id(db, row=row, current_user=current_user)
    organization_requested = clean_text(row.get("organization_id")) is not None or clean_text(row.get("organization_slug")) is not None

    if login_email is None:
        raise AgentImportRowError("login_email is required.")

    agent_profile = find_existing_agent_profile(db, agent_id=agent_id, login_email=login_email)
    user = find_user_by_email(db, login_email)
    if agent_profile is None and user is not None:
        agent_profile = db.scalar(select(AgentProfile).where(AgentProfile.user_id == user.id))
    is_new_agent = agent_profile is None

    if is_new_agent and user is None:
        if portal_access_enabled is True and not temporary_password:
            raise AgentImportRowError("temporary_password is required when portal_access_enabled is TRUE for a new user.")
        user = create_agent_user(db, login_email, temporary_password, organization_id=organization_id)
    elif user is not None and user.role.name != "Agent":
        raise AgentImportRowError("This login email already belongs to a staff user.")

    if user is None:
        raise AgentImportRowError("A user account could not be found or created.")

    if agent_profile is not None and agent_profile.organization_id not in (None, organization_id):
        if not can_manage_all_organizations(current_user):
            raise AgentImportRowError("This agent belongs to another organisation.")
        if organization_requested:
            agent_profile.organization_id = organization_id
        else:
            organization_id = agent_profile.organization_id

    if temporary_password:
        user.hashed_password = hash_password(temporary_password)
    user.organization_id = organization_id

    if agent_profile is None:
        agent_profile = AgentProfile(
            user_id=user.id,
            organization_id=organization_id,
            agent_id=agent_id or generate_next_agent_id(db),
            first_name=first_name,
            last_name=last_name,
            email=login_email,
            personal_email=clean_email(row.get("personal_email")) or login_email,
            company_email=clean_email(row.get("company_email")),
            portal_access_enabled=True if portal_access_enabled is None else portal_access_enabled,
            status=parse_choice(
                row.get("status"),
                AGENT_STATUSES,
                DEFAULT_AGENT_STATUS,
                "status",
                aliases=AGENT_STATUS_ALIASES,
            ),
        )
        db.add(agent_profile)
        db.flush()
        write_profile_fields(agent_profile, row, is_new=True)
        upsert_membership(db, agent_profile, row)
        create_audit_log(
            db,
            action_type="Account created",
            description=f"Agent imported from CSV: {agent_profile.first_name} {agent_profile.last_name}.",
            created_by=current_user.id,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )
        return "created", agent_profile

    if not update_existing:
        return "skipped", agent_profile

    if agent_profile.user_id != user.id:
        raise AgentImportRowError("The agent ID and login email belong to different existing records.")

    write_profile_fields(agent_profile, row, is_new=False)
    agent_profile.organization_id = organization_id
    agent_profile.first_name = first_name
    agent_profile.last_name = last_name
    agent_profile.email = login_email
    if portal_access_enabled is not None:
        agent_profile.portal_access_enabled = portal_access_enabled
    upsert_membership(db, agent_profile, row)
    return "updated", agent_profile


def find_existing_agent_profile(db: Session, *, agent_id: str | None, login_email: str) -> AgentProfile | None:
    if agent_id:
        agent_profile = db.scalar(select(AgentProfile).where(AgentProfile.agent_id == agent_id))
        if agent_profile is not None:
            return agent_profile

    return db.scalar(select(AgentProfile).where(AgentProfile.email == login_email))


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.role))
        .where(User.email == email)
    )


def create_agent_user(db: Session, email: str, temporary_password: str | None, *, organization_id: int) -> User:
    role = get_agent_role(db)
    password = temporary_password or secrets.token_urlsafe(24)
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        organization_id=organization_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def get_agent_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.name == "Agent"))
    if role is None:
        role = Role(name="Agent", description="Independent travel agent portal access.")
        db.add(role)
        db.flush()
    return role


def resolve_import_organization_id(db: Session, *, row: dict[str, str], current_user: User) -> int:
    requested_id = parse_int(row.get("organization_id"), "organization_id")
    requested_slug = clean_text(row.get("organization_slug"))

    if not can_manage_all_organizations(current_user):
        if requested_id is not None or requested_slug is not None:
            raise AgentImportRowError("Only Super Admin can import agents into another organisation.")
        if current_user.organization_id is not None:
            return current_user.organization_id
        return ensure_default_organization(db).id

    if requested_id is not None:
        organization = db.get(Organization, requested_id)
    elif requested_slug is not None:
        organization = db.scalar(select(Organization).where(Organization.slug == requested_slug))
    else:
        organization = ensure_default_organization(db)

    if organization is None:
        raise AgentImportRowError("The organisation in this row was not found.")
    return organization.id


def write_profile_fields(agent_profile: AgentProfile, row: dict[str, str], *, is_new: bool) -> None:
    values: dict[str, Any] = {
        "first_name": required_text(row, "first_name"),
        "last_name": required_text(row, "last_name"),
        "email": clean_email(row.get("login_email") or row.get("email")),
        "personal_email": clean_email(row.get("personal_email")),
        "company_email": clean_email(row.get("company_email")),
        "phone": clean_text(row.get("phone")),
        "business_name": clean_text(row.get("business_name")),
        "status": parse_choice(
            row.get("status"),
            AGENT_STATUSES,
            DEFAULT_AGENT_STATUS if is_new else None,
            "status",
            aliases=AGENT_STATUS_ALIASES,
        ),
        "joining_date": parse_date(row.get("joining_date"), "joining_date"),
        "address": clean_text(row.get("address")),
        "postcode": clean_text(row.get("postcode")),
        "commission_bank_name": clean_text(row.get("commission_bank_name")),
        "commission_account_name": clean_text(row.get("commission_account_name")),
        "commission_sort_code": clean_text(row.get("commission_sort_code")),
        "commission_account_number": clean_text(row.get("commission_account_number")),
    }

    for field in PROFILE_FIELDS:
        value = values.get(field)
        if value is not None or is_new:
            setattr(agent_profile, field, value)

    if is_new and not agent_profile.personal_email:
        agent_profile.personal_email = agent_profile.email


def upsert_membership(db: Session, agent_profile: AgentProfile, row: dict[str, str]) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.agent_id == agent_profile.id))
    if membership is None:
        membership = Membership(agent_id=agent_profile.id)
        db.add(membership)
        db.flush()

    membership_values = {
        "membership_type": clean_text(row.get("membership_type")),
        "setup_fee_amount": parse_decimal(row.get("setup_fee_amount"), "setup_fee_amount"),
        "monthly_fee_amount": parse_decimal(row.get("monthly_fee_amount"), "monthly_fee_amount"),
        "membership_status": parse_choice(
            row.get("membership_status"),
            MEMBERSHIP_STATUSES,
            None,
            "membership_status",
            aliases=MEMBERSHIP_STATUS_ALIASES,
        ),
        "payment_status": parse_choice(
            row.get("payment_status"),
            PAYMENT_STATUSES,
            None,
            "payment_status",
            aliases=PAYMENT_STATUS_ALIASES,
        ),
        "payment_method": clean_text(row.get("payment_method")),
        "stripe_customer_id": clean_text(row.get("stripe_customer_id")),
        "stripe_subscription_id": clean_text(row.get("stripe_subscription_id")),
        "last_payment_date": parse_date(row.get("last_payment_date"), "last_payment_date"),
        "next_payment_date": parse_date(row.get("next_payment_date"), "next_payment_date"),
        "failed_payment_count": parse_int(row.get("failed_payment_count"), "failed_payment_count"),
        "access_level": clean_text(row.get("access_level")),
        "internal_notes": clean_text(row.get("internal_notes")),
    }

    membership.membership_status = membership.membership_status or DEFAULT_MEMBERSHIP_STATUS
    membership.payment_status = membership.payment_status or DEFAULT_MEMBERSHIP_PAYMENT_STATUS

    for field, value in membership_values.items():
        if value is not None:
            setattr(membership, field, value)

    return membership


def required_text(row: dict[str, str], field: str) -> str:
    value = clean_text(row.get(field))
    if not value:
        raise AgentImportRowError(f"{field} is required.")
    return value


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_email(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    email = text.lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise AgentImportRowError(f"{text} is not a valid email address.")
    return email


def parse_bool(value: object) -> bool | None:
    text = clean_text(value)
    if text is None:
        return None
    normalised = text.lower()
    if normalised in {"true", "yes", "y", "1", "enabled", "active"}:
        return True
    if normalised in {"false", "no", "n", "0", "disabled", "inactive"}:
        return False
    raise AgentImportRowError(f"{text} is not a valid yes/no value.")


def parse_choice(
    value: object,
    allowed: tuple[str, ...],
    default: str | None,
    field: str,
    *,
    aliases: dict[str, str] | None = None,
) -> str | None:
    text = clean_text(value)
    if text is None:
        return default
    allowed_by_key = {normalise_choice_key(choice): choice for choice in allowed}
    key = normalise_choice_key(text)
    if key in allowed_by_key:
        return allowed_by_key[key]
    if aliases:
        aliases_by_key = {normalise_choice_key(alias): choice for alias, choice in aliases.items()}
        if key in aliases_by_key:
            return aliases_by_key[key]
    allowed_values = ", ".join(allowed)
    raise AgentImportRowError(f"{field} must be one of: {allowed_values}.")


def normalise_choice_key(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").strip().lower().split())


def parse_date(value: object, field: str) -> date | None:
    text = clean_text(value)
    if text is None:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise AgentImportRowError(f"{field} must use YYYY-MM-DD or DD/MM/YYYY format.") from exc


def parse_decimal(value: object, field: str) -> Decimal | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise AgentImportRowError(f"{field} must be a number.") from exc
    if amount < 0:
        raise AgentImportRowError(f"{field} cannot be negative.")
    return amount


def parse_int(value: object, field: str) -> int | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        number = int(text)
    except ValueError as exc:
        raise AgentImportRowError(f"{field} must be a whole number.") from exc
    if number < 0:
        raise AgentImportRowError(f"{field} cannot be negative.")
    return number


def clean_database_error(message: str) -> str:
    if "UNIQUE constraint failed" in message:
        return "A unique value, such as agent_id or email, is already used by another record."
    return message
