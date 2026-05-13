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


def retrieve_stripe_customer(customer_id: str) -> dict[str, Any]:
    ensure_stripe_ready()
    try:
        customer = stripe_sdk.Customer.retrieve(customer_id)
    except Exception as exc:  # pragma: no cover - depends on Stripe API/network
        raise StripeIntegrationError(f"Stripe customer could not be loaded: {exc}") from exc
    return stripe_object_to_dict(customer)


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
    if event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed"}:
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
