from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.notifications import NOTIFICATION_TYPES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class NotificationCreate(BaseModel):
    recipient_user_id: int
    agent_id: int | None = None
    notification_type: str
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    link_url: str | None = Field(default=None, max_length=500)

    @field_validator("notification_type")
    @classmethod
    def notification_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in NOTIFICATION_TYPES:
            raise ValueError("Enter a valid notification type.")
        return cleaned

    @field_validator("title", "message")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("link_url")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class NotificationRead(BaseModel):
    id: int
    recipient_user_id: int
    agent_id: int | None = None
    notification_type: str
    title: str
    message: str
    link_url: str | None = None
    read: bool
    read_date: datetime | None = None
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
