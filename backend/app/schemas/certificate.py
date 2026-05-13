from datetime import date as date_type, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.certificates import CERTIFICATE_STATUSES, DEFAULT_CERTIFICATE_STATUS


def clean_required_text(value: str) -> str:
    return value.strip()


class CertificateCreate(BaseModel):
    training_module_id: int
    certificate_name: str = Field(min_length=1, max_length=255)
    certificate_url: str = Field(min_length=1, max_length=500)
    issued_date: date_type | None = None
    expiry_date: date_type | None = None
    renewal_required: bool = False

    @field_validator("certificate_name", "certificate_url")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned


class CertificateRead(BaseModel):
    id: int
    agent_id: int
    training_module_id: int
    certificate_name: str
    certificate_url: str
    issued_date: date_type
    expiry_date: date_type | None = None
    renewal_required: bool
    status: str = DEFAULT_CERTIFICATE_STATUS
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in CERTIFICATE_STATUSES:
            raise ValueError("Enter a valid certificate status.")
        return cleaned

    model_config = ConfigDict(from_attributes=True)
