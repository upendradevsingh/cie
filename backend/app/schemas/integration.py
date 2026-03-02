"""Integration and API key schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Integrations (CRM / webhook config)
# ---------------------------------------------------------------------------


class IntegrationCreate(BaseModel):
    """Payload for registering a new integration."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Friendly name (e.g. 'Salesforce Prod')",
    )
    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Integration type (e.g. 'crm_webhook', 'dialer', 'email')",
    )
    config: Dict[str, Any] = Field(
        ...,
        description=(
            "Integration-specific configuration — e.g. webhook URL, auth headers, "
            "field mapping"
        ),
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"crm_webhook", "dialer", "email", "custom"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}, got '{v}'")
        return v


class IntegrationUpdate(BaseModel):
    """Partial update for an integration."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    config: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable / disable the integration",
    )


class IntegrationResponse(BaseModel):
    """Integration as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    type: str
    config: Dict[str, Any]
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# API Keys (for webhook authentication)
# ---------------------------------------------------------------------------


class ApiKeyCreate(BaseModel):
    """Payload for generating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable label for the key",
    )


class ApiKeyResponse(BaseModel):
    """API key response returned on creation — the only time the raw key is exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key: str = Field(
        ...,
        description="The API key value (only shown once, at creation time)",
    )
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """API key summary used in list views — the raw key is NOT included."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
