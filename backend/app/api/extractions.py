"""Extraction retrieval, correction, and review queue endpoints."""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, case, func
from sqlalchemy.orm import Session

from app.db.session import get_db_with_tenant
from app.models.correction import Correction
from app.models.conversation import Conversation
from app.models.extraction import Extraction
from app.schemas.extraction import (
    CorrectionCreateRequest,
    CorrectionDetailResponse,
    CorrectionResponse,
    ExtractionResponse,
    ReviewQueueItem,
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

    # Return 202 if conversation is still processing — signals "not ready yet"
    if conversation.status not in ("completed", "failed"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=202, content=[])

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


@router.get(
    "/extractions/review-queue",
    response_model=list[ReviewQueueItem],
)
async def get_review_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    extraction_type: Optional[str] = None,
    profile_id: Optional[str] = None,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> list[ReviewQueueItem]:
    """Get extractions ranked by review priority.

    Priority score = (1 - confidence) * 0.4
                   + type_correction_rate * 0.35
                   + recency_score * 0.25
    """
    # Step 1: Compute per-type correction rates for this tenant
    type_stats = (
        db.query(
            Extraction.extraction_type,
            func.count(Extraction.id).label("total"),
            func.sum(
                case((Extraction.corrected == True, 1), else_=0)  # noqa: E712  # noqa: E712
            ).label("corrected"),
        )
        .filter(Extraction.tenant_id == claims.tenant_id)
        .group_by(Extraction.extraction_type)
        .all()
    )

    correction_rates: dict[str, float] = {}
    for ext_type, total, corrected in type_stats:
        correction_rates[ext_type] = (corrected or 0) / total if total > 0 else 0.0

    # Step 2: Query uncorrected extractions
    query = (
        db.query(Extraction)
        .filter(
            Extraction.tenant_id == claims.tenant_id,
            Extraction.corrected == False,  # noqa: E712
        )
    )

    if extraction_type:
        query = query.filter(Extraction.extraction_type == extraction_type)

    if profile_id:
        query = query.join(
            Conversation, Extraction.conversation_id == Conversation.id
        ).filter(Conversation.profile_id == profile_id)

    extractions = query.order_by(Extraction.created_at.desc()).all()

    # Step 3: Score and rank
    now = datetime.now(timezone.utc)
    max_age_days = 30.0

    scored_items: list[tuple[float, Extraction]] = []
    for ext in extractions:
        confidence_score = (1.0 - ext.confidence) * 0.4
        type_rate = correction_rates.get(ext.extraction_type, 0.0) * 0.35
        age_days = (now - ext.created_at).total_seconds() / 86400.0
        recency = max(0.0, 1.0 - age_days / max_age_days) * 0.25
        priority = confidence_score + type_rate + recency
        scored_items.append((priority, ext))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Step 4: Paginate and return
    page = scored_items[offset : offset + limit]
    return [
        ReviewQueueItem(
            id=ext.id,
            conversation_id=ext.conversation_id,
            extraction_type=ext.extraction_type,
            description=ext.description,
            confidence=ext.confidence,
            attributed_to=ext.attributed_to,
            evidence=ext.evidence,
            attributes=ext.attributes,
            corrected=ext.corrected,
            created_at=ext.created_at,
            review_priority=round(priority, 4),
        )
        for priority, ext in page
    ]


@router.get(
    "/extractions/{extraction_id}/corrections",
    response_model=list[CorrectionDetailResponse],
)
async def get_correction_history(
    extraction_id: uuid.UUID,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> list[CorrectionDetailResponse]:
    """Get all corrections for an extraction."""
    # Verify extraction belongs to tenant
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

    corrections = (
        db.query(Correction)
        .filter(Correction.extraction_id == extraction_id)
        .order_by(Correction.created_at.desc())
        .all()
    )
    return [CorrectionDetailResponse.model_validate(c) for c in corrections]
