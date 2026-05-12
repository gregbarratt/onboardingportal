from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.payment_statuses import (
    DEFAULT_CURRENCY,
    DEFAULT_MEMBERSHIP_PAYMENT_STATUS,
    DEFAULT_MEMBERSHIP_STATUS,
    DEFAULT_PAYMENT_STATUS,
    MEMBERSHIP_STATUSES,
    PAYMENT_STATUSES,
)


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class MembershipUpdate(BaseModel):
    membership_type: str | None = Field(default=None, max_length=100)
    setup_fee_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    monthly_fee_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    membership_status: str | None = None
    payment_status: str | None = None
    payment_method: str | None = Field(default=None, max_length=100)
    stripe_customer_id: str | None = Field(default=None, max_length=255)
    stripe_subscription_id: str | None = Field(default=None, max_length=255)
    last_payment_date: date | None = None
    next_payment_date: date | None = None
    failed_payment_count: int | None = Field(default=None, ge=0)
    access_level: str | None = Field(default=None, max_length=100)
    cancellation_date: date | None = None
    suspension_date: date | None = None
    internal_notes: str | None = None

    @field_validator(
        "membership_type",
        "payment_method",
        "stripe_customer_id",
        "stripe_subscription_id",
        "access_level",
        "internal_notes",
    )
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("membership_status")
    @classmethod
    def membership_status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in MEMBERSHIP_STATUSES:
            raise ValueError("Enter a valid membership status.")
        return cleaned

    @field_validator("payment_status")
    @classmethod
    def payment_status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in PAYMENT_STATUSES:
            raise ValueError("Enter a valid payment status.")
        return cleaned


class MembershipRead(BaseModel):
    id: int
    agent_id: int
    membership_type: str | None = None
    setup_fee_amount: Decimal
    monthly_fee_amount: Decimal
    membership_status: str = DEFAULT_MEMBERSHIP_STATUS
    payment_status: str = DEFAULT_MEMBERSHIP_PAYMENT_STATUS
    payment_method: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    last_payment_date: date | None = None
    next_payment_date: date | None = None
    failed_payment_count: int
    access_level: str | None = None
    cancellation_date: date | None = None
    suspension_date: date | None = None
    internal_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default=DEFAULT_CURRENCY, min_length=3, max_length=3)
    payment_type: str = Field(min_length=1, max_length=100)
    payment_status: str | None = None
    payment_date: date | None = None
    due_date: date | None = None
    stripe_payment_id: str | None = Field(default=None, max_length=255)
    invoice_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def currency_must_be_uppercase(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("payment_type")
    @classmethod
    def payment_type_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Payment type is required.")
        return cleaned

    @field_validator("payment_status")
    @classmethod
    def payment_status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in PAYMENT_STATUSES:
            raise ValueError("Enter a valid payment status.")
        return cleaned

    @field_validator("stripe_payment_id", "invoice_url", "notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class PaymentRead(BaseModel):
    id: int
    agent_id: int
    amount: Decimal
    currency: str
    payment_type: str
    payment_status: str = DEFAULT_PAYMENT_STATUS
    payment_date: date | None = None
    due_date: date | None = None
    stripe_payment_id: str | None = None
    invoice_url: str | None = None
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

