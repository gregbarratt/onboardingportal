from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.stripe import process_stripe_webhook_event


router = APIRouter(prefix="/stripe", tags=["Stripe Preparation"])


@router.post("/webhook")
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = await request.body()
    return process_stripe_webhook_event(
        db,
        payload=payload,
        stripe_signature=stripe_signature,
    )
