"""Celery task for end-to-end call processing.

Orchestrates the full pipeline: transcription, LLM analysis, result
persistence, and optional outbound webhook delivery.  Each step updates the
call status so the frontend can display real-time progress.

The task is idempotent with respect to retries — it checks the current call
status before each phase and skips already-completed work.
"""

import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models.action_item import ActionItem, ActionUrgency
from app.models.call import Call, CallStatus, IntentClassification
from app.models.integration import Integration
from app.models.intent import CallIntentSignal, IntentSignal
from app.models.persona import CallPersona, PersonaType
from app.models.quality import CallQualityScore, QualityParameter
from app.services.analysis.llm_analyzer import (
    AnalysisError,
    AnalysisResult,
    CallAnalyzer,
    IntentSignalInput,
    PersonaTypeInput,
    QualityParameterInput,
)
from app.services.transcription import (
    TranscriptionResult,
    get_transcription_provider,
)
from app.services.transcription.base import TranscriptionError
from app.tasks import celery_app

logger = logging.getLogger(__name__)

# Valid urgency values that map to the ActionUrgency enum.
_URGENCY_MAP: Dict[str, ActionUrgency] = {
    "immediate": ActionUrgency.immediate,
    "this_week": ActionUrgency.this_week,
    "next_week": ActionUrgency.next_week,
    "nurture": ActionUrgency.nurture,
}

# Valid intent classification values.
_INTENT_MAP: Dict[str, IntentClassification] = {
    "hot": IntentClassification.hot,
    "warm": IntentClassification.warm,
    "cold": IntentClassification.cold,
}


def _get_sync_session() -> Session:
    """Create a synchronous database session for use within Celery tasks.

    Celery workers are synchronous, so we use the standard SQLAlchemy
    ``SessionLocal`` rather than any async session factory.
    """
    return SessionLocal()


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously.

    Celery tasks are synchronous, but our transcription and analysis services
    expose async interfaces.  This helper bridges the gap by running the
    coroutine in a dedicated event loop.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.tasks.call_processing.process_call",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_call(self: Any, call_id: str) -> Dict[str, Any]:
    """Process a call through the full transcription and analysis pipeline.

    This task:

    1. Loads the call record from the database.
    2. Transcribes the audio recording (Deepgram or Whisper).
    3. Runs LLM analysis against the transcript.
    4. Persists all results (quality scores, intent signals, persona, action items).
    5. Updates the call status to ``completed``.
    6. Optionally pushes results to configured outbound integrations.

    Parameters
    ----------
    call_id:
        UUID string of the :class:`Call` record to process.

    Returns
    -------
    dict
        Summary of the processing result including status and score.
    """
    db: Session = _get_sync_session()

    try:
        # ── 1. Load call ──────────────────────────────────────────────────
        call = _load_call(db, call_id)
        if call is None:
            logger.error("Call %s not found in database", call_id)
            return {"status": "error", "message": f"Call {call_id} not found"}

        logger.info(
            "Processing call %s (tenant=%s, status=%s)",
            call_id,
            call.tenant_id,
            call.status.value,
        )

        # ── 2. Transcription ─────────────────────────────────────────────
        audio_path = _resolve_audio_path(db, call)
        transcript_result = _transcribe_call(db, call, audio_path)

        # ── 3. Load tenant configuration ─────────────────────────────────
        quality_params = _load_quality_parameters(db, call.tenant_id)
        intent_signals_config = _load_intent_signals(db, call.tenant_id)
        persona_types_config = _load_persona_types(db, call.tenant_id)

        # ── 4. LLM analysis ──────────────────────────────────────────────
        analysis_result = _analyze_call(
            db,
            call,
            transcript_result,
            quality_params,
            intent_signals_config,
            persona_types_config,
        )

        # ── 5. Persist results ────────────────────────────────────────────
        _save_analysis_results(
            db,
            call,
            analysis_result,
            quality_params,
            intent_signals_config,
            persona_types_config,
        )

        # ── 6. Mark completed ─────────────────────────────────────────────
        call.status = CallStatus.completed
        call.error_message = None
        call.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Call %s processing completed — overall_score=%.1f intent=%s",
            call_id,
            call.overall_score or 0,
            call.intent_classification.value if call.intent_classification else "N/A",
        )

        # ── 7. Outbound integrations ─────────────────────────────────────
        _push_to_integrations(db, call, analysis_result)

        return {
            "status": "completed",
            "call_id": call_id,
            "overall_score": call.overall_score,
            "intent_classification": (
                call.intent_classification.value if call.intent_classification else None
            ),
        }

    except (TranscriptionError, AnalysisError) as exc:
        logger.exception("Call %s processing failed: %s", call_id, exc)
        _mark_failed(db, call_id, str(exc))
        # Retry on transient errors
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.exception("Call %s processing failed unexpectedly: %s", call_id, exc)
        _mark_failed(db, call_id, str(exc))
        # Only retry if we have retries left
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"status": "failed", "call_id": call_id, "error": str(exc)}

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def _load_call(db: Session, call_id: str) -> Optional[Call]:
    """Load a call record from the database by ID."""
    try:
        uid = uuid.UUID(call_id)
    except (ValueError, TypeError):
        logger.error("Invalid call ID format: %s", call_id)
        return None

    return db.query(Call).filter(Call.id == uid).first()


