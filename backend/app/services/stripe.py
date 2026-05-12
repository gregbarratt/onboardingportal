from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.payment import Payment


def create_stripe_customer(agent_profile: AgentProfile) -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": f"Stripe customer creation placeholder for agent {agent_profile.agent_id}.",
    }


def create_stripe_subscription(membership: Membership) -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": f"Stripe subscription creation placeholder for membership {membership.id}.",
    }


def cancel_stripe_subscription(membership: Membership) -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": f"Stripe subscription cancellation placeholder for membership {membership.id}.",
    }


def handle_successful_payment(payment: Payment) -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": f"Stripe successful payment placeholder for payment {payment.id}.",
    }


def handle_failed_payment(payment: Payment) -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": f"Stripe failed payment placeholder for payment {payment.id}.",
    }

