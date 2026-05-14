from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.password_reset import PasswordResetToken
from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hash_reset_token(token: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_password_reset_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"


def create_password_reset_token(db: Session, user: User) -> tuple[PasswordResetToken, str]:
    now = utc_now()

    existing_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    for existing_token in existing_tokens:
        existing_token.used_at = now

    raw_token = secrets.token_urlsafe(40)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now + timedelta(minutes=settings.password_reset_token_expire_minutes),
    )
    db.add(reset_token)
    db.flush()
    return reset_token, raw_token


def password_reset_token_is_valid(reset_token: PasswordResetToken) -> bool:
    if reset_token.used_at is not None:
        return False
    return ensure_utc(reset_token.expires_at) >= utc_now()


def find_valid_password_reset_token(db: Session, raw_token: str) -> PasswordResetToken | None:
    reset_token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_reset_token(raw_token))
    )
    if reset_token is None or not password_reset_token_is_valid(reset_token):
        return None
    return reset_token
