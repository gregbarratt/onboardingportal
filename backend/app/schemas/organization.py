from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.organizations import slugify_organization_name


class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    status: str = Field(default="Active", max_length=50)
    contact_email: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator("name", "status")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("slug")
    @classmethod
    def slug_can_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = slugify_organization_name(value)
        return cleaned or None

    @field_validator("contact_email")
    @classmethod
    def optional_email_must_look_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator("name", "status")
    @classmethod
    def optional_required_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return cleaned

    @field_validator("slug")
    @classmethod
    def slug_can_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return slugify_organization_name(value)

    @field_validator("contact_email")
    @classmethod
    def optional_email_must_look_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def notes_can_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class OrganizationRead(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    contact_email: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
