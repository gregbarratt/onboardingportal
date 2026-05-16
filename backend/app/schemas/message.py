from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.messages import MESSAGE_TICKET_STATUSES


def clean_required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("This field is required.")
    return cleaned


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)

    @field_validator("subject", "message")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        return clean_required_text(value)


class SupportTicketReplyCreate(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        return clean_required_text(value)


class SupportTicketStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in MESSAGE_TICKET_STATUSES:
            raise ValueError("Enter a valid ticket status.")
        return cleaned


class SupportTicketMessageRead(BaseModel):
    id: int
    ticket_id: int
    sender_user_id: int
    sender_email: str
    sender_role: str
    message: str
    internal_note: bool
    created_at: datetime


class SupportTicketRead(BaseModel):
    id: int
    organization_id: int | None
    agent_id: int | None
    agent_name: str
    agent_email: str
    created_by_user_id: int
    subject: str
    status: str
    message_count: int
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    messages: list[SupportTicketMessageRead]

    model_config = ConfigDict(from_attributes=True)
