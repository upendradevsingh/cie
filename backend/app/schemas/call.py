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
    """Lightweight call representation used in list views (matches frontend CallListItem)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_name: str = ""
    agent_id: Optional[UUID] = None
    lead_name: str = ""
    lead_id: str = ""
    lead_phone: str = ""
    duration: float = 0
    overall_score: float = 0
    intent_classification: Optional[str] = None
    intent_score: float = 0
    status: str = "pending"
    source: str = ""
    follow_up_urgency: Optional[str] = None
    created_at: datetime


class CallListResponse(BaseModel):
    """Paginated list of call summaries."""

    items: List[CallSummary]
    total: int = Field(..., ge=0, description="Total matching records")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(default=1, ge=1)


# ---------------------------------------------------------------------------
# Nested response models for Call Detail (matching frontend CallData)
# ---------------------------------------------------------------------------


class TranscriptSegmentResponse(BaseModel):
    """Enriched transcript segment for call detail API response."""

    id: str
    speaker: str
    speaker_name: str
    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0
    is_key_moment: bool = False
    key_moment_label: Optional[str] = None


class QualityScoreResponse(BaseModel):
    """Quality score for a single parameter."""

    parameter_id: str
    parameter_name: str
    category: str
    score: float
    max_score: float = 10.0
    weight: float
    justification: str


class IntentSignalResponse(BaseModel):
    """Intent signal detection result."""

    id: str
    name: str
    description: str = ""
    detected: bool
    details: Optional[str] = None


class ObjectionResponse(BaseModel):
    """Extracted objection from the call."""

    objection: str
    category: str = "general"
    severity: str = "medium"
    rebuttal_suggestion: Optional[str] = None


class LeadIntelligenceResponse(BaseModel):
    """Lead intelligence analysis."""

    intent_score: float = 0
    classification: str = "cold"
    signals: List[IntentSignalResponse] = Field(default_factory=list)
    key_objections: List[ObjectionResponse] = Field(default_factory=list)
    buying_signals: List[str] = Field(default_factory=list)


class BANTScoreResponse(BaseModel):
    """BANT scoring breakdown."""

    budget: float = 0
    authority: float = 0
    need: float = 0
    timeline: float = 0


class PersonaDataResponse(BaseModel):
    """Persona analysis with BANT."""

    persona_type: str = "Unknown"
    persona_type_id: Optional[str] = None
    bant: BANTScoreResponse = Field(default_factory=BANTScoreResponse)
    discovery_insights: List[str] = Field(default_factory=list)


class ActionItemResponse(BaseModel):
    """Action item extracted from call."""

    id: str
    call_id: str
    text: str
    type: str = "follow_up"
    urgency: str = "this_week"
    category: str = ""
    priority: str = "medium"
    due_date: Optional[str] = None
    completed: bool = False
    created_at: str = ""


class RebuttalItem(BaseModel):
    """Objection-rebuttal pair."""

    objection: str
    rebuttal: str


class PathToConversionResponse(BaseModel):
    """AI-generated path to conversion."""

    talking_points: List[str] = Field(default_factory=list)
    rebuttals: List[RebuttalItem] = Field(default_factory=list)
    follow_up_urgency: str = "nurture"
    next_best_action: str = ""


class CustomFieldItem(BaseModel):
    """Key-value custom field."""

    key: str
    value: str


class CallResponse(BaseModel):
    """Full call detail — matches frontend CallData interface."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    recording_url: Optional[str] = None
    duration: float = 0
    agent_name: str = ""
    agent_id: Optional[UUID] = None
    lead_name: str = ""
    lead_id: str = ""
    lead_phone: str = ""
    source: str = ""
    status: str = "pending"
    custom_fields: List[CustomFieldItem] = Field(default_factory=list)

    # Transcript
    transcript: List[TranscriptSegmentResponse] = Field(default_factory=list)

    # Quality scores
    quality_scores: List[QualityScoreResponse] = Field(default_factory=list)
    overall_score: float = 0

    # Lead Intelligence (nested)
    lead_intelligence: LeadIntelligenceResponse = Field(
        default_factory=LeadIntelligenceResponse,
    )

    # Persona (nested)
    persona: PersonaDataResponse = Field(default_factory=PersonaDataResponse)

    # Action Items
    action_items: List[ActionItemResponse] = Field(default_factory=list)

    # Path to Conversion (nested)
    path_to_conversion: PathToConversionResponse = Field(
        default_factory=PathToConversionResponse,
    )

    # Metadata
    metadata_extraction: Dict[str, Any] = Field(default_factory=dict)
    follow_up_urgency: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
