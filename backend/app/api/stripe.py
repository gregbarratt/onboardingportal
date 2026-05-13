from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.stripe import StripeIntegrationError, process_stripe_webhook_event


router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post("/webhook")
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = await request.body()
    try:
        return process_stripe_webhook_event(
            db,
            payload=payload,
            stripe_signature=stripe_signature,
        )
    except StripeIntegrationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
