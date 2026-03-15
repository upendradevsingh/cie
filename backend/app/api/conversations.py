"""Conversation submission and retrieval endpoints."""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_with_tenant
from app.models.conversation import Conversation, ConversationStatus
from app.profiles import get_profile_loader
from app.schemas.conversation import ConversationCreateRequest, ConversationResponse
from app.services.auth import TokenClaims, get_token_claims
from app.tasks.process_conversation import process_conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_conversation(
    request: ConversationCreateRequest,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> ConversationResponse:
    """Submit a conversation for processing.

    If `segments` are provided, transcription is skipped.
    If `audio_url` is provided, transcription will be performed asynchronously.
    """
    # Validate profile exists
    loader = get_profile_loader()
    try:
        loader.load(request.profile)
    except ValueError:
        available = loader.list_profiles()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown profile '{request.profile}'. Available: {available}",
        )

    # Build transcript from segments if provided
    transcript_raw: Optional[str] = None
    transcript_segments: Optional[list] = None
    initial_status = ConversationStatus.pending

    if request.segments:
        transcript_segments = [s.model_dump() for s in request.segments]
        transcript_raw = " ".join(s.text for s in request.segments)
        initial_status = ConversationStatus.pending  # will go straight to extracting

    conversation = Conversation(
        tenant_id=claims.tenant_id,
        source=request.source,
        profile_id=request.profile,
        participants=[p.model_dump(by_alias=True) for p in request.participants],
        audio_url=request.audio_url,
        language=request.language,
        callback_url=request.callback_url,
        source_metadata=request.source_metadata,
        transcript_raw=transcript_raw,
        transcript_segments=transcript_segments,
        status=initial_status,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Dispatch async processing task
    process_conversation.delay(str(conversation.id))
    logger.info("Submitted conversation %s profile=%s", conversation.id, request.profile)

    return ConversationResponse.model_validate(conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> ConversationResponse:
    """Get conversation status and metadata by ID."""
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
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    status: Optional[ConversationStatus] = None,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> list[ConversationResponse]:
    """List conversations for the current tenant."""
    query = db.query(Conversation).filter(
        Conversation.tenant_id == claims.tenant_id
    )
    if status:
        query = query.filter(Conversation.status == status)
    conversations = query.order_by(Conversation.created_at.desc()).offset(offset).limit(limit).all()
    return [ConversationResponse.model_validate(c) for c in conversations]
