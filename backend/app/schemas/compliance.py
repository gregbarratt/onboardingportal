from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.compliance import (
    COMPLIANCE_POLICY_STATUSES,
    COMPLIANCE_POLICY_TYPES,
    DEFAULT_COMPLIANCE_POLICY_STATUS,
    DEFAULT_COMPLIANCE_POLICY_VERSION,
)


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class CompliancePolicyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    policy_type: str
    content: str = Field(min_length=1)
    version: str = Field(default=DEFAULT_COMPLIANCE_POLICY_VERSION, min_length=1, max_length=50)
    requires_acceptance: bool = True
    published_status: str = DEFAULT_COMPLIANCE_POLICY_STATUS

    @field_validator("title", "content", "version")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("policy_type")
    @classmethod
    def policy_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in COMPLIANCE_POLICY_TYPES:
            raise ValueError("Enter a valid compliance policy type.")
        return cleaned

    @field_validator("published_status")
    @classmethod
    def published_status_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in COMPLIANCE_POLICY_STATUSES:
            raise ValueError("Enter a valid policy status.")
        return cleaned


class CompliancePolicyRead(BaseModel):
    id: int
    title: str
    policy_type: str
    content: str
    version: str
    requires_acceptance: bool
    published_status: str
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyAcceptanceRequest(BaseModel):
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class PolicyAcceptanceRead(BaseModel):
    id: int
    policy_id: int
    agent_id: int
    accepted_by: int
    accepted_date: datetime
    policy_version: str
    ip_address: str | None = None
    user_agent: str | None = None
    acceptance_statement: str | None = None
    notes: str | None = None
    agent_name: str | None = None
    accepted_by_email: str | None = None
    policy: CompliancePolicyRead

    model_config = ConfigDict(from_attributes=True)


class ComplianceAgentIssue(BaseModel):
    agent_id: int
    agent_name: str
    status: str
    issues: list[str]


class AgentComplianceStatusRead(BaseModel):
    agent_id: int
    agent_name: str
    agent_status: str
    compliance_hold: bool
    required_policy_count: int
    accepted_policy_count: int
    accepted_policy_ids: list[int]
    missing_policy_titles: list[str]
    accepted_policy_titles: list[str]
    missing_document_types: list[str]
    documents_awaiting_review: list[str]
    rejected_documents: list[str]
    expired_compliance_training: list[str]
    missing_compliance_training: list[str]
    compliance_checklist: list[str]
    customer_money_handling_rules: list[str]
    advertising_and_social_media_rules: list[str]
    complaints_process: list[str]


class AdminComplianceDashboardRead(BaseModel):
    total_agents: int
    agents_on_compliance_hold: int
    documents_awaiting_review: int
    policy_acceptance_count: int
    missing_document_agents: list[ComplianceAgentIssue]
    expired_compliance_training_agents: list[ComplianceAgentIssue]
    compliance_hold_agents: list[ComplianceAgentIssue]
    recent_policy_acceptances: list[PolicyAcceptanceRead]
