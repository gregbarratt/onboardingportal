from datetime import date as date_type, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.documents import DEFAULT_DOCUMENT_STATUS, DOCUMENT_STATUSES, DOCUMENT_TYPES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class DocumentCreate(BaseModel):
    document_type: str
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str = Field(min_length=1, max_length=500)
    requires_signature: bool = False
    signed: bool = False
    signed_date: date_type | None = None
    expiry_date: date_type | None = None
    notes: str | None = None

    @field_validator("document_type")
    @classmethod
    def document_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in DOCUMENT_TYPES:
            raise ValueError("Enter a valid document type.")
        return cleaned

    @field_validator("file_name", "file_url")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class DocumentReviewRequest(BaseModel):
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class DocumentRead(BaseModel):
    id: int
    agent_id: int
    document_type: str
    file_name: str
    file_url: str
    uploaded_by: int
    uploaded_date: date_type
    requires_signature: bool
    signed: bool
    signed_date: date_type | None = None
    verified: bool
    verified_by: int | None = None
    verified_date: date_type | None = None
    expiry_date: date_type | None = None
    status: str = DEFAULT_DOCUMENT_STATUS
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in DOCUMENT_STATUSES:
            raise ValueError("Enter a valid document status.")
        return cleaned

    model_config = ConfigDict(from_attributes=True)
