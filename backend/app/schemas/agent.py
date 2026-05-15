from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.agent_statuses import AGENT_STATUSES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


def business_name_or_default(value: str | None) -> str:
    cleaned = clean_optional_text(value)
    return cleaned or "N/A"


class AgentProfileBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    personal_email: str | None = Field(default=None, min_length=3, max_length=255)
    company_email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    business_name: str | None = Field(default="N/A", max_length=255)
    joining_date: date | None = None
    address: str | None = None
    postcode: str | None = Field(default=None, max_length=20)
    commission_bank_name: str | None = Field(default=None, max_length=255)
    commission_account_name: str | None = Field(default=None, max_length=255)
    commission_sort_code: str | None = Field(default=None, max_length=20)
    commission_account_number: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("personal_email", "company_email")
    @classmethod
    def optional_email_must_look_valid(cls, value: str | None) -> str | None:
        cleaned = clean_optional_text(value)
        if cleaned is None:
            return None
        cleaned = cleaned.lower()
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator(
        "phone",
        "address",
        "postcode",
        "commission_bank_name",
        "commission_account_name",
        "commission_sort_code",
        "commission_account_number",
    )
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("business_name")
    @classmethod
    def business_name_defaults_to_na(cls, value: str | None) -> str:
        return business_name_or_default(value)


class AgentProfileCreate(AgentProfileBase):
    user_id: int | None = None
    organization_id: int | None = None
    agent_id: str | None = Field(default=None, max_length=50)
    status: str | None = None
    portal_access_enabled: bool | None = None

    @field_validator("agent_id")
    @classmethod
    def agent_id_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned not in AGENT_STATUSES:
            raise ValueError("Enter a valid agent status.")
        return cleaned


class ManualAgentCreate(AgentProfileBase):
    organization_id: int | None = None
    agent_id: str | None = Field(default=None, max_length=50)
    status: str | None = "Registered"
    portal_access_enabled: bool = True
    send_password_reset_email: bool = True

    @field_validator("agent_id")
    @classmethod
    def agent_id_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned not in AGENT_STATUSES:
            raise ValueError("Enter a valid agent status.")
        return cleaned


class AgentProfileUpdate(BaseModel):
    organization_id: int | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    personal_email: str | None = Field(default=None, min_length=3, max_length=255)
    company_email: str | None = Field(default=None, min_length=3, max_length=255)
    portal_access_enabled: bool | None = None
    phone: str | None = Field(default=None, max_length=50)
    business_name: str | None = Field(default="N/A", max_length=255)
    status: str | None = None
    joining_date: date | None = None
    address: str | None = None
    postcode: str | None = Field(default=None, max_length=20)
    commission_bank_name: str | None = Field(default=None, max_length=255)
    commission_account_name: str | None = Field(default=None, max_length=255)
    commission_sort_code: str | None = Field(default=None, max_length=20)
    commission_account_number: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return cleaned

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("personal_email", "company_email")
    @classmethod
    def optional_email_must_look_valid(cls, value: str | None) -> str | None:
        cleaned = clean_optional_text(value)
        if cleaned is None:
            return None
        cleaned = cleaned.lower()
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned not in AGENT_STATUSES:
            raise ValueError("Enter a valid agent status.")
        return cleaned

    @field_validator(
        "phone",
        "address",
        "postcode",
        "commission_bank_name",
        "commission_account_name",
        "commission_sort_code",
        "commission_account_number",
    )
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("business_name")
    @classmethod
    def business_name_defaults_to_na(cls, value: str | None) -> str:
        return business_name_or_default(value)


class AgentProfileRead(AgentProfileBase):
    id: int
    user_id: int
    organization_id: int | None = None
    agent_id: str
    status: str
    portal_access_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualAgentCreateResponse(BaseModel):
    agent: AgentProfileRead
    password_reset_email_sent: bool
    password_reset_error: str | None = None
    message: str


class AgentCsvImportRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_content_base64: str = Field(min_length=1)
    update_existing: bool = True
    sync_stripe_after_import: bool = False


class AgentCsvImportError(BaseModel):
    row_number: int
    identifier: str | None = None
    message: str


class AgentCsvImportResponse(BaseModel):
    total_rows: int
    created: int
    updated: int
    skipped: int
    stripe_sync_queued: int = 0
    stripe_sync_agent_ids: list[int] = Field(default_factory=list)
    stripe_synced: int = 0
    stripe_sync_failed: int = 0
    stripe_profiles_synced: int = 0
    stripe_profile_fields_synced: int = 0
    stripe_invoices_synced: int = 0
    stripe_subscriptions_synced: int = 0
    errors: list[AgentCsvImportError]
    next_agent_id: str


class AgentStripeSyncBatchRequest(BaseModel):
    agent_profile_ids: list[int] = Field(default_factory=list)
    after_agent_id: int | None = None
    limit: int = Field(default=1, ge=1, le=5)


class AgentStripeSyncBatchError(BaseModel):
    agent_id: int
    identifier: str | None = None
    message: str


class AgentStripeSyncBatchResponse(BaseModel):
    processed: int
    stripe_synced: int = 0
    stripe_sync_failed: int = 0
    stripe_profiles_synced: int = 0
    stripe_profile_fields_synced: int = 0
    stripe_invoices_synced: int = 0
    stripe_subscriptions_synced: int = 0
    next_after_agent_id: int | None = None
    has_more: bool
    done: bool
    errors: list[AgentStripeSyncBatchError] = Field(default_factory=list)


class BulkAgentAccessTrainingResponse(BaseModel):
    message: str
    users_checked: int
    users_activated: int
    agents_checked: int
    portal_access_enabled: int
    onboarding_modules_found: int
    onboarding_training_completed: int


class FinalApprovalRequirementRead(BaseModel):
    key: str
    label: str
    complete: bool
    detail: str | None = None


class FinalApprovalStatusRead(BaseModel):
    agent_id: int
    agent_name: str
    current_status: str
    ready_for_approval: bool
    approved_to_trade: bool
    tracking_exempt: bool = False
    missing_requirements: list[str]
    requirements: list[FinalApprovalRequirementRead]
