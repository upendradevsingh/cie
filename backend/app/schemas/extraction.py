import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AttributedToSchema(BaseModel):
    external_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None


class ExtractionResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    tenant_id: uuid.UUID
    extraction_type: str
    description: str
    confidence: float
    attributed_to: Optional[dict] = None
    evidence: Optional[str] = None
    evidence_start_ms: Optional[int] = None
    evidence_end_ms: Optional[int] = None
    status: str
    attributes: dict[str, Any]
    corrected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CorrectionCreateRequest(BaseModel):
    field_name: str
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    correction_note: Optional[str] = None
    correction_type: str = "modify"
    attributes_delta: Optional[dict] = None


class CorrectionResponse(BaseModel):
    id: uuid.UUID
    extraction_id: uuid.UUID
    field_name: str
    correction_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
