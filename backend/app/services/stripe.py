from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.payment import Payment

try:
    import stripe as stripe_sdk
except ImportError:  # pragma: no cover - keeps local placeholder mode working before install
    stripe_sdk = None


STRIPE_PREPARATION_MESSAGE = (
    "Stripe is prepared, but this project is still in placeholder mode. "
    "No real customer, subscription, charge, refund, or cancellation has been sent to Stripe."
)


def stripe_secret_key_is_configured() -> bool:
    return bool(settings.stripe_secret_key.strip())


def stripe_webhook_secret_is_configured() -> bool:
    return bool(settings.stripe_webhook_secret.strip())


def stripe_sdk_is_available() -> bool:
    return stripe_sdk is not None


def stripe_is_ready_for_live_connection() -> bool:
    return stripe_secret_key_is_configured() and stripe_sdk_is_available()


def create_stripe_customer(agent_profile: AgentProfile) -> dict[str, Any]:
    return placeholder_response(
        action="create_customer",
        message=f"Customer creation is prepared for agent {agent_profile.agent_id}.",
        reference=f"cus_placeholder_{agent_profile.agent_id.lower().replace('-', '_')}",
    )


def create_stripe_subscription(membership: Membership) -> dict[str, Any]:
    return placeholder_response(
        action="create_subscription",
        message=f"Subscription creation is prepared for membership {membership.id}.",
        reference=f"sub_placeholder_membership_{membership.id}",
    )


def cancel_stripe_subscription(membership: Membership) -> dict[str, Any]:
    return placeholder_response(
        action="cancel_subscription",
        message=f"Subscription cancellation is prepared for membership {membership.id}.",
        reference=membership.stripe_subscription_id or f"sub_placeholder_membership_{membership.id}",
    )


def handle_successful_payment(payment: Payment, membership: Membership | None = None) -> dict[str, Any]:
    payment.payment_status = "Paid"
    payment.payment_date = payment.payment_date or date.today()

    if membership is not None:
        membership.payment_status = "Paid"
        membership.membership_status = "Active"
        membership.last_payment_date = payment.payment_date
        membership.failed_payment_count = 0

    return placeholder_response(
        action="handle_successful_payment",
        message=f"Payment success handling is prepared for payment {payment.id}.",
        reference=payment.stripe_payment_id,
    )


def handle_failed_payment(payment: Payment, membership: Membership | None = None) -> dict[str, Any]:
    payment.payment_status = "Failed"

    if membership is not None:
        membership.payment_status = "Failed"
        membership.membership_status = "Failed Payment"
        membership.failed_payment_count = (membership.failed_payment_count or 0) + 1

    return placeholder_response(
        action="handle_failed_payment",
        message=f"Payment failure handling is prepared for payment {payment.id}.",
        reference=payment.stripe_payment_id,
    )


def handle_subscription_cancelled(membership: Membership) -> dict[str, Any]:
    membership.membership_status = "Cancelled"
    membership.payment_status = "Cancelled"
    membership.cancellation_date = membership.cancellation_date or date.today()

    return placeholder_response(
        action="handle_subscription_cancelled",
        message=f"Subscription cancellation handling is prepared for membership {membership.id}.",
        reference=membership.stripe_subscription_id,
    )


def process_stripe_webhook_event(
    db: Session,
    *,
    payload: bytes,
    stripe_signature: str | None,
) -> dict[str, Any]:
    event = parse_stripe_event(payload, stripe_signature)
    event_type = event.get("type", "unknown")

    return {
        "status": "received",
        "mode": "placeholder",
        "event_type": event_type,
        "handled_by": webhook_handler_name(event_type),
        "stripe_secret_key_configured": stripe_secret_key_is_configured(),
        "stripe_webhook_secret_configured": stripe_webhook_secret_is_configured(),
        "stripe_sdk_available": stripe_sdk_is_available(),
        "database_ready": db is not None,
        "message": (
            "Stripe webhook received. This placeholder does not change payment records "
            "until the real Stripe mapping rules are added."
        ),
    }


def parse_stripe_event(payload: bytes, stripe_signature: str | None) -> dict[str, Any]:
    if stripe_webhook_secret_is_configured() and stripe_signature and stripe_sdk_is_available():
        try:
            return stripe_sdk.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=settings.stripe_webhook_secret,
            )
        except Exception as exc:
            return {"type": "signature_verification_failed", "error": str(exc)}

    try:
        decoded_payload = payload.decode("utf-8") if payload else "{}"
        event = json.loads(decoded_payload)
    except json.JSONDecodeError:
        event = {"type": "unparseable"}

    return event if isinstance(event, dict) else {"type": "unknown"}


def webhook_handler_name(event_type: str) -> str:
    if event_type in {"invoice.payment_succeeded", "payment_intent.succeeded"}:
        return "handle_successful_payment"
    if event_type in {"invoice.payment_failed", "payment_intent.payment_failed"}:
        return "handle_failed_payment"
    if event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        return "handle_subscription_cancelled"
    return "placeholder_acknowledgement"


def placeholder_response(action: str, message: str, reference: str | None = None) -> dict[str, Any]:
    return {
        "status": "prepared",
        "mode": "placeholder",
        "action": action,
        "reference": reference,
        "stripe_secret_key_configured": stripe_secret_key_is_configured(),
        "stripe_sdk_available": stripe_sdk_is_available(),
        "ready_for_live_connection": stripe_is_ready_for_live_connection(),
        "message": f"{message} {STRIPE_PREPARATION_MESSAGE}",
    }
