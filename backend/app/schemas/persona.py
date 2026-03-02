"""Persona type and BANT analysis schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Persona Type CRUD
# ---------------------------------------------------------------------------


class PersonaTypeCreate(BaseModel):
    """Payload for creating a new persona type."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Persona label (e.g. 'Budget-Conscious Decision Maker')",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Behavioral description of this persona",
    )
    bant_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Ideal BANT profile for this persona — keys: budget, authority, need, "
            "timeline, each with a target score range"
        ),
    )


class PersonaTypeUpdate(BaseModel):
    """Partial update for a persona type."""

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
    bant_profile: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(
        default=None,
        description="Soft-enable / soft-disable the persona type",
    )


class PersonaTypeResponse(BaseModel):
    """Persona type as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str
    bant_profile: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Per-call persona / BANT analysis
# ---------------------------------------------------------------------------


class CallPersonaResponse(BaseModel):
    """BANT analysis and persona classification for a specific call."""

    persona_type_name: Optional[str] = Field(
        default=None,
        description="Matched persona type (None if no strong match)",
    )
    budget_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Budget indication score (0–10)",
    )
    authority_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Authority / decision-maker score (0–10)",
    )
    need_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Need / pain-point score (0–10)",
    )
    timeline_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Timeline urgency score (0–10)",
    )
    discovery_insights: List[str] = Field(
        default_factory=list,
        description="Key insights discovered about the lead during the call",
    )

    @field_validator("budget_score", "authority_score", "need_score", "timeline_score")
    @classmethod
    def round_scores(cls, v: float) -> float:
        return round(v, 1)
