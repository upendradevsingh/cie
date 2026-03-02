"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Shared fields for user representations."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full display name",
    )
    role: str = Field(
        default="agent",
        description="User role: admin, team_lead, or agent",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "team_lead", "agent"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}, got '{v}'")
        return v


class UserCreate(UserBase):
    """Payload for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )


class UserUpdate(BaseModel):
    """Payload for partially updating a user. All fields optional."""

    full_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name",
    )
    role: Optional[str] = Field(default=None, description="Updated role")
    is_active: Optional[bool] = Field(default=None, description="Enable / disable user")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"admin", "team_lead", "agent"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}, got '{v}'")
        return v


class UserResponse(UserBase):
    """User representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