def _resolve_audio_path(db: Session, call: Call) -> str:
    """Determine the local file path for the audio recording.

    If the recording is available as a local file (``recording_file_path``),
    use that directly.  Otherwise, download the ``recording_url`` to a
    temporary file.

    Parameters
    ----------
    db:
        Database session (unused but kept for consistency).
    call:
        The call record.

    Returns
    -------
    str
        Absolute path to the audio file on disk.

    Raises
    ------
    TranscriptionError
        If no audio source is available or the download fails.
    """
    # Prefer local file
    if call.recording_file_path and os.path.exists(call.recording_file_path):
        return call.recording_file_path

    # Download from URL
    if call.recording_url:
        return _download_recording(call.recording_url)

    raise TranscriptionError(
        provider="system",
        message=f"No audio source available for call {call.id}",
    )


def _download_recording(url: str) -> str:
    """Download a recording from a URL to a temporary file.

    Returns the path to the downloaded file.  The caller is responsible for
    cleanup, but since Celery tasks are short-lived, OS temp cleanup handles
    this adequately.
    """
    logger.info("Downloading recording from %s", url)

    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

        # Determine file extension from content type or URL
        content_type = response.headers.get("content-type", "")
        ext = ".wav"
        if "mp3" in content_type or url.lower().endswith(".mp3"):
            ext = ".mp3"
        elif "mp4" in content_type or url.lower().endswith(".m4a"):
            ext = ".m4a"
        elif "webm" in content_type or url.lower().endswith(".webm"):
            ext = ".webm"

        # Write to temp file
        tmp = tempfile.NamedTemporaryFile(
            suffix=ext, prefix="saleslens_", delete=False
        )
        tmp.write(response.content)
        tmp.close()

        logger.info(
            "Recording downloaded to %s (%.1f MB)",
            tmp.name,
            len(response.content) / (1024 * 1024),
        )
        return tmp.name

    except httpx.HTTPError as exc:
        raise TranscriptionError(
            provider="system",
            message=f"Failed to download recording from {url}: {exc}",
        ) from exc


def _transcribe_call(
    db: Session,
    call: Call,
    audio_path: str,
) -> TranscriptionResult:
    """Transcribe the audio file and save the transcript to the call record.

    Updates the call status to ``transcribing`` and persists the transcript
    text and speaker-labelled segments once complete.
    """
    # Update status
    call.status = CallStatus.transcribing
    call.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Transcribing call %s from %s", call.id, audio_path)

    provider = get_transcription_provider()
    result: TranscriptionResult = _run_async(
        provider.transcribe(
            audio_path=audio_path,
            language=call.language or "en",
        )
    )

    # Save transcript
    call.transcript_raw = result.raw_text
    call.transcript_segments = [
        {
            "speaker": seg.speaker,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text,
        }
        for seg in result.segments
    ]

    # Update duration if not already set
    if not call.duration_seconds and result.duration_seconds:
        call.duration_seconds = int(result.duration_seconds)

    # Detect language if provider reports it
    if result.language:
        call.language = result.language

    db.commit()

    logger.info(
        "Transcription completed for call %s — %d segments, %.0f seconds",
        call.id,
        len(result.segments),
        result.duration_seconds,
    )

    return result


def _load_quality_parameters(
    db: Session,
    tenant_id: uuid.UUID,
) -> List[QualityParameter]:
    """Load active quality parameters for the tenant."""
    return (
        db.query(QualityParameter)
        .filter(
            QualityParameter.tenant_id == tenant_id,
            QualityParameter.is_active.is_(True),
        )
        .order_by(QualityParameter.display_order)
        .all()
    )


