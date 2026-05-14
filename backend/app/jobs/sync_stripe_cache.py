from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.services.stripe import (
    StripeIntegrationError,
    mark_stripe_sync_failed,
    stripe_is_ready_for_live_connection,
    sync_stripe_cache_for_membership,
)


def run_nightly_stripe_sync() -> dict[str, int]:
    if not stripe_is_ready_for_live_connection():
        print("Stripe is not configured, so the nightly sync was skipped.")
        return {
            "checked": 0,
            "synced": 0,
            "failed": 0,
            "profiles_updated": 0,
            "profile_fields_updated": 0,
            "invoices_synced": 0,
            "subscriptions_synced": 0,
        }

    db = SessionLocal()
    try:
        return sync_memberships(db)
    finally:
        db.close()


def sync_memberships(db: Session) -> dict[str, int]:
    limit = max(settings.stripe_nightly_sync_limit, 1)
    rows = list(
        db.execute(
            select(Membership.id, AgentProfile.id)
            .join(AgentProfile, Membership.agent_id == AgentProfile.id)
            .where(Membership.stripe_customer_id.is_not(None))
            .where(Membership.stripe_customer_id != "")
            .order_by(Membership.stripe_last_synced_at.is_not(None), Membership.stripe_last_synced_at, Membership.id)
            .limit(limit)
        )
    )

    result = {
        "checked": len(rows),
        "synced": 0,
        "failed": 0,
        "profiles_updated": 0,
        "profile_fields_updated": 0,
        "invoices_synced": 0,
        "subscriptions_synced": 0,
    }

    for membership_id, agent_profile_id in rows:
        membership = db.get(Membership, membership_id)
        agent_profile = db.get(AgentProfile, agent_profile_id)
        if membership is None or agent_profile is None:
            continue

        try:
            sync_result = sync_stripe_cache_for_membership(
                db,
                agent_profile=agent_profile,
                membership=membership,
                current_user=None,
            )
            db.commit()
        except StripeIntegrationError as exc:
            db.rollback()
            failed_membership = db.get(Membership, membership_id)
            if failed_membership is not None:
                mark_stripe_sync_failed(failed_membership, exc)
                db.commit()
            result["failed"] += 1
            print(f"Stripe sync failed for membership {membership_id}: {exc}")
            continue
        except Exception as exc:
            db.rollback()
            failed_membership = db.get(Membership, membership_id)
            if failed_membership is not None:
                mark_stripe_sync_failed(failed_membership, exc)
                db.commit()
            result["failed"] += 1
            print(f"Unexpected sync failure for membership {membership_id}: {exc}")
            continue

        result["synced"] += sync_result["stripe_synced"]
        result["profiles_updated"] += sync_result["stripe_profiles_synced"]
        result["profile_fields_updated"] += sync_result["stripe_profile_fields_synced"]
        result["invoices_synced"] += sync_result["stripe_invoices_synced"]
        result["subscriptions_synced"] += sync_result["stripe_subscriptions_synced"]

    return result


def main() -> None:
    result = run_nightly_stripe_sync()
    print(
        "Nightly Stripe sync complete: "
        f"{result['checked']} checked, "
        f"{result['synced']} synced, "
        f"{result['failed']} failed, "
        f"{result['invoices_synced']} invoices synced, "
        f"{result['subscriptions_synced']} subscriptions synced."
    )


if __name__ == "__main__":
    main()
