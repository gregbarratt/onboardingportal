from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.onboarding_statuses import DEFAULT_ONBOARDING_STATUS, ONBOARDING_STATUSES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class OnboardingStepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    required: bool = True
    approval_required: bool = False
    sort_order: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Step title is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class OnboardingStepUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    required: bool | None = None
    approval_required: bool | None = None
    sort_order: int | None = Field(default=None, ge=1)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Step title cannot be blank.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class OnboardingStepRead(BaseModel):
    id: int
    sort_order: int
    title: str
    description: str | None = None
    required: bool
    approval_required: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentOnboardingProgressUpdate(BaseModel):
    completion_status: str | None = None
    due_date: date | None = None
    completed_date: date | None = None
    completed_by: int | None = None
    evidence_file_or_link: str | None = Field(default=None, max_length=500)
    admin_notes: str | None = None
    agent_notes: str | None = None

    @field_validator("completion_status")
    @classmethod
    def status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in ONBOARDING_STATUSES:
            raise ValueError("Enter a valid onboarding status.")
        return cleaned

    @field_validator("evidence_file_or_link", "admin_notes", "agent_notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class AgentOnboardingProgressRead(BaseModel):
    id: int
    agent_id: int
    step_id: int
    completion_status: str = DEFAULT_ONBOARDING_STATUS
    due_date: date | None = None
    completed_date: date | None = None
    completed_by: int | None = None
    evidence_file_or_link: str | None = None
    admin_notes: str | None = None
    agent_notes: str | None = None
    approved_by: int | None = None
    approved_date: date | None = None
    created_at: datetime
    updated_at: datetime
    step: OnboardingStepRead

    model_config = ConfigDict(from_attributes=True)


class AdminOnboardingSummaryRead(BaseModel):
    id: int
    agent_id: str
    first_name: str
    last_name: str
    email: str
    business_name: str | None = None
    status: str
    total_steps: int
    complete_steps: int
    awaiting_review: int


class OnboardingApprovalRequest(BaseModel):
    admin_notes: str | None = None

    @field_validator("admin_notes")
    @classmethod
    def admin_notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)
