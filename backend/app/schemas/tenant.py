"""Tenant (organization) schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantCreate(BaseModel):
    """Payload for registering a new tenant."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization / company name",
    )
    slug: str = Field(
        ...,
        min_length=2,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe slug (lowercase alphanumeric + hyphens)",
    )


class TenantUpdate(BaseModel):
    """Partial update for a tenant."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated organization name",
    )
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tenant-level settings (JSON object)",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable / disable the tenant",
    )


class TenantResponse(BaseModel):
    """Tenant representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
