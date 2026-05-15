from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.resources import MARKETING_ASSET_TYPES, SUPPLIER_TYPES


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_required_text(value: str) -> str:
    return value.strip()


class SupplierAccessCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_type: str
    portal_url: str | None = Field(default=None, max_length=500)
    login_instructions: str | None = None
    access_notes: str | None = None
    training_required: bool = False
    related_training_module: int | None = None
    visible_to_agents: bool = True

    @field_validator("supplier_name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("supplier_type")
    @classmethod
    def supplier_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in SUPPLIER_TYPES:
            raise ValueError("Enter a valid supplier type.")
        return cleaned

    @field_validator("portal_url", "login_instructions", "access_notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class SupplierAccessUpdate(SupplierAccessCreate):
    pass


class SupplierAccessRead(BaseModel):
    id: int
    supplier_name: str
    supplier_type: str
    portal_url: str | None = None
    login_instructions: str | None = None
    access_notes: str | None = None
    training_required: bool
    related_training_module: int | None = None
    visible_to_agents: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketingAssetCreate(BaseModel):
    asset_name: str = Field(min_length=1, max_length=255)
    asset_type: str
    description: str | None = None
    file_url: str | None = Field(default=None, max_length=500)
    resource_url: str | None = Field(default=None, max_length=500)
    approved_offer_wording: str | None = None
    access_notes: str | None = None
    visible_to_agents: bool = True

    @field_validator("asset_name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("asset_type")
    @classmethod
    def asset_type_must_be_allowed(cls, value: str) -> str:
        cleaned = clean_required_text(value)
        if cleaned not in MARKETING_ASSET_TYPES:
            raise ValueError("Enter a valid marketing asset type.")
        return cleaned

    @field_validator("description", "file_url", "resource_url", "approved_offer_wording", "access_notes")
    @classmethod
    def optional_text_can_be_blank(cls, value: str | None) -> str | None:
        return clean_optional_text(value)


class MarketingAssetRead(BaseModel):
    id: int
    asset_name: str
    asset_type: str
    description: str | None = None
    file_url: str | None = None
    resource_url: str | None = None
    approved_offer_wording: str | None = None
    access_notes: str | None = None
    visible_to_agents: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
