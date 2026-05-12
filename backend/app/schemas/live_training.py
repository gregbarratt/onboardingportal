from datetime import date as date_type, datetime, time as time_type

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.live_training import ATTENDANCE_STATUSES, DEFAULT_ATTENDANCE_STATUS, LIVE_SESSION_TYPES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class LiveTrainingSessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    session_type: str
    description: str | None = None
    date: date_type
    start_time: time_type | None = None
    end_time: time_type | None = None
    trainer_host: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)
    recording_link: str | None = Field(default=None, max_length=500)
    attendance_required: bool = True
    related_training_module_id: int | None = None
    follow_up_quiz_required: bool = False
    certificate_issued: bool = False
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Live session title is required.")
        return cleaned

    @field_validator("session_type")
    @classmethod
    def session_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in LIVE_SESSION_TYPES:
            raise ValueError("Enter a valid live session type.")
        return cleaned

    @field_validator("description", "trainer_host", "meeting_link", "recording_link", "notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class LiveTrainingSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    session_type: str | None = None
    description: str | None = None
    date: date_type | None = None
    start_time: time_type | None = None
    end_time: time_type | None = None
    trainer_host: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)
    recording_link: str | None = Field(default=None, max_length=500)
    attendance_required: bool | None = None
    related_training_module_id: int | None = None
    follow_up_quiz_required: bool | None = None
    certificate_issued: bool | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("Live session title cannot be blank.")
        return cleaned

    @field_validator("session_type")
    @classmethod
    def session_type_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if cleaned not in LIVE_SESSION_TYPES:
            raise ValueError("Enter a valid live session type.")
        return cleaned

    @field_validator("description", "trainer_host", "meeting_link", "recording_link", "notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class LiveTrainingSessionRead(BaseModel):
    id: int
    title: str
    session_type: str
    description: str | None = None
    date: date_type
    start_time: time_type | None = None
    end_time: time_type | None = None
    trainer_host: str | None = None
    meeting_link: str | None = None
    recording_link: str | None = None
    attendance_required: bool
    related_training_module_id: int | None = None
    follow_up_quiz_required: bool
    certificate_issued: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LiveSessionAssignRequest(BaseModel):
    agent_id: int
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class AttendanceLogCreate(BaseModel):
    agent_id: int
    attendance_status: str = DEFAULT_ATTENDANCE_STATUS
    join_time: time_type | None = None
    leave_time: time_type | None = None
    duration_attended: int | None = Field(default=None, ge=0)
    marked_date: date_type | None = None
    notes: str | None = None
    follow_up_required: bool = False
    watched_recording: bool = False
    recording_completed_date: date_type | None = None

    @field_validator("attendance_status")
    @classmethod
    def attendance_status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in ATTENDANCE_STATUSES:
            raise ValueError("Enter a valid attendance status.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class AttendanceBulkRequest(BaseModel):
    items: list[AttendanceLogCreate] = Field(min_length=1)


class AttendanceLogRead(BaseModel):
    id: int
    session_id: int
    agent_id: int
    attendance_status: str
    join_time: time_type | None = None
    leave_time: time_type | None = None
    duration_attended: int | None = None
    marked_by: int | None = None
    marked_date: date_type | None = None
    notes: str | None = None
    follow_up_required: bool
    watched_recording: bool
    recording_completed_date: date_type | None = None
    created_at: datetime
    updated_at: datetime
    session: LiveTrainingSessionRead

    model_config = ConfigDict(from_attributes=True)
