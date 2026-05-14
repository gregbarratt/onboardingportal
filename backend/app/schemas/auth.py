from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalise_email(value: str) -> str:
    return value.strip().lower()


class RegisterUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str) -> str:
        value = normalise_email(value)
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return value


class AgentRegistrationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=50)
    business_name: str | None = Field(default=None, max_length=255)
    address: str = Field(min_length=1)
    postcode: str = Field(min_length=1, max_length=20)
    accepted_terms: bool = False

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str) -> str:
        value = normalise_email(value)
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("first_name", "last_name", "phone", "address", "postcode")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("business_name")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("accepted_terms")
    @classmethod
    def terms_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the membership terms before continuing.")
        return value


class AgentRegistrationResponse(BaseModel):
    agent_profile_id: int
    checkout_session_id: str
    checkout_url: str
    message: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return normalise_email(value)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        value = normalise_email(value)
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return value


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_url: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PasswordResetConfirmResponse(BaseModel):
    message: str


class PasswordResetLinkResponse(BaseModel):
    user_id: int
    email: str
    reset_url: str
    expires_at: datetime


class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserOrganizationRead(BaseModel):
    id: int
    name: str
    slug: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: int
    email: str
    is_active: bool
    role: RoleRead
    organization_id: int | None = None
    organization: UserOrganizationRead | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