def _load_intent_signals(
    db: Session,
    tenant_id: uuid.UUID,
) -> List[IntentSignal]:
    """Load active intent signals for the tenant."""
    return (
        db.query(IntentSignal)
        .filter(
            IntentSignal.tenant_id == tenant_id,
            IntentSignal.is_active.is_(True),
        )
        .all()
    )


def _load_persona_types(
    db: Session,
    tenant_id: uuid.UUID,
) -> List[PersonaType]:
    """Load active persona types for the tenant."""
    return (
        db.query(PersonaType)
        .filter(
            PersonaType.tenant_id == tenant_id,
            PersonaType.is_active.is_(True),
        )
        .all()
    )


def _analyze_call(
    db: Session,
    call: Call,
    transcript_result: TranscriptionResult,
    quality_params: List[QualityParameter],
    intent_signals: List[IntentSignal],
    persona_types: List[PersonaType],
) -> AnalysisResult:
    """Run LLM analysis on the transcript and return structured results.

    Updates the call status to ``analyzing`` during processing.
    """
    call.status = CallStatus.analyzing
    call.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Analyzing call %s with LLM", call.id)

    # Build prompt inputs from DB models
    qp_inputs = [
        QualityParameterInput(
            name=p.name,
            description=p.description or "",
            weight=p.weight,
        )
        for p in quality_params
    ]

    is_inputs = [
        IntentSignalInput(
            name=s.name,
            description=s.description or "",
        )
        for s in intent_signals
    ]

    pt_inputs = [
        PersonaTypeInput(
            name=t.name,
            description=t.description or "",
        )
        for t in persona_types
    ]

    # Use the speaker-labelled transcript for better analysis context
    transcript_text = transcript_result.speaker_labeled_text or transcript_result.raw_text

    analyzer = CallAnalyzer()
    result: AnalysisResult = _run_async(
        analyzer.analyze_call(
            transcript=transcript_text,
            quality_parameters=qp_inputs,
            intent_signals=is_inputs,
            persona_types=pt_inputs,
        )
    )

    logger.info(
        "Analysis completed for call %s — overall_score=%.1f intent=%s",
        call.id,
        result.overall_score,
        result.intent_classification,
    )

    return result


def _save_analysis_results(
    db: Session,
    call: Call,
    result: AnalysisResult,
    quality_params: List[QualityParameter],
    intent_signals: List[IntentSignal],
    persona_types: List[PersonaType],
) -> None:
    """Persist all analysis results to the database.

    Creates related records (quality scores, intent signals, persona, action
    items) and updates the call's summary fields.
    """
    # ── Clean up any previous analysis results (in case of retry) ─────
    db.query(CallQualityScore).filter(CallQualityScore.call_id == call.id).delete()
    db.query(CallIntentSignal).filter(CallIntentSignal.call_id == call.id).delete()
    db.query(CallPersona).filter(CallPersona.call_id == call.id).delete()
    db.query(ActionItem).filter(ActionItem.call_id == call.id).delete()
    db.flush()

    # ── Quality scores ────────────────────────────────────────────────
    param_name_to_id: Dict[str, uuid.UUID] = {
        p.name.lower(): p.id for p in quality_params
    }

    for qs in result.quality_scores:
        param_id = param_name_to_id.get(qs.parameter_name.lower())
        if param_id is None:
            logger.warning(
                "Quality parameter %r from LLM not found in tenant config, skipping",
                qs.parameter_name,
            )
            continue

        db.add(
            CallQualityScore(
                call_id=call.id,
                parameter_id=param_id,
                score=max(0, min(10, qs.score)),  # Clamp to 0-10
                justification=qs.justification,
            )
        )

    # ── Intent signals ────────────────────────────────────────────────
    signal_name_to_id: Dict[str, uuid.UUID] = {
        s.name.lower(): s.id for s in intent_signals
    }

    for sig in result.intent_signals:
        signal_id = signal_name_to_id.get(sig.signal_name.lower())
        if signal_id is None:
            logger.warning(
                "Intent signal %r from LLM not found in tenant config, skipping",
                sig.signal_name,
            )
            continue

        db.add(
            CallIntentSignal(
                call_id=call.id,
                signal_id=signal_id,
                detected=sig.detected,
                details=sig.details,
            )
        )

    # ── Persona ───────────────────────────────────────────────────────
    persona_type_name_to_id: Dict[str, uuid.UUID] = {
        t.name.lower(): t.id for t in persona_types
    }
    matched_persona_id = persona_type_name_to_id.get(
        result.persona.type.lower()
    )

    db.add(
        CallPersona(
            call_id=call.id,
            persona_type_id=matched_persona_id,
            budget_score=max(0, min(10, int(result.persona.budget_score))),
            authority_score=max(0, min(10, int(result.persona.authority_score))),
            need_score=max(0, min(10, int(result.persona.need_score))),
            timeline_score=max(0, min(10, int(result.persona.timeline_score))),
            discovery_insights=result.persona.discovery_insights,
        )
    )

    # ── Action items ──────────────────────────────────────────────────
    for ai in result.action_items:
        urgency = _URGENCY_MAP.get(ai.urgency.lower(), ActionUrgency.this_week)
        db.add(
            ActionItem(
                call_id=call.id,
                description=ai.description,
                category=ai.category,
                urgency=urgency,
                completed=False,
            )
        )

    # ── Update call summary fields ────────────────────────────────────
    call.overall_score = max(0, min(100, result.overall_score))
    call.lead_intent_score = max(0, min(100, result.lead_intent_score))
    call.intent_classification = _INTENT_MAP.get(
        result.intent_classification.lower(),
        IntentClassification.cold,
    )
    call.analysis = result.to_dict()
    call.updated_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        "Analysis results saved for call %s — "
        "%d quality scores, %d intent signals, %d action items",
        call.id,
        len(result.quality_scores),
        len(result.intent_signals),
        len(result.action_items),
    )


