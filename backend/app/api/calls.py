"""Call ingestion, listing, detail, transcript, and QA override routes."""

import os
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db.session import get_db
from app.models.call import Call, CallStatus, IntentClassification
from app.models.quality import CallQualityScore, QualityParameter
from app.models.intent import CallIntentSignal, IntentSignal
from app.models.persona import CallPersona
from app.models.action_item import ActionItem
from app.models.user import User
from app.schemas.call import (
    CallListFilters,
    CallListResponse,
    CallResponse,
    CallSummary,
    CallUpload,
    CallWebhook,
    TranscriptResponse,
    TranscriptSegment,
)
from app.schemas.quality import QAOverride
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/calls", tags=["Calls"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm"}


def _validate_audio_extension(filename: str) -> str:
    """Return the lowercase file extension or raise 400 if unsupported."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


def _build_call_response(call: Call) -> CallResponse:
    """Transform a Call ORM instance into a CallResponse schema."""
    # Quality scores
    quality_scores = None
    if call.quality_scores:
        quality_scores = [
            {
                "parameter_name": qs.parameter.name if qs.parameter else "Unknown",
                "parameter_category": qs.parameter.category if qs.parameter else "",
                "score": qs.score,
                "weight": qs.parameter.weight if qs.parameter else 0,
                "justification": qs.justification or "",
            }
            for qs in call.quality_scores
        ]

    # Intent signals
    intent_signals_out = None
    if call.intent_signals:
        intent_signals_out = [
            {
                "signal_name": sig.signal.name if sig.signal else "Unknown",
                "detected": sig.detected,
                "details": sig.details or "",
            }
            for sig in call.intent_signals
        ]

    # Persona / BANT
    persona_out = None
    if call.persona:
        persona_out = {
            "persona_type_name": (
                call.persona.persona_type.name if call.persona.persona_type else None
            ),
            "budget_score": call.persona.budget_score,
            "authority_score": call.persona.authority_score,
            "need_score": call.persona.need_score,
            "timeline_score": call.persona.timeline_score,
            "discovery_insights": call.persona.discovery_insights or [],
        }

    # Action items
    action_items_out = None
    if call.action_items:
        action_items_out = [
            {
                "id": str(ai.id),
                "description": ai.description,
                "category": ai.category,
                "urgency": ai.urgency.value if hasattr(ai.urgency, "value") else ai.urgency,
                "completed": ai.completed,
            }
            for ai in call.action_items
        ]

    # Extract analysis sub-fields
    analysis = call.analysis or {}
    objections = analysis.get("objections")
    path_to_conversion = analysis.get("path_to_conversion")
    follow_up_urgency = analysis.get("follow_up_urgency")
    extracted_metadata = analysis.get("extracted_metadata")

    # Transcript segments
    transcript_segments = None
    if call.transcript_segments:
        segments_raw = call.transcript_segments
        if isinstance(segments_raw, list):
            transcript_segments = [
                TranscriptSegment(**seg) for seg in segments_raw
            ]

    return CallResponse(
        id=call.id,
        tenant_id=call.tenant_id,
        agent_id=call.agent_id,
        agent_name=call.agent.full_name if call.agent else None,
        lead_id=call.lead_id,
        lead_name=call.lead_name,
        lead_phone=call.lead_phone,
        source=call.source,
        recording_url=call.recording_url,
        duration=call.duration_seconds,
        language=call.language or "en",
        status=call.status.value if hasattr(call.status, "value") else str(call.status),
        custom_fields=call.custom_fields,
        transcript_segments=transcript_segments,
        raw_transcript=call.transcript_raw,
        overall_score=call.overall_score,
        quality_scores=quality_scores,
        intent_score=call.lead_intent_score,
        intent_classification=(
            call.intent_classification.value
            if call.intent_classification and hasattr(call.intent_classification, "value")
            else call.intent_classification
        ),
        intent_signals=intent_signals_out,
        objections=objections,
        persona=persona_out,
        action_items=action_items_out,
        path_to_conversion=path_to_conversion,
        follow_up_urgency=follow_up_urgency,
        extracted_metadata=extracted_metadata,
        analysis_raw=call.analysis,
        created_at=call.created_at,
        updated_at=call.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /calls/upload
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a call recording for processing",
)
async def upload_call(
    file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, webm)"),
    agent_id: Optional[str] = Form(default=None, description="UUID of the agent"),
    lead_id: Optional[str] = Form(default=None, description="External lead identifier"),
    lead_name: Optional[str] = Form(default=None, description="Name of the lead"),
    lead_phone: Optional[str] = Form(default=None, description="Lead phone number"),
    source: Optional[str] = Form(default=None, description="Lead source"),
    language: str = Form(default="en", description="Language code (en, hi, hinglish)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CallResponse:
    """Upload an audio recording and queue it for transcription + analysis.

    The file is persisted to the configured upload directory (or S3 when
    configured).  A Celery task is dispatched to process the call
    asynchronously.  The response contains the newly created call record
    with ``status=uploaded``.
    """
    # Validate file type
    _validate_audio_extension(file.filename or "unknown.mp3")

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB",
        )

    # Validate agent_id if provided
    parsed_agent_id: UUID | None = None
    if agent_id:
        try:
            parsed_agent_id = UUID(agent_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent_id format. Must be a valid UUID.",
            )
        agent = (
            db.query(User)
            .filter(
                User.id == parsed_agent_id,
                User.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found in this tenant",
            )

    # Save file to disk
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.tenant_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_id = uuid_mod.uuid4()
    _, ext = os.path.splitext(file.filename or "recording.mp3")
    file_path = os.path.join(upload_dir, f"{file_id}{ext.lower()}")

    with open(file_path, "wb") as f:
        f.write(contents)

    # Create call record
    call = Call(
        tenant_id=current_user.tenant_id,
        agent_id=parsed_agent_id or current_user.id,
        recording_file_path=file_path,
        lead_id=lead_id,
        lead_name=lead_name,
        lead_phone=lead_phone,
        source=source,
        language=language,
        status=CallStatus.uploaded,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    # Dispatch async processing task
    try:
        from app.tasks.call_processing import process_call  # noqa: F811

        process_call.delay(str(call.id))
    except ImportError:
        # Tasks module may not be available yet during development
        pass

    # Eagerly load relationships for the response
    call = (
        db.query(Call)
        .options(
            joinedload(Call.agent),
            joinedload(Call.quality_scores).joinedload(CallQualityScore.parameter),
            joinedload(Call.intent_signals).joinedload(CallIntentSignal.signal),
            joinedload(Call.persona),
            joinedload(Call.action_items),
        )
        .filter(Call.id == call.id)
        .first()
    )

    return _build_call_response(call)


# ---------------------------------------------------------------------------
# POST /calls/webhook
# ---------------------------------------------------------------------------


@router.post(
    "/webhook",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive a call recording via webhook",
)
def webhook_call(
    body: CallWebhook,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CallResponse:
    """Receive a recording URL and metadata from an external CRM or dialer.

    The recording URL is stored and a Celery task is dispatched to download,
    transcribe, and analyze the call.
    """
    # Resolve agent_id: prefer explicit ID, fall back to email lookup
    resolved_agent_id: UUID | None = body.agent_id
    if resolved_agent_id is None and body.agent_email:
        agent = (
            db.query(User)
            .filter(
                User.email == body.agent_email,
                User.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if agent:
            resolved_agent_id = agent.id

    call = Call(
        tenant_id=current_user.tenant_id,
        agent_id=resolved_agent_id,
        recording_url=str(body.recording_url),
        lead_id=body.lead_id,
        lead_name=body.lead_name,
        lead_phone=body.lead_phone,
        source=body.source,
        custom_fields=body.custom_fields,
        language=body.language,
        status=CallStatus.uploaded,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    # Dispatch async processing task
    try:
        from app.tasks.call_processing import process_call

        process_call.delay(str(call.id))
    except ImportError:
        pass

    # Reload with relationships
    call = (
        db.query(Call)
        .options(
            joinedload(Call.agent),
            joinedload(Call.quality_scores).joinedload(CallQualityScore.parameter),
            joinedload(Call.intent_signals).joinedload(CallIntentSignal.signal),
            joinedload(Call.persona),
            joinedload(Call.action_items),
        )
        .filter(Call.id == call.id)
        .first()
    )

    return _build_call_response(call)


# ---------------------------------------------------------------------------
# GET /calls
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=CallListResponse,
    summary="List calls with filters and pagination",
)
def list_calls(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    agent_id: Optional[UUID] = Query(default=None, description="Filter by agent UUID"),
    date_from: Optional[datetime] = Query(default=None, description="Start date (inclusive)"),
    date_to: Optional[datetime] = Query(default=None, description="End date (inclusive)"),
    score_min: Optional[float] = Query(default=None, ge=0, le=100, description="Min quality score"),
    score_max: Optional[float] = Query(default=None, ge=0, le=100, description="Max quality score"),
    intent_classification: Optional[str] = Query(default=None, description="hot, warm, or cold"),
    call_status: Optional[str] = Query(default=None, alias="status", description="Processing status"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
) -> CallListResponse:
    """Return a paginated list of calls for the current tenant.

    Supports filtering by agent, date range, score range, intent
    classification, and processing status.
    """
    query = (
        db.query(Call)
        .options(joinedload(Call.agent))
        .filter(Call.tenant_id == current_user.tenant_id)
    )

    # Apply filters
    if agent_id is not None:
        query = query.filter(Call.agent_id == agent_id)

    if date_from is not None:
        query = query.filter(Call.created_at >= date_from)

    if date_to is not None:
        query = query.filter(Call.created_at <= date_to)

    if score_min is not None:
        query = query.filter(Call.overall_score >= score_min)

    if score_max is not None:
        query = query.filter(Call.overall_score <= score_max)

    if intent_classification is not None:
        intent_val = intent_classification.lower()
        if intent_val in {"hot", "warm", "cold"}:
            query = query.filter(
                Call.intent_classification == IntentClassification(intent_val)
            )

    if call_status is not None:
        status_val = call_status.lower()
        if status_val in {s.value for s in CallStatus}:
            query = query.filter(Call.status == CallStatus(status_val))

    # Total count (before pagination)
    total = query.count()

    # Order and paginate
    calls = (
        query.order_by(Call.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        CallSummary(
            id=call.id,
            agent_name=call.agent.full_name if call.agent else None,
            lead_name=call.lead_name,
            duration=call.duration_seconds,
            overall_score=call.overall_score,
            intent_classification=(
                call.intent_classification.value
                if call.intent_classification and hasattr(call.intent_classification, "value")
                else call.intent_classification
            ),
            status=call.status.value if hasattr(call.status, "value") else str(call.status),
            created_at=call.created_at,
        )
        for call in calls
    ]

    return CallListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /calls/{call_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{call_id}",
    response_model=CallResponse,
    summary="Get full call detail",
)
def get_call(
    call_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CallResponse:
    """Return the full call detail including transcript, quality scores,
    lead intelligence, persona analysis, and action items.
    """
    call = (
        db.query(Call)
        .options(
            joinedload(Call.agent),
            joinedload(Call.quality_scores).joinedload(CallQualityScore.parameter),
            joinedload(Call.intent_signals).joinedload(CallIntentSignal.signal),
            joinedload(Call.persona).joinedload(CallPersona.persona_type),
            joinedload(Call.action_items),
        )
        .filter(
            Call.id == call_id,
            Call.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    return _build_call_response(call)


# ---------------------------------------------------------------------------
# GET /calls/{call_id}/transcript
# ---------------------------------------------------------------------------


@router.get(
    "/{call_id}/transcript",
    response_model=TranscriptResponse,
    summary="Get call transcript with speaker labels",
)
def get_transcript(
    call_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TranscriptResponse:
    """Return the speaker-labeled transcript for a specific call.

    Segments include speaker identification, start/end timestamps, and
    the transcribed text.
    """
    call = (
        db.query(Call)
        .filter(
            Call.id == call_id,
            Call.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    if call.status not in (CallStatus.completed, CallStatus.analyzing):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transcript not available. Call status is '{call.status.value}'.",
        )

    segments: List[TranscriptSegment] = []
    if call.transcript_segments and isinstance(call.transcript_segments, list):
        segments = [TranscriptSegment(**seg) for seg in call.transcript_segments]

    return TranscriptResponse(
        call_id=call.id,
        segments=segments,
        raw_text=call.transcript_raw or "",
    )


# ---------------------------------------------------------------------------
# PUT /calls/{call_id}/qa-override
# ---------------------------------------------------------------------------


@router.put(
    "/{call_id}/qa-override",
    response_model=CallResponse,
    summary="Override quality scores via manual QA review",
)
def qa_override(
    call_id: UUID,
    body: QAOverride,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin", "team_lead"]))],
) -> CallResponse:
    """Allow admin or team lead to manually correct quality scores.

    Each item in the ``scores`` list specifies a quality parameter ID,
    the corrected score (0--10), and a justification for the override.
    The overall weighted score is recalculated after applying all overrides.
    """
    call = (
        db.query(Call)
        .options(
            joinedload(Call.agent),
            joinedload(Call.quality_scores).joinedload(CallQualityScore.parameter),
            joinedload(Call.intent_signals).joinedload(CallIntentSignal.signal),
            joinedload(Call.persona).joinedload(CallPersona.persona_type),
            joinedload(Call.action_items),
        )
        .filter(
            Call.id == call_id,
            Call.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    if call.status != CallStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="QA override is only available for completed calls",
        )

    # Build a lookup from parameter_id -> existing CallQualityScore
    existing_scores = {qs.parameter_id: qs for qs in call.quality_scores}

    for override_item in body.scores:
        # Verify the parameter belongs to this tenant
        param = (
            db.query(QualityParameter)
            .filter(
                QualityParameter.id == override_item.parameter_id,
                QualityParameter.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if param is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quality parameter {override_item.parameter_id} not found",
            )

        if override_item.parameter_id in existing_scores:
            # Update existing score
            qs = existing_scores[override_item.parameter_id]
            qs.score = override_item.new_score
            qs.justification = f"[QA Override] {override_item.justification}"
        else:
            # Create new score entry
            new_qs = CallQualityScore(
                call_id=call.id,
                parameter_id=override_item.parameter_id,
                score=override_item.new_score,
                justification=f"[QA Override] {override_item.justification}",
            )
            db.add(new_qs)

    # Recalculate overall weighted score
    db.flush()  # Ensure new scores are visible
    all_scores = (
        db.query(CallQualityScore)
        .options(joinedload(CallQualityScore.parameter))
        .filter(CallQualityScore.call_id == call.id)
        .all()
    )

    total_weight = 0.0
    weighted_sum = 0.0
    for qs in all_scores:
        if qs.parameter and qs.parameter.is_active:
            weight = qs.parameter.weight
            # Score is 0-10, normalize to 0-100 scale for overall
            weighted_sum += qs.score * weight
            total_weight += weight

    if total_weight > 0:
        # Convert from 0-10 scale to 0-100 scale
        call.overall_score = round((weighted_sum / total_weight) * 10, 2)
    else:
        call.overall_score = 0.0

    call.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Reload with all relationships
    call = (
        db.query(Call)
        .options(
            joinedload(Call.agent),
            joinedload(Call.quality_scores).joinedload(CallQualityScore.parameter),
            joinedload(Call.intent_signals).joinedload(CallIntentSignal.signal),
            joinedload(Call.persona).joinedload(CallPersona.persona_type),
            joinedload(Call.action_items),
        )
        .filter(Call.id == call_id)
        .first()
    )

    return _build_call_response(call)
