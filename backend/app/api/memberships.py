from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.payment_statuses import (
    DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
    DEFAULT_MEMBERSHIP_STATUS,
    DEFAULT_PAYMENT_STATUS,
)
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.membership import Membership
from app.models.payment import Payment
from app.models.user import User
from app.schemas.membership import (
    MembershipRead,
    MembershipUpdate,
    PaymentCreate,
    PaymentRead,
    StripeBillingPortalSessionRead,
    StripeCustomerCandidateRead,
    StripeCustomerLinkRequest,
    StripeInvoiceRead,
    StripeInvoiceSyncResponse,
    StripeSubscriptionRead,
    StripeSubscriptionSyncResponse,
)
from app.services.audit import create_audit_log
from app.services.stripe import (
    StripeIntegrationError,
    create_billing_portal_session,
    create_stripe_customer,
    list_stripe_invoices,
    list_stripe_subscriptions,
    mark_stripe_sync_failed,
    mark_stripe_sync_success,
    retrieve_stripe_customer,
    search_stripe_customers_for_agent,
    sync_stripe_invoices_for_membership,
    sync_stripe_subscription_for_membership,
)


router = APIRouter(prefix="/agents", tags=["Memberships and Payments"])


def get_membership_for_agent(db: Session, agent_profile_id: int) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.agent_id == agent_profile_id))


def get_membership_or_404(db: Session, agent_profile_id: int) -> Membership:
    membership = get_membership_for_agent(db, agent_profile_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership record not found for this agent.",
        )
    return membership


def get_or_create_membership_for_agent(db: Session, agent_profile: AgentProfile) -> Membership:
    membership = get_membership_for_agent(db, agent_profile.id)
    if membership is not None:
        return membership

    membership = Membership(
        agent_id=agent_profile.id,
        setup_fee_amount=Decimal("0.00"),
        monthly_fee_amount=Decimal("0.00"),
        membership_status=DEFAULT_MEMBERSHIP_STATUS,
        payment_status=DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
        failed_payment_count=0,
    )
    db.add(membership)
    db.flush()
    return membership


def value_as_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def add_membership_change_audit_logs(
    db: Session,
    *,
    agent_profile: AgentProfile,
    current_user: User,
    previous_membership_status: str | None,
    previous_payment_status: str | None,
    previous_access_level: str | None,
    membership: Membership,
) -> None:
    if previous_membership_status != membership.membership_status:
        create_audit_log(
            db,
            action_type="Membership status changed",
            description=f"Membership status changed for {agent_profile.first_name} {agent_profile.last_name}.",
            previous_value=value_as_text(previous_membership_status),
            new_value=value_as_text(membership.membership_status),
            created_by=current_user.id,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )

    if previous_payment_status != membership.payment_status:
        create_audit_log(
            db,
            action_type="Payment status changed",
            description=f"Membership payment status changed for {agent_profile.first_name} {agent_profile.last_name}.",
            previous_value=value_as_text(previous_payment_status),
            new_value=value_as_text(membership.payment_status),
            created_by=current_user.id,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )

    if previous_access_level != membership.access_level:
        create_audit_log(
            db,
            action_type="Access level changed",
            description=f"Membership access level changed for {agent_profile.first_name} {agent_profile.last_name}.",
            previous_value=value_as_text(previous_access_level),
            new_value=value_as_text(membership.access_level),
            created_by=current_user.id,
            user_id=agent_profile.user_id,
            agent_id=agent_profile.id,
        )


@router.get("/{agent_profile_id}/membership", response_model=MembershipRead)
def get_agent_membership(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return get_membership_or_404(db, agent_profile.id)


@router.put("/{agent_profile_id}/membership", response_model=MembershipRead)
def update_agent_membership(
    agent_profile_id: int,
    request: MembershipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update membership and payment status.",
        )

    membership = get_membership_for_agent(db, agent_profile.id)
    if membership is None:
        membership = get_or_create_membership_for_agent(db, agent_profile)

    previous_membership_status = membership.membership_status
    previous_payment_status = membership.payment_status
    previous_access_level = membership.access_level

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(membership, field, value)

    add_membership_change_audit_logs(
        db,
        agent_profile=agent_profile,
        current_user=current_user,
        previous_membership_status=previous_membership_status,
        previous_payment_status=previous_payment_status,
        previous_access_level=previous_access_level,
        membership=membership,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Membership record could not be saved because it conflicts with an existing record.",
        ) from None

    db.refresh(membership)
    return membership


@router.post("/{agent_profile_id}/stripe/customer", response_model=MembershipRead)
def create_or_link_stripe_customer(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can connect an agent to Stripe.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_or_create_membership_for_agent(db, agent_profile)
    if membership.stripe_customer_id:
        return membership

    try:
        customer = create_stripe_customer(agent_profile)
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stripe_customer_id = customer.get("id")
    if not stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe did not return a customer ID.",
        )

    membership.stripe_customer_id = stripe_customer_id
    membership.payment_method = membership.payment_method or "Stripe"
    create_audit_log(
        db,
        action_type="Payment setup completed",
        description=f"Stripe customer created for {agent_profile.first_name} {agent_profile.last_name}.",
        previous_value=None,
        new_value=value_as_text(membership.stripe_customer_id),
        created_by=current_user.id,
        user_id=agent_profile.user_id,
        agent_id=agent_profile.id,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe customer could not be saved because it conflicts with an existing record.",
        ) from None

    db.refresh(membership)
    return membership


@router.post("/{agent_profile_id}/stripe/billing-portal", response_model=StripeBillingPortalSessionRead)
def create_agent_billing_portal_session(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_membership_or_404(db, agent_profile.id)
    if not membership.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This agent is not linked to a Stripe customer yet.",
        )

    return_path = f"/admin/agents/{agent_profile.id}/membership" if is_admin_user(current_user) else "/membership"

    try:
        session = create_billing_portal_session(
            membership.stripe_customer_id,
            return_path=return_path,
        )
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    portal_url = session.get("url")
    if not portal_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe did not return a billing portal link.",
        )

    return {
        "stripe_customer_id": membership.stripe_customer_id,
        "session_id": session.get("id"),
        "url": portal_url,
    }


