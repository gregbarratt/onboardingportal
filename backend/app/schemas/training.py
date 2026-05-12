from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.training import (
    DEFAULT_TRAINING_PROGRESS_STATUS,
    DEFAULT_TRAINING_PUBLISHED_STATUS,
    DEFAULT_TRAINING_TRACK,
    TRAINING_PROGRESS_STATUSES,
    TRAINING_PUBLISHED_STATUSES,
    TRAINING_TRACKS,
)


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class TrainingCategoryRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TrainingModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: int
    level: str | None = Field(default=None, max_length=100)
    mandatory: bool = False
    estimated_completion_time: str | None = Field(default=None, max_length=100)
    content_type: str | None = Field(default=None, max_length=100)
    content_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    pdf_url: str | None = Field(default=None, max_length=500)
    text_content: str | None = None
    quiz_required: bool = False
    pass_mark: int | None = Field(default=None, ge=0, le=100)
    certificate_issued: bool = False
    renewal_required: bool = False
    renewal_period_months: int | None = Field(default=None, ge=1)
    expiry_date: date | None = None
    training_track: str = DEFAULT_TRAINING_TRACK
    published_status: str = DEFAULT_TRAINING_PUBLISHED_STATUS

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Training module title is required.")
        return cleaned

    @field_validator(
        "description",
        "level",
        "estimated_completion_time",
        "content_type",
        "content_url",
        "video_url",
        "pdf_url",
        "text_content",
    )
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("published_status")
    @classmethod
    def published_status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in TRAINING_PUBLISHED_STATUSES:
            raise ValueError("Enter a valid published status.")
        return cleaned

    @field_validator("training_track")
    @classmethod
    def training_track_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in TRAINING_TRACKS:
            raise ValueError("Enter a valid training track.")
        return cleaned


class TrainingModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: int | None = None
    level: str | None = Field(default=None, max_length=100)
    mandatory: bool | None = None
    estimated_completion_time: str | None = Field(default=None, max_length=100)
    content_type: str | None = Field(default=None, max_length=100)
    content_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    pdf_url: str | None = Field(default=None, max_length=500)
    text_content: str | None = None
    quiz_required: bool | None = None
    pass_mark: int | None = Field(default=None, ge=0, le=100)
    certificate_issued: bool | None = None
    renewal_required: bool | None = None
    renewal_period_months: int | None = Field(default=None, ge=1)
    expiry_date: date | None = None
    training_track: str | None = None
    published_status: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Training module title cannot be blank.")
        return cleaned

    @field_validator(
        "description",
        "level",
        "estimated_completion_time",
        "content_type",
        "content_url",
        "video_url",
        "pdf_url",
        "text_content",
    )
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("published_status")
    @classmethod
    def published_status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in TRAINING_PUBLISHED_STATUSES:
            raise ValueError("Enter a valid published status.")
        return cleaned

    @field_validator("training_track")
    @classmethod
    def training_track_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in TRAINING_TRACKS:
            raise ValueError("Enter a valid training track.")
        return cleaned


class TrainingModuleRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    category_id: int
    category: TrainingCategoryRead
    level: str | None = None
    mandatory: bool
    estimated_completion_time: str | None = None
    content_type: str | None = None
    content_url: str | None = None
    video_url: str | None = None
    pdf_url: str | None = None
    text_content: str | None = None
    quiz_required: bool
    pass_mark: int | None = None
    certificate_issued: bool
    renewal_required: bool
    renewal_period_months: int | None = None
    expiry_date: date | None = None
    training_track: str = DEFAULT_TRAINING_TRACK
    published_status: str = DEFAULT_TRAINING_PUBLISHED_STATUS
    created_by: int | None = None
    created_date: datetime
    updated_date: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingAssignRequest(BaseModel):
    agent_id: int
    due_date: date | None = None
    mandatory: bool | None = None
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class AgentTrainingProgressUpdate(BaseModel):
    progress_status: str | None = None
    started_date: date | None = None
    completed_date: date | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    passed: bool | None = None
    certificate_issued: bool | None = None
    expiry_date: date | None = None
    notes: str | None = None

    @field_validator("progress_status")
    @classmethod
    def progress_status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in TRAINING_PROGRESS_STATUSES:
            raise ValueError("Enter a valid training progress status.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class TrainingAssignmentRead(BaseModel):
    id: int
    agent_id: int
    training_module_id: int
    assigned_by: int | None = None
    assigned_date: datetime
    due_date: date | None = None
    mandatory: bool
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AgentTrainingProgressRead(BaseModel):
    id: int
    assignment_id: int
    agent_id: int
    training_module_id: int
    progress_status: str = DEFAULT_TRAINING_PROGRESS_STATUS
    started_date: date | None = None
    completed_date: date | None = None
    score: int | None = None
    passed: bool | None = None
    certificate_issued: bool
    expiry_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    training_module: TrainingModuleRead
    assignment: TrainingAssignmentRead

    model_config = ConfigDict(from_attributes=True)
