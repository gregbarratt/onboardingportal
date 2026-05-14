from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.payment import Payment
from app.models.user import User
from app.services.audit import create_audit_log

try:
    import stripe as stripe_sdk
except ImportError:  # pragma: no cover - lets the app explain missing setup cleanly
    stripe_sdk = None


class StripeIntegrationError(RuntimeError):
    """Raised when Stripe cannot complete a live API request."""


def stripe_secret_key_is_configured() -> bool:
    return bool(settings.stripe_secret_key.strip())


def stripe_webhook_secret_is_configured() -> bool:
    return bool(settings.stripe_webhook_secret.strip())


def stripe_sdk_is_available() -> bool:
    return stripe_sdk is not None


def stripe_is_ready_for_live_connection() -> bool:
    return stripe_secret_key_is_configured() and stripe_sdk_is_available()


def stripe_mode() -> str:
    key = settings.stripe_secret_key.strip()
    if key.startswith("sk_live_"):
        return "live"
    if key.startswith("sk_test_"):
        return "test"
    if key:
        return "configured"
    return "not_configured"


def ensure_stripe_ready() -> None:
    if not stripe_secret_key_is_configured():
        raise StripeIntegrationError("Stripe is not connected yet. Add STRIPE_SECRET_KEY to the backend .env file.")
    if not stripe_sdk_is_available():
        raise StripeIntegrationError("The Stripe Python package is not installed in this backend environment.")
    stripe_sdk.api_key = settings.stripe_secret_key.strip()


def ensure_agent_registration_checkout_ready() -> None:
    ensure_stripe_ready()
    if not settings.stripe_agent_monthly_price_id.strip():
        raise StripeIntegrationError(
            "Stripe monthly membership price is not configured. Add STRIPE_AGENT_MONTHLY_PRICE_ID in Render."
        )


def create_stripe_customer(agent_profile: AgentProfile) -> dict[str, Any]:
    ensure_stripe_ready()

    full_name = f"{agent_profile.first_name} {agent_profile.last_name}".strip()
    try:
        customer = stripe_sdk.Customer.create(
            email=billing_email_for_agent(agent_profile),
            name=full_name or None,
            phone=agent_profile.phone,
            metadata={
                "agent_profile_id": str(agent_profile.id),
                "agent_id": agent_profile.agent_id,
                "portal_email": agent_profile.email,
                "company_email": agent_profile.company_email or "",
            },
        )
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe customer could not be created: {exc}") from exc

    return stripe_object_to_dict(customer)


