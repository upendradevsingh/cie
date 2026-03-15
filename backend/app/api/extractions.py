"""Extraction retrieval and correction endpoints."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_with_tenant
from app.models.correction import Correction
from app.models.conversation import Conversation
from app.models.extraction import Extraction
from app.schemas.extraction import (
    CorrectionCreateRequest,
    CorrectionResponse,
    ExtractionResponse,
)
from app.services.auth import TokenClaims, get_token_claims

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extractions"])


@router.get(
    "/conversations/{conversation_id}/extractions",
    response_model=list[ExtractionResponse],
)
async def get_extractions(
    conversation_id: uuid.UUID,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> list[ExtractionResponse]:
    """Get all extractions for a conversation."""
    # Verify conversation belongs to tenant
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == claims.tenant_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    extractions = (
        db.query(Extraction)
        .filter(
            Extraction.conversation_id == conversation_id,
            Extraction.tenant_id == claims.tenant_id,
        )
        .order_by(Extraction.created_at)
        .all()
    )
    return [ExtractionResponse.model_validate(e) for e in extractions]


@router.post(
    "/extractions/{extraction_id}/corrections",
    response_model=CorrectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_correction(
    extraction_id: uuid.UUID,
    request: CorrectionCreateRequest,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> CorrectionResponse:
    """Submit a correction for an extraction (feedback loop)."""
    extraction = (
        db.query(Extraction)
        .filter(
            Extraction.id == extraction_id,
            Extraction.tenant_id == claims.tenant_id,
        )
        .first()
    )
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction {extraction_id} not found",
        )

    correction = Correction(
        extraction_id=extraction_id,
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        field_name=request.field_name,
        original_value=request.original_value,
        corrected_value=request.corrected_value,
        correction_note=request.correction_note,
        correction_type=request.correction_type,
        attributes_delta=request.attributes_delta,
    )

    # Mark extraction as corrected
    from datetime import datetime, timezone
    extraction.corrected = True
    extraction.corrected_at = datetime.now(timezone.utc)

    db.add(correction)
    db.commit()
    db.refresh(correction)

    logger.info("Correction created for extraction %s", extraction_id)
    return CorrectionResponse.model_validate(correction)
