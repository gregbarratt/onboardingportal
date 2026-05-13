from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.audit import AUDIT_ACTION_TYPES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class AuditLogRead(BaseModel):
    id: int
    user_id: int | None = None
    agent_id: int | None = None
    action_type: str
    description: str
    previous_value: str | None = None
    new_value: str | None = None
    ip_address: str | None = None
    created_date: datetime
    created_by: int | None = None

    @field_validator("action_type")
    @classmethod
    def action_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in AUDIT_ACTION_TYPES:
            raise ValueError("Enter a valid audit action type.")
        return cleaned

    model_config = ConfigDict(from_attributes=True)


class AdminNoteCreate(BaseModel):
    note: str = Field(min_length=1)

    @field_validator("note")
    @classmethod
    def note_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned


class AdminNoteRead(BaseModel):
    id: int
    agent_id: int
    note: str
    created_by: int
    created_date: datetime
    updated_date: datetime

    model_config = ConfigDict(from_attributes=True)
