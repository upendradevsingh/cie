"""Celery task: ingest → transcribe (if audio) → extract → persist → callback."""
import logging
import time
import uuid
from datetime import datetime, timezone

import httpx

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_conversation", bind=True, max_retries=2)
def process_conversation(self, conversation_id: str) -> dict:
    """Process a conversation: transcribe (if needed) → extract → persist."""
    from app.db.session import SessionLocal
    from app.models.conversation import Conversation, ConversationStatus
    from app.models.extraction import Extraction
    from app.profiles import ProfileLoader
    from app.services.extraction.engine import ExtractionEngine

    db = SessionLocal()
    start_time = time.time()

    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == uuid.UUID(conversation_id)
        ).first()

        if not conversation:
            logger.error("Conversation %s not found", conversation_id)
            return {"error": "not_found"}

        logger.info(
            "Processing conversation %s profile=%s source=%s",
            conversation_id,
            conversation.profile_id,
            conversation.source,
        )

        # Step 1: Transcribe if audio and no transcript yet
        if conversation.audio_url and not conversation.transcript_raw:
            conversation.status = ConversationStatus.transcribing
            db.commit()

            try:
                transcript_result = _transcribe(conversation)
                conversation.transcript_raw = transcript_result.raw_text
                conversation.transcript_segments = [
                    {
                        "speaker": seg.speaker,
                        "text": seg.text,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                    }
                    for seg in transcript_result.segments
                ]
                conversation.duration_seconds = transcript_result.duration_seconds
                db.commit()
            except Exception as e:
                logger.error("Transcription failed for %s: %s", conversation_id, e)
                conversation.status = ConversationStatus.failed
                conversation.error_message = f"Transcription failed: {e}"
                db.commit()
                return {"error": "transcription_failed", "detail": str(e)}

        # Step 2: Ensure we have a transcript
        transcript = conversation.transcript_raw
        if not transcript:
            conversation.status = ConversationStatus.failed
            conversation.error_message = "No transcript available for extraction"
            db.commit()
            return {"error": "no_transcript"}

        # Step 3: Extract
        conversation.status = ConversationStatus.extracting
        db.commit()

        try:
            loader = ProfileLoader()
            profile = loader.load(conversation.profile_id)
            engine = ExtractionEngine(profile, extraction_mode=profile.extraction_mode)

            # Extract meeting_type from source_metadata if provided
            meeting_type = None
            if conversation.source_metadata:
                meeting_type = conversation.source_metadata.get("meeting_type")

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    engine.extract(
                        transcript,
                        conversation.participants or [],
                        segments=conversation.transcript_segments,
                        meeting_type=meeting_type,
                        db=db,
                        tenant_id=conversation.tenant_id,
                    )
                )
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as e:
            logger.error("Extraction failed for %s: %s", conversation_id, e)
            conversation.status = ConversationStatus.failed
            conversation.error_message = f"Extraction failed: {e}"
            db.commit()
            return {"error": "extraction_failed", "detail": str(e)}

        # Step 4: Persist extractions
        for item in result.extractions:
            extraction = Extraction(
                conversation_id=conversation.id,
                tenant_id=conversation.tenant_id,
                extraction_type=item.extraction_type,
                description=item.description,
                confidence=item.confidence,
                attributed_to=item.attributed_to,
                evidence=item.evidence,
                attributes=item.attributes,
            )
            db.add(extraction)

        # Update conversation
        conversation.summary = result.summary
        conversation.status = ConversationStatus.completed
        conversation.processing_time_ms = int((time.time() - start_time) * 1000)
        db.commit()

        logger.info(
            "Conversation %s completed: extractions=%d tokens=%d ms=%d",
            conversation_id,
            len(result.extractions),
            result.tokens_used,
            result.duration_ms,
        )

        # Step 5: Callback if configured
        if conversation.callback_url:
            _send_callback(conversation.callback_url, conversation_id, result)

        return {
            "conversation_id": conversation_id,
            "extractions": len(result.extractions),
            "tokens_used": result.tokens_used,
        }

    except Exception as e:
        logger.error("Unexpected error processing %s: %s", conversation_id, e, exc_info=True)
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == uuid.UUID(conversation_id)
            ).first()
            if conversation:
                conversation.status = ConversationStatus.failed
                conversation.error_message = str(e)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()


def _transcribe(conversation):
    """Transcribe audio for a conversation."""
    from app.services.transcription.factory import get_transcription_provider
    import asyncio

    provider = get_transcription_provider()
    audio_path = conversation.audio_file_path or conversation.audio_url
    return asyncio.run(provider.transcribe(audio_path, language=conversation.language))


def _send_callback(callback_url: str, conversation_id: str, result) -> None:
    """Send webhook callback with extraction results."""
    try:
        payload = {
            "conversation_id": conversation_id,
            "status": "completed",
            "extractions_count": len(result.extractions),
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(callback_url, json=payload)
            response.raise_for_status()
        logger.info("Callback sent to %s for conversation %s", callback_url, conversation_id)
    except Exception as e:
        logger.warning("Callback failed for %s: %s", conversation_id, e)
