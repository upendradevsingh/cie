import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.conversation import ConversationStatus


class ParticipantSchema(BaseModel):
    external_id: str = Field(..., alias="externalId")
    name: str
    role: str

    model_config = {"populate_by_name": True}


class SegmentSchema(BaseModel):
    speaker: str
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ConversationCreateRequest(BaseModel):
    source: str = Field(..., description="voice|text|chat|meeting|email")
    profile: str = Field(..., description="Profile ID, e.g. performance|sales")
    participants: list[ParticipantSchema] = Field(default_factory=list)
    segments: Optional[list[SegmentSchema]] = Field(
        None, description="Pre-transcribed segments (skip transcription if provided)"
    )
    audio_url: Optional[str] = None
    language: str = "en"
    callback_url: Optional[str] = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    profile_id: str
    status: ConversationStatus
    language: str
    participants: list[dict]
    summary: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
