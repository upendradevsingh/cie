"""Intent signal schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Intent Signal CRUD
# ---------------------------------------------------------------------------


class IntentSignalCreate(BaseModel):
    """Payload for creating a new intent signal definition."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Signal name (e.g. 'Budget Mentioned')",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="What this signal represents — also used in the LLM prompt",
    )


class IntentSignalUpdate(BaseModel):
    """Partial update for an intent signal."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Soft-enable / soft-disable the signal",
    )


class IntentSignalResponse(BaseModel):
    """Intent signal as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Per-call intent evaluation
# ---------------------------------------------------------------------------


class CallIntentResponse(BaseModel):
    """Result of evaluating one intent signal against a specific call."""

    signal_name: str = Field(..., description="Name of the intent signal")
    detected: bool = Field(
        ...,
        description="Whether the signal was detected in the call",
    )
    details: str = Field(
        default="",
        description="LLM-generated supporting detail or quote from the transcript",
    )
