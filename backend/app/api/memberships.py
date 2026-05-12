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

    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update membership and payment status.",
        )

    membership = get_membership_for_agent(db, agent_profile.id)
    if membership is None:
        membership = Membership(
            agent_id=agent_profile.id,
            setup_fee_amount=Decimal("0.00"),
            monthly_fee_amount=Decimal("0.00"),
            membership_status=DEFAULT_MEMBERSHIP_STATUS,
            payment_status=DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
            failed_payment_count=0,
        )
        db.add(membership)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(membership, field, value)

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


@router.post("/{agent_profile_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_agent_payment(
    agent_profile_id: int,
    request: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Payment:
    agent_profile: AgentProfile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    admin_user = is_admin_user(current_user)
    if not admin_user and request.payment_status is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can set payment status.",
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

