"""Call-related Pydantic schemas.

Covers upload, webhook ingestion, list/detail responses, transcript, and
filtering / pagination for the calls API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class CallUpload(BaseModel):
    """Metadata submitted alongside a recording file upload.

    The actual audio file is received as ``UploadFile`` in the endpoint;
    this schema captures the accompanying form / JSON metadata.
    """

    agent_id: Optional[UUID] = Field(
        default=None,
        description="ID of the agent who handled the call",
    )
    lead_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="External lead / contact identifier",
    )
    lead_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Name of the lead / customer",
    )
    lead_phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Lead phone number",
    )
    source: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Lead source (e.g. website, referral, campaign name)",
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Up to 5 arbitrary key/value pairs for tenant-specific data",
    )
    language: str = Field(
        default="en",
        max_length=10,
        description="Primary language code (en, hi, hinglish)",
    )

    @field_validator("custom_fields")
    @classmethod
    def limit_custom_fields(
        cls, v: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if v is not None and len(v) > 5:
            raise ValueError("A maximum of 5 custom fields is allowed")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = {"en", "hi", "hinglish"}
        if v not in allowed:
            raise ValueError(f"Language must be one of {allowed}, got '{v}'")
        return v


class CallWebhook(BaseModel):
    """Payload received from an external CRM / dialer webhook."""

    recording_url: HttpUrl = Field(
        ...,
        description="Publicly-accessible URL of the call recording",
    )
    agent_id: Optional[UUID] = Field(
        default=None,
        description="ID of the agent who handled the call",
    )
    agent_email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Agent email — used to look up the agent when agent_id is absent",
    )
    lead_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="External lead / contact identifier",
    )
    lead_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Name of the lead / customer",
    )
    lead_phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Lead phone number",
    )
    source: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Lead source",
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Up to 5 arbitrary key/value pairs",
    )
    language: str = Field(
        default="en",
        max_length=10,
        description="Primary language code (en, hi, hinglish)",
    )

    @field_validator("custom_fields")
    @classmethod
    def limit_custom_fields(
        cls, v: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if v is not None and len(v) > 5:
            raise ValueError("A maximum of 5 custom fields is allowed")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = {"en", "hi", "hinglish"}
        if v not in allowed:
            raise ValueError(f"Language must be one of {allowed}, got '{v}'")
        return v


# ---------------------------------------------------------------------------
# Filters / Pagination
# ---------------------------------------------------------------------------


class CallListFilters(BaseModel):
    """Query parameters for the calls listing endpoint."""

    agent_id: Optional[UUID] = Field(default=None, description="Filter by agent")
    date_from: Optional[datetime] = Field(
        default=None,
        description="Include calls on or after this timestamp",
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Include calls on or before this timestamp",
    )
    score_min: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Minimum overall quality score",
    )
    score_max: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Maximum overall quality score",
    )
    intent_classification: Optional[str] = Field(
        default=None,
        description="Lead intent bucket: hot, warm, or cold",
    )
    status: Optional[str] = Field(
        default=None,
        description="Processing status: pending, transcribing, analyzing, completed, failed",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Results per page (max 100)",
    )

    @field_validator("intent_classification")
    @classmethod
    def validate_intent(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"hot", "warm", "cold"}
        if v.lower() not in allowed:
            raise ValueError(f"intent_classification must be one of {allowed}")
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"pending", "transcribing", "analyzing", "completed", "failed"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v.lower()


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


class TranscriptSegment(BaseModel):
    """A single speaker-labeled segment of a call transcript."""

    speaker: str = Field(..., description="Speaker label (e.g. 'agent' or 'customer')")
    start_time: float = Field(..., ge=0, description="Segment start time in seconds")
    end_time: float = Field(..., ge=0, description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text for the segment")


class TranscriptResponse(BaseModel):
    """Full transcript for a single call."""

    model_config = ConfigDict(from_attributes=True)

    call_id: UUID
    segments: List[TranscriptSegment] = Field(default_factory=list)
    raw_text: str = Field(default="", description="Plain-text transcript without speaker labels")


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class CallSummary(BaseModel):
    """Lightweight call representation used in list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_name: Optional[str] = None
    lead_name: Optional[str] = None
    duration: Optional[float] = Field(
        default=None,
        description="Call duration in seconds",
    )
    overall_score: Optional[float] = Field(
        default=None,
        description="Weighted quality score (0-100)",
    )
    intent_classification: Optional[str] = Field(
        default=None,
        description="hot / warm / cold",
    )
    status: str = Field(
        default="pending",
        description="Processing status",
    )
    created_at: datetime


class CallListResponse(BaseModel):
    """Paginated list of call summaries."""

    items: List[CallSummary]
    total: int = Field(..., ge=0, description="Total matching records")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


class CallResponse(BaseModel):
    """Full call detail — includes transcript, analysis, scores, and metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    lead_id: Optional[str] = None
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    source: Optional[str] = None
    recording_url: Optional[str] = None
    duration: Optional[float] = None
    language: str = "en"
    status: str = "pending"
    custom_fields: Optional[Dict[str, Any]] = None

    # Transcript
    transcript_segments: Optional[List[TranscriptSegment]] = None
    raw_transcript: Optional[str] = None

    # Quality scores
    overall_score: Optional[float] = None
    quality_scores: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-parameter quality scores with justifications",
    )

    # Lead intelligence
    intent_score: Optional[float] = None
    intent_classification: Optional[str] = None
    intent_signals: Optional[List[Dict[str, Any]]] = None
    objections: Optional[List[Dict[str, Any]]] = None

    # Persona / BANT
    persona: Optional[Dict[str, Any]] = None

    # Action items
    action_items: Optional[List[Dict[str, Any]]] = None
    path_to_conversion: Optional[List[str]] = None
    follow_up_urgency: Optional[str] = None

    # Metadata extraction
    extracted_metadata: Optional[Dict[str, Any]] = None

    # LLM raw analysis (stored for debugging / audit)
    analysis_raw: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