@router.get("/{agent_profile_id}/stripe/customers/search", response_model=list[StripeCustomerCandidateRead])
def search_agent_stripe_customers(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can search Stripe customers.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    try:
        return search_stripe_customers_for_agent(agent_profile)
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{agent_profile_id}/stripe/customer/link", response_model=MembershipRead)
def link_existing_stripe_customer(
    agent_profile_id: int,
    request: StripeCustomerLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can link an agent to Stripe.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_or_create_membership_for_agent(db, agent_profile)

    existing_membership = db.scalar(
        select(Membership).where(
            Membership.stripe_customer_id == request.stripe_customer_id,
            Membership.agent_id != agent_profile.id,
        )
    )
    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Stripe customer is already linked to another agent.",
        )

    try:
        customer = retrieve_stripe_customer(request.stripe_customer_id)
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stripe_customer_id = customer.get("id")
    if stripe_customer_id != request.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe did not return the expected customer record.",
        )

    previous_customer_id = membership.stripe_customer_id
    membership.stripe_customer_id = request.stripe_customer_id
    membership.payment_method = membership.payment_method or "Stripe"
    create_audit_log(
        db,
        action_type="Payment setup completed",
        description=f"Existing Stripe customer linked for {agent_profile.first_name} {agent_profile.last_name}.",
        previous_value=value_as_text(previous_customer_id),
        new_value=value_as_text(membership.stripe_customer_id),
        created_by=current_user.id,
        user_id=agent_profile.user_id,
        agent_id=agent_profile.id,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe customer could not be linked because it conflicts with an existing record.",
        ) from None

    db.refresh(membership)
    return membership


@router.get("/{agent_profile_id}/stripe/invoices", response_model=list[StripeInvoiceRead])
def list_agent_stripe_invoices(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_membership_or_404(db, agent_profile.id)
    if not membership.stripe_customer_id:
        return []

    try:
        return list_stripe_invoices(membership.stripe_customer_id)
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{agent_profile_id}/stripe/invoices/sync", response_model=StripeInvoiceSyncResponse)
def sync_agent_stripe_invoices(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can sync Stripe invoices.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_membership_or_404(db, agent_profile.id)
    if not membership.stripe_customer_id:
        return {"synced_count": 0, "invoices": []}

    membership_id = membership.id
    try:
        invoices = sync_stripe_invoices_for_membership(
            db,
            agent_profile=agent_profile,
            membership=membership,
            current_user=current_user,
        )
        mark_stripe_sync_success(membership)
    except StripeIntegrationError as exc:
        db.rollback()
        failed_membership = db.get(Membership, membership_id)
        if failed_membership is not None:
            mark_stripe_sync_failed(failed_membership, exc)
            db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return {"synced_count": len(invoices), "invoices": invoices}


@router.get("/{agent_profile_id}/stripe/subscriptions", response_model=list[StripeSubscriptionRead])
def list_agent_stripe_subscriptions(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_membership_or_404(db, agent_profile.id)
    if not membership.stripe_customer_id:
        return []

    try:
        return list_stripe_subscriptions(membership.stripe_customer_id)
    except StripeIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{agent_profile_id}/stripe/subscriptions/sync", response_model=StripeSubscriptionSyncResponse)
def sync_agent_stripe_subscription(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can sync Stripe subscriptions.",
        )

    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    membership = get_membership_or_404(db, agent_profile.id)
    if not membership.stripe_customer_id:
        return {"synced": False, "subscription": None}

    membership_id = membership.id
    try:
        subscription = sync_stripe_subscription_for_membership(
            db,
            agent_profile=agent_profile,
            membership=membership,
            current_user=current_user,
        )
        mark_stripe_sync_success(membership)
    except StripeIntegrationError as exc:
        db.rollback()
        failed_membership = db.get(Membership, membership_id)
        if failed_membership is not None:
            mark_stripe_sync_failed(failed_membership, exc)
            db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return {"synced": subscription is not None, "subscription": subscription}


@router.post("/{agent_profile_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_agent_payment(
    agent_profile_id: int,
    request: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Payment:
    agent_profile: AgentProfile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create payment records.",
        )

    payment = Payment(
        agent_id=agent_profile.id,
        amount=request.amount,
        currency=request.currency,
        payment_type=request.payment_type,
        payment_status=request.payment_status or DEFAULT_PAYMENT_STATUS,
        payment_date=request.payment_date,
        due_date=request.due_date,
        stripe_payment_id=request.stripe_payment_id,
        invoice_url=request.invoice_url,
        notes=request.notes,
    )
    db.add(payment)
    create_audit_log(
        db,
        action_type="Payment status changed",
        description=f"Payment record created for {agent_profile.first_name} {agent_profile.last_name}.",
        previous_value=None,
        new_value=value_as_text(payment.payment_status),
        created_by=current_user.id,
        user_id=agent_profile.user_id,
        agent_id=agent_profile.id,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment record could not be created because it conflicts with an existing record.",
        ) from None

    db.refresh(payment)
    return payment


@router.get("/{agent_profile_id}/payments", response_model=list[PaymentRead])
def list_agent_payments(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Payment]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.agent_id == agent_profile.id)
            .order_by(Payment.id)
        )
    )
