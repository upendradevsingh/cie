"""Quality parameter and scoring schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Quality Parameter CRUD
# ---------------------------------------------------------------------------


class QualityParameterCreate(BaseModel):
    """Payload for creating a new quality scoring parameter."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable parameter name (e.g. 'Objection Handling')",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="What this parameter measures — also fed to the LLM prompt",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative weight for the overall score (0.0 – 1.0)",
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Grouping category (e.g. 'Communication', 'Sales Technique')",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Order in which to display this parameter in the UI",
    )

    @field_validator("weight")
    @classmethod
    def validate_weight_precision(cls, v: float) -> float:
        """Round weight to two decimal places to avoid floating-point noise."""
        return round(v, 2)


class QualityParameterUpdate(BaseModel):
    """Partial update for a quality parameter. All fields optional."""

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
    weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    category: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Soft-enable / soft-disable the parameter",
    )
    display_order: Optional[int] = Field(
        default=None,
        ge=0,
    )

    @field_validator("weight")
    @classmethod
    def validate_weight_precision(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        return round(v, 2)


class QualityParameterResponse(BaseModel):
    """Quality parameter as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str
    weight: float
    category: str
    is_active: bool
    display_order: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Per-call quality scores
# ---------------------------------------------------------------------------


class CallQualityScoreResponse(BaseModel):
    """A single parameter's score for a specific call."""

    parameter_name: str = Field(..., description="Name of the quality parameter")
    parameter_category: str = Field(..., description="Category of the parameter")
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Score awarded for this parameter (0–10)",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight used when computing the overall score",
    )
    justification: str = Field(
        ...,
        description="LLM-generated explanation for the score",
    )


# ---------------------------------------------------------------------------
# QA Override
# ---------------------------------------------------------------------------


class QAOverrideItem(BaseModel):
    """A single score correction within a QA override request."""

    parameter_id: UUID = Field(..., description="Quality parameter being overridden")
    new_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Corrected score (0–10)",
    )
    justification: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Reason for the override",
    )


class QAOverride(BaseModel):
    """Batch QA override — allows correcting multiple parameter scores at once."""

    scores: List[QAOverrideItem] = Field(
        ...,
        min_length=1,
        description="List of parameter-level score corrections",
    )
