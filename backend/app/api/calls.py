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
from app.db.rls import set_tenant_context
from app.db.session import get_db, get_db_with_tenant
from app.models.call import Call, CallStatus, IntentClassification
from app.models.quality import CallQualityScore, QualityParameter
from app.models.intent import CallIntentSignal, IntentSignal
from app.models.persona import CallPersona
from app.models.action_item import ActionItem
from app.models.user import User
from app.schemas.call import (
    ActionItemResponse,
    BANTScoreResponse,
    CallListFilters,
    CallListResponse,
    CallResponse,
    CallSummary,
    CallUpload,
    CallWebhook,
    CustomFieldItem,
    EscalationKeyword,
    IntentSignalResponse,
    LeadIntelligenceResponse,
    ObjectionResponse,
    PathToConversionResponse,
    PersonaDataResponse,
    QualityScoreResponse,
    RebuttalItem,
    SalesAuditKeyword,
    SalesAuditKeywords,
    SentimentData,
    TranscriptResponse,
    TranscriptSegment,
    TranscriptSegmentResponse,
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
    """Transform a Call ORM instance into a CallResponse matching frontend CallData."""
    analysis = call.analysis or {}

    # --- Transcript ---
    transcript = []
    if call.transcript_segments and isinstance(call.transcript_segments, list):
        for idx, seg in enumerate(call.transcript_segments):
            speaker_raw = seg.get("speaker", "unknown")
            speaker = speaker_raw.lower() if speaker_raw else "unknown"
            if speaker not in ("agent", "customer"):
                speaker = (
                    "agent"
                    if "agent" in speaker
                    else "customer" if "customer" in speaker else "unknown"
                )
            transcript.append(
                TranscriptSegmentResponse(
                    id=str(idx),
                    speaker=speaker,
                    speaker_name=seg.get("speaker", speaker.capitalize()),
                    text=seg.get("text", ""),
                    start_time=seg.get("start_time", 0),
                    end_time=seg.get("end_time", 0),
                    confidence=seg.get("confidence", 1.0),
                    is_key_moment=seg.get("is_key_moment", False),
                    key_moment_label=seg.get("key_moment_label"),
                )
            )

    # --- Quality Scores ---
    quality_scores = []
    if call.quality_scores:
        # Use ORM relationship data (call was analyzed after params were seeded)
        for qs in call.quality_scores:
            quality_scores.append(
                QualityScoreResponse(
                    parameter_id=str(qs.parameter_id) if qs.parameter_id else "",
                    parameter_name=qs.parameter.name if qs.parameter else "Unknown",
                    category=qs.parameter.category if qs.parameter else "General",
                    score=qs.score,
                    max_score=10.0,
                    weight=qs.parameter.weight if qs.parameter else 0,
                    justification=qs.justification or "",
                )
            )
    elif analysis.get("quality_scores"):
        # Fallback: use raw analysis JSON (call analyzed before params seeded)
        for idx, qs in enumerate(analysis["quality_scores"]):
            if isinstance(qs, dict):
                quality_scores.append(
                    QualityScoreResponse(
                        parameter_id=str(idx),
                        parameter_name=qs.get("parameter_name", "Unknown"),
                        category=qs.get("parameter_category", "General"),
                        score=qs.get("score", 0),
                        max_score=10.0,
                        weight=qs.get("weight", 0),
                        justification=qs.get("justification", ""),
                    )
                )

    # --- Lead Intelligence ---
    # Intent signals from ORM relationship
    signals = []
    buying_signals = []
    if call.intent_signals:
        for sig in call.intent_signals:
            signals.append(
                IntentSignalResponse(
                    id=str(sig.id),
                    name=sig.signal.name if sig.signal else "Unknown",
                    description=sig.signal.description if sig.signal else "",
                    detected=sig.detected,
                    details=sig.details or "",
                )
            )
            if sig.detected and sig.details:
                buying_signals.append(sig.details)
    elif analysis.get("intent_signals"):
        # Fallback: use raw analysis JSON
        for idx, sig in enumerate(analysis["intent_signals"]):
            if isinstance(sig, dict):
                detected = sig.get("detected", False)
                details = sig.get("details", "")
                signals.append(
                    IntentSignalResponse(
                        id=str(idx),
                        name=sig.get("signal_name", "Unknown"),
                        description="",
                        detected=detected,
                        details=details,
                    )
                )
                if detected and details:
                    buying_signals.append(details)

    # Key objections from analysis
    key_objections = []
    raw_objections = analysis.get("objections") or []
    if isinstance(raw_objections, list):
        for obj in raw_objections:
            if isinstance(obj, dict):
                key_objections.append(
                    ObjectionResponse(
                        objection=obj.get("objection", obj.get("text", str(obj))),
                        category=obj.get("category", "general"),
                        severity=obj.get("severity", "medium"),
                        rebuttal_suggestion=obj.get(
                            "rebuttal_suggestion", obj.get("rebuttal")
                        ),
                    )
                )
            elif isinstance(obj, str):
                key_objections.append(ObjectionResponse(objection=obj))

    lead_intelligence = LeadIntelligenceResponse(
        intent_score=call.lead_intent_score or 0,
        classification=(
            call.intent_classification.value
            if call.intent_classification
            and hasattr(call.intent_classification, "value")
            else call.intent_classification or "cold"
        ),
        signals=signals,
        key_objections=key_objections,
        buying_signals=buying_signals,
    )

    # --- Persona ---
    persona_data = PersonaDataResponse()
    if call.persona:
        raw_persona = analysis.get("persona", {})
        if not isinstance(raw_persona, dict):
            raw_persona = {}
        persona_data = PersonaDataResponse(
            persona_type=(
                call.persona.persona_type.name
                if call.persona.persona_type
                else raw_persona.get("type", "Unknown")
            ),
            persona_type_id=(
                str(call.persona.persona_type_id)
                if call.persona.persona_type_id
                else None
            ),
            bant=BANTScoreResponse(
                budget=call.persona.budget_score or 0,
                authority=call.persona.authority_score or 0,
                need=call.persona.need_score or 0,
                timeline=call.persona.timeline_score or 0,
            ),
            discovery_insights=(
                call.persona.discovery_insights
                if isinstance(call.persona.discovery_insights, list)
                else []
            ),
        )
    elif analysis.get("persona") and isinstance(analysis["persona"], dict):
        # Fallback: use raw analysis JSON persona
        raw_p = analysis["persona"]
        persona_data = PersonaDataResponse(
            persona_type=raw_p.get("type", "Unknown"),
            persona_type_id=None,
            bant=BANTScoreResponse(
                budget=raw_p.get("budget_score", 0),
                authority=raw_p.get("authority_score", 0),
                need=raw_p.get("need_score", 0),
                timeline=raw_p.get("timeline_score", 0),
            ),
            discovery_insights=(
                raw_p.get("discovery_insights", [])
                if isinstance(raw_p.get("discovery_insights"), list)
                else []
            ),
        )

    # --- Action Items ---
    urgency_priority_map = {
        "immediate": "high",
        "this_week": "medium",
        "next_week": "low",
        "nurture": "low",
    }
    category_type_map = {
        "proposal": "send_info",
        "demo": "schedule",
        "follow_up": "follow_up",
        "meeting": "schedule",
        "email": "send_info",
        "call": "follow_up",
    }
    action_items = []
    if call.action_items:
        for ai in call.action_items:
            urgency_val = (
                ai.urgency.value if hasattr(ai.urgency, "value") else str(ai.urgency)
            )
            category_val = ai.category or ""
            action_items.append(
                ActionItemResponse(
                    id=str(ai.id),
                    call_id=str(ai.call_id),
                    text=ai.description,
                    type=category_type_map.get(category_val.lower(), "other"),
                    urgency=urgency_val,
                    category=category_val,
                    priority=urgency_priority_map.get(urgency_val, "medium"),
                    due_date=None,
                    completed=ai.completed,
                    created_at=(
                        ai.created_at.isoformat() if ai.created_at else ""
                    ),
                )
            )

    # --- Path to Conversion ---
    raw_ptc = analysis.get("path_to_conversion")
    talking_points: list[str] = []
    if isinstance(raw_ptc, str) and raw_ptc:
        talking_points = [raw_ptc]
    elif isinstance(raw_ptc, list):
        talking_points = [str(p) for p in raw_ptc]

    raw_rebuttals = analysis.get("rebuttals") or []
    rebuttals = []
    if isinstance(raw_rebuttals, list):
        for r in raw_rebuttals:
            if isinstance(r, dict):
                rebuttals.append(
                    RebuttalItem(
                        objection=r.get("objection", ""),
                        rebuttal=r.get("rebuttal", r.get("response", "")),
                    )
                )

    follow_up_urgency = analysis.get("follow_up_urgency")
    next_best_action = analysis.get("call_summary", "")
    if talking_points and not next_best_action:
        next_best_action = talking_points[0]

    path_to_conversion = PathToConversionResponse(
        talking_points=talking_points,
        rebuttals=rebuttals,
        follow_up_urgency=follow_up_urgency or "nurture",
        next_best_action=next_best_action,
    )

    # --- Custom Fields ---
    custom_fields = []
    if call.custom_fields and isinstance(call.custom_fields, dict):
        for k, v in call.custom_fields.items():
            custom_fields.append(CustomFieldItem(key=k, value=str(v)))

    # --- Metadata Extraction ---
    metadata_extraction: dict[str, str] = {}
    raw_meta = (
        analysis.get("key_data_points")
        or analysis.get("extracted_metadata")
        or {}
    )
    if isinstance(raw_meta, dict):
        for k, v in raw_meta.items():
            if isinstance(v, list):
                metadata_extraction[k] = ", ".join(str(i) for i in v)
            else:
                metadata_extraction[k] = str(v)

    # --- Enhanced Analysis Fields ---
    escalation_kw_list: list = []
    raw_escalation = (
        call.escalation_keywords
        if call.escalation_keywords is not None
        else analysis.get("escalation_keywords", [])
    )
    if isinstance(raw_escalation, list):
        for ek in raw_escalation:
            if isinstance(ek, dict):
                escalation_kw_list.append(
                    EscalationKeyword(
                        keyword=ek.get("keyword", ""),
                        context=ek.get("context", ""),
                        severity=ek.get("severity", "low"),
                    )
                )

    raw_sentiment = (
        call.sentiment_keywords
        if call.sentiment_keywords is not None
        else analysis.get("sentiment", {})
    )
    if isinstance(raw_sentiment, dict):
        sentiment_data = SentimentData(
            positive_keywords=raw_sentiment.get("positive_keywords", []),
            negative_keywords=raw_sentiment.get("negative_keywords", []),
            overall_sentiment=raw_sentiment.get("overall_sentiment", "neutral"),
        )
    else:
        sentiment_data = SentimentData()

    call_tags_list: list[str] = (
        call.call_tags
        if call.call_tags is not None
        else analysis.get("call_tags", [])
    )
    if not isinstance(call_tags_list, list):
        call_tags_list = []

    # --- Sales Audit Keywords ---
    sales_audit_kw: SalesAuditKeywords | None = None
    raw_audit = (
        call.sales_audit_keywords
        if getattr(call, "sales_audit_keywords", None) is not None
        else analysis.get("sales_audit_keywords")
    )
    if isinstance(raw_audit, dict):
        audit_fields: dict[str, list[SalesAuditKeyword]] = {}
        for cat in (
            "compliance_violations",
            "missed_opportunities",
            "pricing_discounts",
            "competitor_mentions",
            "customer_pain_points",
            "commitment_closing",
            "objection_handling",
            "negative_reactions",
        ):
            items_raw = raw_audit.get(cat, [])
            kw_list: list[SalesAuditKeyword] = []
            if isinstance(items_raw, list):
                for item in items_raw:
                    if isinstance(item, dict):
                        kw_list.append(
                            SalesAuditKeyword(
                                keyword=item.get("keyword", ""),
                                context=item.get("context", ""),
                                severity=item.get("severity", "low"),
                            )
                        )
            audit_fields[cat] = kw_list
        sales_audit_kw = SalesAuditKeywords(**audit_fields)

    return CallResponse(
        id=call.id,
        tenant_id=call.tenant_id,
        recording_url=call.recording_url,
        duration=call.duration_seconds or 0,
        agent_name=call.agent.full_name if call.agent else "",
        agent_id=call.agent_id,
        lead_name=call.lead_name or "",
        lead_id=call.lead_id or "",
        lead_phone=call.lead_phone or "",
        source=call.source or "",
        status=(
            call.status.value if hasattr(call.status, "value") else str(call.status)
        ),
        custom_fields=custom_fields,
        transcript=transcript,
        quality_scores=quality_scores,
        overall_score=call.overall_score or 0,
        lead_intelligence=lead_intelligence,
        persona=persona_data,
        action_items=action_items,
        path_to_conversion=path_to_conversion,
        metadata_extraction=metadata_extraction,
        follow_up_urgency=follow_up_urgency,
        escalation_keywords=escalation_kw_list,
        sentiment=sentiment_data,
        call_tags=call_tags_list,
        sales_audit_keywords=sales_audit_kw,
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
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_active_user),
) -> CallResponse:
    """Upload an audio recording and queue it for transcription + analysis.

    The file is persisted to the configured upload directory (or S3 when
    configured).  A Celery task is dispatched to process the call
    asynchronously.  The response contains the newly created call record
    with ``status=uploaded``.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

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
                # RLS enforces tenant isolation; filter kept as defense-in-depth
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

        process_call.delay(str(call.id), tenant_id=str(current_user.tenant_id))
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CallResponse:
    """Receive a recording URL and metadata from an external CRM or dialer.

    The recording URL is stored and a Celery task is dispatched to download,
    transcribe, and analyze the call.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    # Resolve agent_id: prefer explicit ID, fall back to email lookup
    resolved_agent_id: UUID | None = body.agent_id
    if resolved_agent_id is None and body.agent_email:
        agent = (
            db.query(User)
            .filter(
                User.email == body.agent_email,
                # RLS enforces tenant isolation; filter kept as defense-in-depth
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

        process_call.delay(str(call.id), tenant_id=str(current_user.tenant_id))
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
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
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    query = (
        db.query(Call)
        .options(joinedload(Call.agent))
        # RLS enforces tenant isolation; filter kept as defense-in-depth
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
            agent_name=call.agent.full_name if call.agent else "",
            agent_id=call.agent_id,
            lead_name=call.lead_name or "",
            lead_id=call.lead_id or "",
            lead_phone=call.lead_phone or "",
            duration=call.duration_seconds or 0,
            overall_score=call.overall_score or 0,
            intent_classification=(
                call.intent_classification.value
                if call.intent_classification and hasattr(call.intent_classification, "value")
                else call.intent_classification
            ),
            intent_score=call.lead_intent_score or 0,
            status=call.status.value if hasattr(call.status, "value") else str(call.status),
            source=call.source or "",
            follow_up_urgency=(
                (call.analysis or {}).get("follow_up_urgency") if call.analysis else None
            ),
            call_tags=(
                call.call_tags if isinstance(call.call_tags, list) else []
            ),
            overall_sentiment=(
                (call.sentiment_keywords or {}).get("overall_sentiment")
                if isinstance(call.sentiment_keywords, dict)
                else None
            ),
            created_at=call.created_at,
        )
        for call in calls
    ]

    import math
    total_pages = max(1, math.ceil(total / page_size))

    return CallListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CallResponse:
    """Return the full call detail including transcript, quality scores,
    lead intelligence, persona analysis, and action items.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

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
            # RLS enforces tenant isolation; filter kept as defense-in-depth
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TranscriptResponse:
    """Return the speaker-labeled transcript for a specific call.

    Segments include speaker identification, start/end timestamps, and
    the transcribed text.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    call = (
        db.query(Call)
        .filter(
            Call.id == call_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin", "team_lead"]))],
) -> CallResponse:
    """Allow admin or team lead to manually correct quality scores.

    Each item in the ``scores`` list specifies a quality parameter ID,
    the corrected score (0--10), and a justification for the override.
    The overall weighted score is recalculated after applying all overrides.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

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
            # RLS enforces tenant isolation; filter kept as defense-in-depth
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
                # RLS enforces tenant isolation; filter kept as defense-in-depth
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