# ---------------------------------------------------------------------------
# Integration push
# ---------------------------------------------------------------------------


def _push_to_integrations(
    db: Session,
    call: Call,
    result: AnalysisResult,
) -> None:
    """Push analysis results to all active outbound integrations for the tenant.

    Currently supports ``webhook`` type integrations.  Each integration's
    ``config`` should contain:
    - ``url``: The webhook endpoint URL.
    - ``headers`` (optional): Extra HTTP headers as a dict.
    - ``secret`` (optional): Shared secret for HMAC signature verification.
    """
    integrations = (
        db.query(Integration)
        .filter(
            Integration.tenant_id == call.tenant_id,
            Integration.is_active.is_(True),
            Integration.type == "webhook",
        )
        .all()
    )

    if not integrations:
        return

    payload = {
        "event": "call.analyzed",
        "call_id": str(call.id),
        "tenant_id": str(call.tenant_id),
        "agent_id": str(call.agent_id) if call.agent_id else None,
        "lead_id": call.lead_id,
        "lead_name": call.lead_name,
        "overall_score": call.overall_score,
        "lead_intent_score": call.lead_intent_score,
        "intent_classification": (
            call.intent_classification.value if call.intent_classification else None
        ),
        "analysis": result.to_dict(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    for integration in integrations:
        _send_webhook(integration, payload)


def _send_webhook(
    integration: Integration,
    payload: Dict[str, Any],
) -> None:
    """Send a webhook payload to the configured URL.

    Logs warnings on failure but does not raise — outbound webhook failures
    should not block call processing.
    """
    config = integration.config or {}
    url = config.get("url")

    if not url:
        logger.warning(
            "Integration %s (%s) has no URL configured, skipping",
            integration.id,
            integration.name,
        )
        return

    headers = {"Content-Type": "application/json"}
    extra_headers = config.get("headers", {})
    if isinstance(extra_headers, dict):
        headers.update(extra_headers)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info(
            "Webhook delivered to %s — status=%d",
            integration.name,
            response.status_code,
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Webhook delivery to %s (%s) failed: %s",
            integration.name,
            url,
            exc,
        )
    except Exception as exc:
        logger.warning(
            "Unexpected error delivering webhook to %s: %s",
            integration.name,
            exc,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mark_failed(db: Session, call_id: str, error_message: str) -> None:
    """Set a call's status to ``failed`` with the given error message."""
    try:
        uid = uuid.UUID(call_id)
        call = db.query(Call).filter(Call.id == uid).first()
        if call:
            call.status = CallStatus.failed
            call.error_message = error_message[:2000]  # Truncate very long errors
            call.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        logger.exception("Failed to update call %s status to failed", call_id)
        db.rollback()