def create_agent_registration_checkout_session(
    *,
    agent_profile: AgentProfile,
    membership: Membership,
) -> dict[str, Any]:
    ensure_agent_registration_checkout_ready()
    if not membership.stripe_customer_id:
        raise StripeIntegrationError("This registration does not have a Stripe customer yet.")

    line_items = [
        {
            "price": settings.stripe_agent_monthly_price_id.strip(),
            "quantity": 1,
        }
    ]
    setup_price_id = settings.stripe_agent_setup_price_id.strip()
    if setup_price_id:
        line_items.insert(
            0,
            {
                "price": setup_price_id,
                "quantity": 1,
            },
        )

    metadata = {
        "agent_profile_id": str(agent_profile.id),
        "membership_id": str(membership.id),
        "agent_id": agent_profile.agent_id,
        "user_id": str(agent_profile.user_id),
        "portal_email": agent_profile.email,
    }

    try:
        session = stripe_sdk.checkout.Session.create(
            mode="subscription",
            customer=membership.stripe_customer_id,
            client_reference_id=f"agent_profile:{agent_profile.id}",
            line_items=line_items,
            success_url=f"{settings.frontend_url.rstrip('/')}/register/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url.rstrip('/')}/register/cancel",
            billing_address_collection="required",
            phone_number_collection={"enabled": True},
            customer_update={
                "address": "auto",
                "name": "auto",
            },
            subscription_data={"metadata": metadata},
            metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe checkout could not be created: {exc}") from exc

    return stripe_object_to_dict(session)


def retrieve_stripe_customer(customer_id: str) -> dict[str, Any]:
    ensure_stripe_ready()
    try:
        customer = stripe_sdk.Customer.retrieve(customer_id)
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe customer could not be loaded: {exc}") from exc
    return stripe_object_to_dict(customer)


def search_stripe_customers_for_agent(agent_profile: AgentProfile, limit: int = 10) -> list[dict[str, Any]]:
    ensure_stripe_ready()
    safe_limit = min(max(limit, 1), 20)
    candidates: dict[str, dict[str, Any]] = {}

    def add_customer(customer: dict[str, Any], *, reason: str, score: int) -> None:
        customer_id = text_or_none(customer.get("id"))
        if not customer_id:
            return

        existing = candidates.get(customer_id)
        row = stripe_customer_to_candidate(customer, reason=reason, score=score)
        if existing is None:
            candidates[customer_id] = row
            return

        reasons = {part.strip() for part in existing["match_reason"].split(";") if part.strip()}
        reasons.add(reason)
        existing["match_reason"] = "; ".join(sorted(reasons))
        existing["match_score"] = max(existing["match_score"], score)

    for email in agent_billing_email_candidates(agent_profile):
        try:
            response = stripe_sdk.Customer.list(email=email, limit=safe_limit)
        except Exception as exc:  # pragma: no cover - depends on Stripe API/network
            raise StripeIntegrationError(f"Stripe customers could not be searched by email: {exc}") from exc

        for customer in stripe_response_data(response):
            customer_dict = stripe_object_to_dict(customer)
            score = 100 if str(customer_dict.get("email") or "").lower() == email.lower() else 90
            add_customer(customer_dict, reason=f"Email match: {email}", score=score)

    search_terms = []
    full_name = agent_full_name(agent_profile)
    if full_name:
        search_terms.append(f"name:'{stripe_search_value(full_name)}'")
    for email in agent_billing_email_candidates(agent_profile):
        search_terms.append(f"email:'{stripe_search_value(email)}'")

    search_error: Exception | None = None
    if search_terms and hasattr(stripe_sdk.Customer, "search"):
        try:
            response = stripe_sdk.Customer.search(query=" OR ".join(search_terms), limit=safe_limit)
            for customer in stripe_response_data(response):
                customer_dict = stripe_object_to_dict(customer)
                reason = stripe_customer_match_reason(customer_dict, agent_profile)
                score = stripe_customer_match_score(customer_dict, agent_profile)
                add_customer(customer_dict, reason=reason, score=score)
        except Exception as exc:  # pragma: no cover - depends on Stripe API/network
            search_error = exc

    if not candidates and search_error is not None:
        raise StripeIntegrationError(f"Stripe customers could not be searched by name: {search_error}") from search_error

    return sorted(
        candidates.values(),
        key=lambda customer: (customer["match_score"], customer["created"] or date.min),
        reverse=True,
    )


def list_stripe_invoices(customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_stripe_ready()
    try:
        response = stripe_sdk.Invoice.list(customer=customer_id, limit=limit)
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe invoices could not be loaded: {exc}") from exc

    invoice_rows = response.get("data", []) if hasattr(response, "get") else response.data
    return [stripe_invoice_to_portal_invoice(stripe_object_to_dict(invoice)) for invoice in invoice_rows]


def list_stripe_subscriptions(customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_stripe_ready()
    try:
        response = stripe_sdk.Subscription.list(
            customer=customer_id,
            status="all",
            limit=limit,
            expand=["data.latest_invoice"],
        )
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe subscriptions could not be loaded: {exc}") from exc

    subscription_rows = response.get("data", []) if hasattr(response, "get") else response.data
    return [
        stripe_subscription_to_portal_subscription(stripe_object_to_dict(subscription))
        for subscription in subscription_rows
    ]


def create_billing_portal_session(customer_id: str, return_path: str = "/membership") -> dict[str, Any]:
    ensure_stripe_ready()
    customer_id = customer_id.strip()
    if not customer_id:
        raise StripeIntegrationError("This membership does not have a Stripe customer ID.")

    safe_return_path = return_path if return_path.startswith("/") else "/membership"
    return_url = f"{settings.frontend_url.rstrip('/')}{safe_return_path}"

    try:
        session = stripe_sdk.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe billing portal could not be opened: {exc}") from exc

    return stripe_object_to_dict(session)


def create_stripe_subscription(membership: Membership) -> dict[str, Any]:
    ensure_stripe_ready()
    if not membership.stripe_customer_id:
        raise StripeIntegrationError("This membership does not have a Stripe customer yet.")
    return {
        "status": "prepared",
        "mode": stripe_mode(),
        "message": "Subscription creation needs a Stripe price ID before it can be safely enabled.",
        "stripe_customer_id": membership.stripe_customer_id,
    }


def cancel_stripe_subscription(membership: Membership) -> dict[str, Any]:
    ensure_stripe_ready()
    if not membership.stripe_subscription_id:
        raise StripeIntegrationError("This membership does not have a Stripe subscription ID.")

    try:
        subscription = stripe_sdk.Subscription.delete(membership.stripe_subscription_id)
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe subscription could not be cancelled: {exc}") from exc

    handle_subscription_cancelled(membership)
    return stripe_object_to_dict(subscription)


def sync_stripe_invoices_for_membership(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    current_user: User | None = None,
) -> list[dict[str, Any]]:
    if not membership.stripe_customer_id:
        return []

    invoices = list_stripe_invoices(membership.stripe_customer_id)
    for invoice in invoices:
        upsert_payment_from_invoice(
            db,
            agent_profile=agent_profile,
            membership=membership,
            invoice=invoice,
            current_user=current_user,
            source="Stripe invoice sync",
        )

    if invoices:
        update_membership_from_invoice(
            db,
            agent_profile=agent_profile,
            membership=membership,
            invoice=invoices[0],
            current_user=current_user,
            source="Stripe invoice sync",
        )

    return invoices


def mark_stripe_sync_success(membership: Membership) -> None:
    membership.stripe_last_synced_at = datetime.now(timezone.utc)
    membership.stripe_sync_status = "Synced"
    membership.stripe_sync_error = None


def mark_stripe_sync_failed(membership: Membership, error: object) -> None:
    membership.stripe_last_synced_at = datetime.now(timezone.utc)
    membership.stripe_sync_status = "Failed"
    membership.stripe_sync_error = text_or_none(error)[:1000] if text_or_none(error) else "Stripe sync failed."


def sync_stripe_cache_for_membership(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    current_user: User | None = None,
) -> dict[str, int]:
    if not membership.stripe_customer_id:
        membership.stripe_sync_status = "Not linked"
        membership.stripe_sync_error = None
        return {
            "stripe_synced": 0,
            "stripe_profiles_synced": 0,
            "stripe_profile_fields_synced": 0,
            "stripe_invoices_synced": 0,
            "stripe_subscriptions_synced": 0,
        }

    profile_fields = sync_stripe_customer_profile_for_agent(
        agent_profile=agent_profile,
        membership=membership,
    )
    subscription = sync_stripe_subscription_for_membership(
        db,
        agent_profile=agent_profile,
        membership=membership,
        current_user=current_user,
    )
    invoices = sync_stripe_invoices_for_membership(
        db,
        agent_profile=agent_profile,
        membership=membership,
        current_user=current_user,
    )
    mark_stripe_sync_success(membership)
    return {
        "stripe_synced": 1,
        "stripe_profiles_synced": 1 if profile_fields else 0,
        "stripe_profile_fields_synced": len(profile_fields),
        "stripe_invoices_synced": len(invoices),
        "stripe_subscriptions_synced": 1 if subscription is not None else 0,
    }


def sync_stripe_customer_profile_for_agent(
    *,
    agent_profile: AgentProfile,
    membership: Membership,
) -> list[str]:
    if not membership.stripe_customer_id:
        return []

    customer = retrieve_stripe_customer(membership.stripe_customer_id)
    return apply_stripe_customer_details_to_agent_profile(agent_profile, customer)


def apply_stripe_customer_details_to_agent_profile(agent_profile: AgentProfile, customer: dict[str, Any]) -> list[str]:
    updated_fields: list[str] = []

    customer_email = text_or_none(customer.get("email"))
    if customer_email and not text_or_none(agent_profile.personal_email):
        agent_profile.personal_email = customer_email.lower()
        updated_fields.append("personal_email")

    customer_phone = text_or_none(customer.get("phone"))
    if customer_phone and not text_or_none(agent_profile.phone):
        agent_profile.phone = customer_phone
        updated_fields.append("phone")

    address = customer.get("address") if isinstance(customer.get("address"), dict) else {}
    postal_code = text_or_none(address.get("postal_code"))
    if postal_code and not text_or_none(agent_profile.postcode):
        agent_profile.postcode = postal_code
        updated_fields.append("postcode")

    billing_address = format_stripe_billing_address(address)
    if billing_address and not text_or_none(agent_profile.address):
        agent_profile.address = billing_address
        updated_fields.append("address")

    metadata = customer.get("metadata") if isinstance(customer.get("metadata"), dict) else {}
    business_name = text_or_none(metadata.get("business_name") or metadata.get("company_name"))
    if business_name and not text_or_none(agent_profile.business_name):
        agent_profile.business_name = business_name
        updated_fields.append("business_name")

    return updated_fields


def format_stripe_billing_address(address: dict[str, Any]) -> str | None:
    address_parts = [
        text_or_none(address.get("line1")),
        text_or_none(address.get("line2")),
        text_or_none(address.get("city")),
        text_or_none(address.get("state")),
        text_or_none(address.get("country")),
    ]
    lines = [part for part in address_parts if part]
    return ", ".join(lines) or None


def sync_stripe_subscription_for_membership(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    current_user: User | None = None,
) -> dict[str, Any] | None:
    if not membership.stripe_customer_id:
        return None

    subscriptions = list_stripe_subscriptions(membership.stripe_customer_id)
    subscription = choose_subscription_for_membership(membership, subscriptions)
    if subscription is None:
        return None

    update_membership_from_subscription(
        db,
        agent_profile=agent_profile,
        membership=membership,
        subscription=subscription,
        current_user=current_user,
        source="Stripe subscription sync",
    )
    return subscription


def handle_successful_payment(payment: Payment, membership: Membership | None = None) -> dict[str, Any]:
    payment.payment_status = "Paid"
    payment.payment_date = payment.payment_date or date.today()

    if membership is not None:
        membership.payment_status = "Paid"
        membership.membership_status = "Active"
        membership.last_payment_date = payment.payment_date
        membership.failed_payment_count = 0

    return {
        "status": "handled",
        "action": "handle_successful_payment",
        "payment_id": payment.id,
        "stripe_payment_id": payment.stripe_payment_id,
    }


def handle_failed_payment(payment: Payment, membership: Membership | None = None) -> dict[str, Any]:
    payment.payment_status = "Failed"

    if membership is not None:
        membership.payment_status = "Failed"
        membership.membership_status = "Failed Payment"
        membership.failed_payment_count = (membership.failed_payment_count or 0) + 1

    return {
        "status": "handled",
        "action": "handle_failed_payment",
        "payment_id": payment.id,
        "stripe_payment_id": payment.stripe_payment_id,
    }


def handle_subscription_cancelled(membership: Membership) -> dict[str, Any]:
    membership.membership_status = "Cancelled"
    membership.payment_status = "Cancelled"
    membership.cancellation_date = membership.cancellation_date or date.today()

    return {
        "status": "handled",
        "action": "handle_subscription_cancelled",
        "membership_id": membership.id,
        "stripe_subscription_id": membership.stripe_subscription_id,
    }


def process_stripe_webhook_event(
    db: Session,
    *,
    payload: bytes,
    stripe_signature: str | None,
) -> dict[str, Any]:
    event = parse_stripe_event(payload, stripe_signature)
    event_type = str(event.get("type", "unknown"))
    event_data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
    stripe_object = event_data.get("object") if isinstance(event_data.get("object"), dict) else {}

    handled = False
    if event_type == "checkout.session.completed":
        handle_checkout_session_completed(db, session=stripe_object)
        handled = True
    elif event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed"}:
        handle_stripe_invoice_event(db, event_type=event_type, invoice=stripe_object)
        handled = True
    elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        handle_stripe_subscription_event(db, event_type=event_type, subscription=stripe_object)
        handled = True
    elif event_type == "customer.subscription.deleted":
        handle_stripe_subscription_event(db, event_type=event_type, subscription=stripe_object)
        handled = True

    db.commit()
    return {
        "status": "received",
        "mode": stripe_mode(),
        "event_type": event_type,
        "handled": handled,
    }


def parse_stripe_event(payload: bytes, stripe_signature: str | None) -> dict[str, Any]:
    if stripe_webhook_secret_is_configured():
        if not stripe_signature:
            raise StripeIntegrationError("Stripe webhook signature was missing.")
        if not stripe_sdk_is_available():
            raise StripeIntegrationError("The Stripe Python package is not installed in this backend environment.")
        try:
            return stripe_sdk.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=settings.stripe_webhook_secret.strip(),
            )
        except Exception as exc:
            raise StripeIntegrationError(f"Stripe webhook signature could not be verified: {exc}") from exc

    try:
        decoded_payload = payload.decode("utf-8") if payload else "{}"
        event = json.loads(decoded_payload)
    except json.JSONDecodeError as exc:
        raise StripeIntegrationError(f"Stripe webhook payload could not be read: {exc}") from exc

    return event if isinstance(event, dict) else {"type": "unknown"}


def handle_checkout_session_completed(db: Session, *, session: dict[str, Any]) -> None:
    customer_id = text_or_none(session.get("customer"))
    subscription_id = text_or_none(session.get("subscription"))
    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    membership_id = text_or_none(metadata.get("membership_id"))

    membership = None
    if membership_id:
        try:
            membership = db.get(Membership, int(membership_id))
        except ValueError:
            membership = None
    if membership is None and customer_id:
        membership = db.scalar(select(Membership).where(Membership.stripe_customer_id == customer_id))
    if membership is None:
        return

    agent_profile = db.get(AgentProfile, membership.agent_id)
    if agent_profile is None:
        return

    previous_membership_status = membership.membership_status
    previous_payment_status = membership.payment_status

    if customer_id:
        membership.stripe_customer_id = customer_id
    if subscription_id:
        membership.stripe_subscription_id = subscription_id
    membership.payment_method = membership.payment_method or "Stripe"

    if session.get("payment_status") == "paid":
        membership.membership_status = "Active"
        membership.payment_status = "Paid"
        membership.last_payment_date = date.today()
        membership.failed_payment_count = 0
        agent_profile.status = "Payment Active"
        agent_profile.portal_access_enabled = True
    else:
        membership.membership_status = "Payment Pending"
        membership.payment_status = "Pending"

    add_membership_audit_log(
        db,
        agent_profile=agent_profile,
        membership=membership,
        current_user=None,
        previous_membership_status=previous_membership_status,
        previous_payment_status=previous_payment_status,
        source="Stripe checkout completed",
    )


def handle_stripe_invoice_event(db: Session, *, event_type: str, invoice: dict[str, Any]) -> None:
    customer_id = text_or_none(invoice.get("customer"))
    if not customer_id:
        return

    membership = db.scalar(select(Membership).where(Membership.stripe_customer_id == customer_id))
    if membership is None:
        return

    agent_profile = db.get(AgentProfile, membership.agent_id)
    if agent_profile is None:
        return

    portal_invoice = stripe_invoice_to_portal_invoice(invoice)
    if event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        portal_invoice["status"] = "paid"
        portal_invoice["paid"] = True
    elif event_type == "invoice.payment_failed":
        portal_invoice["status"] = "uncollectible"
        portal_invoice["paid"] = False

    upsert_payment_from_invoice(
        db,
        agent_profile=agent_profile,
        membership=membership,
        invoice=portal_invoice,
        current_user=None,
        source=f"Stripe webhook {event_type}",
    )
    update_membership_from_invoice(
        db,
        agent_profile=agent_profile,
        membership=membership,
        invoice=portal_invoice,
        current_user=None,
        source=f"Stripe webhook {event_type}",
    )


def handle_stripe_subscription_event(db: Session, *, event_type: str, subscription: dict[str, Any]) -> None:
    subscription_id = text_or_none(subscription.get("id"))
    if not subscription_id:
        return

    customer_id = text_or_none(subscription.get("customer"))
    membership = db.scalar(select(Membership).where(Membership.stripe_subscription_id == subscription_id))
    if membership is None and customer_id:
        membership = db.scalar(select(Membership).where(Membership.stripe_customer_id == customer_id))
    if membership is None:
        return

    agent_profile = db.get(AgentProfile, membership.agent_id)
    if agent_profile is None:
        return

    portal_subscription = stripe_subscription_to_portal_subscription(subscription)
    if event_type == "customer.subscription.deleted":
        portal_subscription["status"] = "canceled"

    update_membership_from_subscription(
        db,
        agent_profile=agent_profile,
        membership=membership,
        subscription=portal_subscription,
        current_user=None,
        source=f"Stripe webhook {event_type}",
    )


def upsert_payment_from_invoice(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    invoice: dict[str, Any],
    current_user: User | None,
    source: str,
) -> Payment:
    invoice_id = text_or_none(invoice.get("stripe_invoice_id") or invoice.get("id"))
    if not invoice_id:
        raise StripeIntegrationError("Stripe invoice did not include an invoice ID.")

    payment = db.scalar(
        select(Payment).where(
            Payment.agent_id == agent_profile.id,
            Payment.stripe_payment_id == invoice_id,
        )
    )

    previous_status = payment.payment_status if payment is not None else None
    if payment is None:
        payment = Payment(
            agent_id=agent_profile.id,
            amount=Decimal("0.00"),
            currency="GBP",
            payment_type="Stripe Invoice",
            stripe_payment_id=invoice_id,
        )
        db.add(payment)

    amount = invoice_amount_for_portal_payment(invoice)
    payment.amount = amount
    payment.currency = str(invoice.get("currency") or "GBP").upper()
    payment.payment_type = "Stripe Invoice"
    payment.payment_status = map_invoice_status_to_payment_status(invoice.get("status"))
    payment.payment_date = paid_date_from_invoice(invoice)
    payment.due_date = date_from_timestamp(invoice.get("due_date"))
    payment.invoice_url = text_or_none(invoice.get("hosted_invoice_url")) or text_or_none(invoice.get("invoice_pdf"))
    payment.notes = stripe_invoice_note(invoice)

    if previous_status != payment.payment_status:
        create_audit_log(
            db,
            action_type="Payment status changed",
            description=f"{source}: invoice {invoice_id} is now {payment.payment_status}.",
            previous_value=text_or_none(previous_status),
            new_value=payment.payment_status,
            created_by=current_user.id if current_user else None,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )

    return payment


def update_membership_from_invoice(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    invoice: dict[str, Any],
    current_user: User | None,
    source: str,
) -> None:
    previous_membership_status = membership.membership_status
    previous_payment_status = membership.payment_status
    invoice_status = str(invoice.get("status") or "").lower()
    payment_status = map_invoice_status_to_payment_status(invoice_status)

    membership.payment_status = payment_status
    if payment_status == "Paid":
        membership.membership_status = "Active"
        membership.last_payment_date = paid_date_from_invoice(invoice) or date.today()
        membership.failed_payment_count = 0
        agent_profile.status = "Payment Active"
        agent_profile.portal_access_enabled = True
    elif payment_status == "Failed":
        membership.membership_status = "Failed Payment"
        attempt_count = int(invoice.get("attempt_count") or 0)
        membership.failed_payment_count = max(membership.failed_payment_count or 0, attempt_count or 1)
    elif payment_status == "Overdue":
        membership.membership_status = "Overdue"
    elif invoice_status == "open":
        membership.membership_status = "Payment Pending"

    subscription_id = text_or_none(invoice.get("subscription"))
    if subscription_id:
        membership.stripe_subscription_id = subscription_id

    add_membership_audit_log(
        db,
        agent_profile=agent_profile,
        membership=membership,
        current_user=current_user,
        previous_membership_status=previous_membership_status,
        previous_payment_status=previous_payment_status,
        source=source,
    )
    mark_stripe_sync_success(membership)


def update_membership_from_subscription(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    subscription: dict[str, Any],
    current_user: User | None,
    source: str,
) -> None:
    previous_membership_status = membership.membership_status
    previous_payment_status = membership.payment_status
    previous_subscription_id = membership.stripe_subscription_id

    subscription_id = text_or_none(subscription.get("stripe_subscription_id") or subscription.get("id"))
    if subscription_id:
        membership.stripe_subscription_id = subscription_id
    membership.payment_method = membership.payment_method or "Stripe"

    membership_status, payment_status = map_subscription_status_to_membership_status(subscription.get("status"))
    membership.membership_status = membership_status
    membership.payment_status = payment_status
    membership.next_payment_date = subscription.get("current_period_end") or membership.next_payment_date
    if subscription.get("canceled_at"):
        membership.cancellation_date = subscription.get("canceled_at")
    if membership_status == "Active":
        agent_profile.status = "Payment Active"
        agent_profile.portal_access_enabled = True
    elif membership_status in {"Overdue", "Suspended"}:
        agent_profile.status = "Payment Overdue" if membership_status == "Overdue" else "Suspended"

    add_membership_audit_log(
        db,
        agent_profile=agent_profile,
        membership=membership,
        current_user=current_user,
        previous_membership_status=previous_membership_status,
        previous_payment_status=previous_payment_status,
        source=source,
    )

    if previous_subscription_id != membership.stripe_subscription_id:
        create_audit_log(
            db,
            action_type="Payment setup completed",
            description=f"{source}: subscription linked as {membership.stripe_subscription_id}.",
            previous_value=text_or_none(previous_subscription_id),
            new_value=text_or_none(membership.stripe_subscription_id),
            created_by=current_user.id if current_user else None,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )
    mark_stripe_sync_success(membership)


def add_membership_audit_log(
    db: Session,
    *,
    agent_profile: AgentProfile,
    membership: Membership,
    current_user: User | None,
    previous_membership_status: str | None,
    previous_payment_status: str | None,
    source: str,
) -> None:
    if previous_membership_status != membership.membership_status:
        create_audit_log(
            db,
            action_type="Membership status changed",
            description=f"{source}: membership moved to {membership.membership_status}.",
            previous_value=text_or_none(previous_membership_status),
            new_value=membership.membership_status,
            created_by=current_user.id if current_user else None,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )

    if previous_payment_status != membership.payment_status:
        create_audit_log(
            db,
            action_type="Payment status changed",
            description=f"{source}: payment status moved to {membership.payment_status}.",
            previous_value=text_or_none(previous_payment_status),
            new_value=membership.payment_status,
            created_by=current_user.id if current_user else None,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )


def stripe_invoice_to_portal_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    status_transitions = invoice.get("status_transitions") or {}
    subscription_id = text_or_none(invoice.get("subscription"))
    if not subscription_id:
        parent = invoice.get("parent") or {}
        subscription_details = parent.get("subscription_details") or {}
        subscription_id = text_or_none(subscription_details.get("subscription"))

    return {
        "stripe_invoice_id": text_or_none(invoice.get("id")) or "",
        "number": text_or_none(invoice.get("number")),
        "status": text_or_none(invoice.get("status")) or "unknown",
        "currency": str(invoice.get("currency") or "GBP").upper(),
        "amount_due": stripe_amount_to_decimal(invoice.get("amount_due"), invoice.get("currency")),
        "amount_paid": stripe_amount_to_decimal(invoice.get("amount_paid"), invoice.get("currency")),
        "amount_remaining": stripe_amount_to_decimal(invoice.get("amount_remaining"), invoice.get("currency")),
        "hosted_invoice_url": text_or_none(invoice.get("hosted_invoice_url")),
        "invoice_pdf": text_or_none(invoice.get("invoice_pdf")),
        "created": date_from_timestamp(invoice.get("created")),
        "due_date": date_from_timestamp(invoice.get("due_date")),
        "paid": bool(invoice.get("paid")),
        "attempt_count": int(invoice.get("attempt_count") or 0),
        "subscription": subscription_id,
        "customer": text_or_none(invoice.get("customer")),
        "payment_intent": text_or_none(invoice.get("payment_intent")),
        "livemode": bool(invoice.get("livemode")),
        "paid_at": date_from_timestamp(status_transitions.get("paid_at")),
    }


def stripe_subscription_to_portal_subscription(subscription: dict[str, Any]) -> dict[str, Any]:
    latest_invoice = subscription.get("latest_invoice")
    latest_invoice_data = latest_invoice if isinstance(latest_invoice, dict) else {}
    latest_invoice_id = text_or_none(latest_invoice_data.get("id")) or text_or_none(latest_invoice)
    first_item = first_subscription_item(subscription)

    return {
        "stripe_subscription_id": text_or_none(subscription.get("id")) or "",
        "status": text_or_none(subscription.get("status")) or "unknown",
        "customer": text_or_none(subscription.get("customer")),
        "current_period_start": date_from_timestamp(subscription.get("current_period_start") or first_item.get("current_period_start")),
        "current_period_end": date_from_timestamp(subscription.get("current_period_end") or first_item.get("current_period_end")),
        "cancel_at_period_end": bool(subscription.get("cancel_at_period_end")),
        "canceled_at": date_from_timestamp(subscription.get("canceled_at")),
        "trial_start": date_from_timestamp(subscription.get("trial_start")),
        "trial_end": date_from_timestamp(subscription.get("trial_end")),
        "latest_invoice": latest_invoice_id,
        "latest_invoice_status": text_or_none(latest_invoice_data.get("status")),
        "latest_invoice_url": text_or_none(latest_invoice_data.get("hosted_invoice_url")),
        "collection_method": text_or_none(subscription.get("collection_method")),
        "livemode": bool(subscription.get("livemode")),
        "created": date_from_timestamp(subscription.get("created")),
    }


def first_subscription_item(subscription: dict[str, Any]) -> dict[str, Any]:
    items = subscription.get("items") or {}
    data = items.get("data") if isinstance(items, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def choose_subscription_for_membership(
    membership: Membership,
    subscriptions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not subscriptions:
        return None

    if membership.stripe_subscription_id:
        for subscription in subscriptions:
            if subscription.get("stripe_subscription_id") == membership.stripe_subscription_id:
                return subscription

    for preferred_status in ("active", "trialing", "past_due", "incomplete"):
        for subscription in subscriptions:
            if str(subscription.get("status") or "").lower() == preferred_status:
                return subscription

    return subscriptions[0]


def map_subscription_status_to_membership_status(status: object) -> tuple[str, str]:
    subscription_status = str(status or "").lower()
    if subscription_status in {"active", "trialing"}:
        return "Active", "Paid"
    if subscription_status in {"past_due", "unpaid"}:
        return "Overdue", "Overdue"
    if subscription_status in {"incomplete", "incomplete_expired"}:
        return "Payment Pending", "Pending"
    if subscription_status in {"canceled", "cancelled"}:
        return "Cancelled", "Cancelled"
    if subscription_status == "paused":
        return "Suspended", "Failed"
    return "Payment Pending", "Pending"


def map_invoice_status_to_payment_status(status: object) -> str:
    invoice_status = str(status or "").lower()
    if invoice_status == "paid":
        return "Paid"
    if invoice_status in {"void", "voided"}:
        return "Cancelled"
    if invoice_status == "uncollectible":
        return "Failed"
    if invoice_status == "open":
        return "Pending"
    if invoice_status == "draft":
        return "Not Started"
    return "Pending"


def billing_email_for_agent(agent_profile: AgentProfile) -> str:
    return agent_profile.personal_email or agent_profile.email


def agent_full_name(agent_profile: AgentProfile) -> str:
    return f"{agent_profile.first_name} {agent_profile.last_name}".strip()


def agent_billing_email_candidates(agent_profile: AgentProfile) -> list[str]:
    emails = [
        agent_profile.personal_email,
        agent_profile.email,
        agent_profile.company_email,
    ]
    unique_emails: list[str] = []
    seen: set[str] = set()
    for email in emails:
        cleaned = text_or_none(email)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        unique_emails.append(cleaned)
        seen.add(key)
    return unique_emails


def stripe_search_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def stripe_response_data(response: Any) -> list[Any]:
    if hasattr(response, "get"):
        data = response.get("data", [])
    else:
        data = getattr(response, "data", [])
    return list(data or [])


def stripe_customer_to_candidate(customer: dict[str, Any], *, reason: str, score: int) -> dict[str, Any]:
    return {
        "stripe_customer_id": text_or_none(customer.get("id")) or "",
        "name": text_or_none(customer.get("name")),
        "email": text_or_none(customer.get("email")),
        "phone": text_or_none(customer.get("phone")),
        "created": date_from_timestamp(customer.get("created")),
        "livemode": bool(customer.get("livemode")),
        "delinquent": bool(customer.get("delinquent")),
        "invoice_prefix": text_or_none(customer.get("invoice_prefix")),
        "match_reason": reason,
        "match_score": score,
    }


def stripe_customer_match_reason(customer: dict[str, Any], agent_profile: AgentProfile) -> str:
    customer_email = str(customer.get("email") or "").lower()
    customer_name = str(customer.get("name") or "").lower()
    reasons: list[str] = []

    for email in agent_billing_email_candidates(agent_profile):
        if customer_email == email.lower():
            reasons.append(f"Email match: {email}")

    full_name = agent_full_name(agent_profile)
    if full_name and customer_name == full_name.lower():
        reasons.append(f"Name match: {full_name}")
    elif full_name and full_name.lower() in customer_name:
        reasons.append(f"Possible name match: {full_name}")

    return "; ".join(reasons) or "Possible Stripe match"


def stripe_customer_match_score(customer: dict[str, Any], agent_profile: AgentProfile) -> int:
    customer_email = str(customer.get("email") or "").lower()
    customer_name = str(customer.get("name") or "").lower()
    score = 50

    if any(customer_email == email.lower() for email in agent_billing_email_candidates(agent_profile)):
        score = max(score, 100)

    full_name = agent_full_name(agent_profile).lower()
    if full_name and customer_name == full_name:
        score = max(score, 90)
    elif full_name and full_name in customer_name:
        score = max(score, 75)

    return score


def invoice_amount_for_portal_payment(invoice: dict[str, Any]) -> Decimal:
    amount_paid = invoice.get("amount_paid")
    if isinstance(amount_paid, Decimal) and amount_paid > 0:
        return amount_paid
    amount_due = invoice.get("amount_due")
    if isinstance(amount_due, Decimal):
        return amount_due
    return Decimal("0.00")


def paid_date_from_invoice(invoice: dict[str, Any]) -> date | None:
    if invoice.get("paid_at"):
        return invoice["paid_at"]
    if invoice.get("paid"):
        return date_from_timestamp(invoice.get("created")) or date.today()
    return None


def stripe_invoice_note(invoice: dict[str, Any]) -> str:
    invoice_number = text_or_none(invoice.get("number"))
    invoice_id = text_or_none(invoice.get("stripe_invoice_id") or invoice.get("id"))
    label = invoice_number or invoice_id or "unknown"
    return f"Stripe invoice {label}"


def stripe_amount_to_decimal(value: object, currency: object = None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    zero_decimal_currencies = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
    divisor = Decimal("1") if str(currency or "").upper() in zero_decimal_currencies else Decimal("100")
    return (Decimal(str(value)) / divisor).quantize(Decimal("0.01"))


def date_from_timestamp(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


def text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def stripe_object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)
