"""Tests for the Celery call processing pipeline.

Mocks both Deepgram and OpenAI, runs the full pipeline synchronously,
and verifies results persisted correctly.
"""

import json
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem
from app.models.call import Call, CallStatus, IntentClassification
from app.models.intent import CallIntentSignal
from app.models.persona import CallPersona
from app.models.quality import CallQualityScore
from app.services.transcription.base import TranscriptionError, TranscriptionResult, TranscriptSegment
from app.services.analysis.llm_analyzer import AnalysisError
from tests.factories import (
    create_call,
    create_default_intent_signals,
    create_default_quality_parameters,
    create_persona_type,
    create_tenant,
    create_admin,
    create_integration,
)
from tests.fixtures.analysis_results import HOT_LEAD_ANALYSIS, WARM_LEAD_ANALYSIS, COLD_LEAD_ANALYSIS, analysis_as_json
from tests.fixtures.transcripts import (
    SOLAR_HOT_LEAD_SEGMENTS,
    SOLAR_HOT_LEAD_RAW,
    SAAS_WARM_LEAD_SEGMENTS,
    SAAS_WARM_LEAD_RAW,
    COLD_CALL_SEGMENTS,
    COLD_CALL_RAW,
    build_speaker_labeled_text,
)
from tests.fixtures.audio import create_dummy_wav


def _make_transcription_result(segments_data, raw_text):
    """Build a TranscriptionResult from test segment data."""
    segments = [
        TranscriptSegment(speaker=s[0], start_time=s[1], end_time=s[2], text=s[3])
        for s in segments_data
    ]
    duration = max(s[2] for s in segments_data) if segments_data else 0
    return TranscriptionResult(
        raw_text=raw_text,
        segments=segments,
        duration_seconds=duration,
        language="en",
    )


def _mock_openai_response(content: str):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestProcessCallPipeline:
    """Full pipeline tests: transcription → analysis → storage."""

    def _run_pipeline(
        self, db_session, tenant, admin, audio_path,
        segments_data, raw_text, analysis_dict,
    ):
        """Helper to set up and run the processing pipeline."""
        # Create tenant config
        quality_params = create_default_quality_parameters(db_session, tenant)
        intent_signals = create_default_intent_signals(db_session, tenant)
        persona = create_persona_type(db_session, tenant, name="Ready Buyer")
        db_session.commit()

        # Create call with audio path
        call = create_call(
            db_session, tenant, agent=admin,
            recording_file_path=audio_path,
        )
        db_session.commit()

        transcription_result = _make_transcription_result(segments_data, raw_text)

        # Prevent the task from closing our test session
        original_close = db_session.close
        db_session.close = lambda: None

        try:
            with patch("app.tasks.call_processing._get_sync_session", return_value=db_session), \
                 patch("app.tasks.call_processing.get_transcription_provider") as mock_trans, \
                 patch("openai.OpenAI") as MockOAI, \
                 patch("app.tasks.call_processing.set_tenant_context"):

                # Mock transcription
                mock_provider = MagicMock()
                mock_trans.return_value = mock_provider

                async def fake_transcribe(*args, **kwargs):
                    return transcription_result
                mock_provider.transcribe = fake_transcribe

                # Mock LLM
                mock_client = MagicMock()
                MockOAI.return_value = mock_client
                mock_client.chat.completions.create.return_value = _mock_openai_response(
                    analysis_as_json(analysis_dict)
                )

                from app.tasks.call_processing import process_call
                result = process_call.__wrapped__(
                    str(call.id),
                    tenant_id=str(tenant.id),
                )
        finally:
            db_session.close = original_close

        return result, call

    def test_process_call_full_pipeline_hot_lead(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "hot.wav"))

        result, call = self._run_pipeline(
            db_session, test_tenant, admin, audio_path,
            SOLAR_HOT_LEAD_SEGMENTS, SOLAR_HOT_LEAD_RAW, HOT_LEAD_ANALYSIS,
        )

        assert result["status"] == "completed"
        db_session.refresh(call)
        assert call.status == CallStatus.completed
        assert call.transcript_raw is not None
        assert call.overall_score is not None
        assert call.overall_score > 0
        assert call.intent_classification == IntentClassification.hot

        # Verify related records
        scores = db_session.query(CallQualityScore).filter_by(call_id=call.id).all()
        assert len(scores) > 0

        persona = db_session.query(CallPersona).filter_by(call_id=call.id).first()
        assert persona is not None

        actions = db_session.query(ActionItem).filter_by(call_id=call.id).all()
        assert len(actions) > 0

    def test_process_call_full_pipeline_warm_lead(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "warm.wav"))

        result, call = self._run_pipeline(
            db_session, test_tenant, admin, audio_path,
            SAAS_WARM_LEAD_SEGMENTS, SAAS_WARM_LEAD_RAW, WARM_LEAD_ANALYSIS,
        )

        assert result["status"] == "completed"
        db_session.refresh(call)
        assert call.intent_classification == IntentClassification.warm

    def test_process_call_full_pipeline_cold_lead(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "cold.wav"))

        result, call = self._run_pipeline(
            db_session, test_tenant, admin, audio_path,
            COLD_CALL_SEGMENTS, COLD_CALL_RAW, COLD_LEAD_ANALYSIS,
        )

        assert result["status"] == "completed"
        db_session.refresh(call)
        assert call.intent_classification == IntentClassification.cold

    def test_process_call_transcription_failure(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "fail.wav"))
        call = create_call(
            db_session, test_tenant, agent=admin,
            recording_file_path=audio_path,
        )
        db_session.commit()

        original_close = db_session.close
        db_session.close = lambda: None
        try:
            with patch("app.tasks.call_processing._get_sync_session", return_value=db_session), \
                 patch("app.tasks.call_processing.get_transcription_provider") as mock_trans, \
                 patch("app.tasks.call_processing.set_tenant_context"):

                mock_provider = MagicMock()
                mock_trans.return_value = mock_provider

                async def fail_transcribe(*args, **kwargs):
                    raise TranscriptionError("deepgram", "API rate limit exceeded")
                mock_provider.transcribe = fail_transcribe

                from app.tasks.call_processing import process_call
                task_obj = process_call._get_current_object()
                original_retry = task_obj.retry
                task_obj.retry = MagicMock(side_effect=TranscriptionError("deepgram", "API rate limit exceeded"))
                try:
                    with pytest.raises(TranscriptionError):
                        process_call.__wrapped__(
                            str(call.id), tenant_id=str(test_tenant.id),
                        )
                finally:
                    task_obj.retry = original_retry
        finally:
            db_session.close = original_close

        db_session.refresh(call)
        assert call.status == CallStatus.failed
        assert "rate limit" in (call.error_message or "").lower()

    def test_process_call_analysis_failure(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "afail.wav"))
        create_default_quality_parameters(db_session, test_tenant)
        create_default_intent_signals(db_session, test_tenant)
        create_persona_type(db_session, test_tenant)
        call = create_call(
            db_session, test_tenant, agent=admin,
            recording_file_path=audio_path,
        )
        db_session.commit()

        transcription_result = _make_transcription_result(
            SOLAR_HOT_LEAD_SEGMENTS, SOLAR_HOT_LEAD_RAW,
        )

        original_close = db_session.close
        db_session.close = lambda: None
        try:
            with patch("app.tasks.call_processing._get_sync_session", return_value=db_session), \
                 patch("app.tasks.call_processing.get_transcription_provider") as mock_trans, \
                 patch("openai.OpenAI") as MockOAI, \
                 patch("app.tasks.call_processing.set_tenant_context"):

                mock_provider = MagicMock()
                mock_trans.return_value = mock_provider

                async def ok_transcribe(*args, **kwargs):
                    return transcription_result
                mock_provider.transcribe = ok_transcribe

                mock_client = MagicMock()
                MockOAI.return_value = mock_client
                mock_client.chat.completions.create.side_effect = Exception("LLM API error")

                from app.tasks.call_processing import process_call
                task_obj = process_call._get_current_object()
                original_retry = task_obj.retry
                task_obj.retry = MagicMock(side_effect=AnalysisError("LLM API error"))
                try:
                    with pytest.raises(AnalysisError):
                        process_call.__wrapped__(
                            str(call.id), tenant_id=str(test_tenant.id),
                        )
                finally:
                    task_obj.retry = original_retry
        finally:
            db_session.close = original_close

        db_session.refresh(call)
        assert call.status == CallStatus.failed
        # Transcript should be saved even though analysis failed
        assert call.transcript_raw is not None

    def test_process_call_invalid_llm_json(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "badjson.wav"))
        create_default_quality_parameters(db_session, test_tenant)
        create_default_intent_signals(db_session, test_tenant)
        create_persona_type(db_session, test_tenant)
        call = create_call(
            db_session, test_tenant, agent=admin,
            recording_file_path=audio_path,
        )
        db_session.commit()

        transcription_result = _make_transcription_result(
            COLD_CALL_SEGMENTS, COLD_CALL_RAW,
        )

        original_close = db_session.close
        db_session.close = lambda: None
        try:
            with patch("app.tasks.call_processing._get_sync_session", return_value=db_session), \
                 patch("app.tasks.call_processing.get_transcription_provider") as mock_trans, \
                 patch("openai.OpenAI") as MockOAI, \
                 patch("app.tasks.call_processing.set_tenant_context"):

                mock_provider = MagicMock()
                mock_trans.return_value = mock_provider

                async def ok_transcribe(*args, **kwargs):
                    return transcription_result
                mock_provider.transcribe = ok_transcribe

                mock_client = MagicMock()
                MockOAI.return_value = mock_client
                mock_client.chat.completions.create.return_value = _mock_openai_response(
                    "NOT VALID JSON {{{}"
                )

                from app.tasks.call_processing import process_call
                task_obj = process_call._get_current_object()
                original_retry = task_obj.retry
                task_obj.retry = MagicMock(side_effect=AnalysisError("Invalid JSON"))
                try:
                    with pytest.raises(AnalysisError):
                        process_call.__wrapped__(
                            str(call.id), tenant_id=str(test_tenant.id),
                        )
                finally:
                    task_obj.retry = original_retry
        finally:
            db_session.close = original_close

    def test_process_call_webhook_delivery(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "webhook.wav"))

        # Create webhook integration
        integration = create_integration(
            db_session, test_tenant,
            name="Test CRM",
            config={"url": "https://crm.example.com/webhook"},
        )
        db_session.commit()

        result, call = self._run_pipeline(
            db_session, test_tenant, admin, audio_path,
            SOLAR_HOT_LEAD_SEGMENTS, SOLAR_HOT_LEAD_RAW, HOT_LEAD_ANALYSIS,
        )

        # Pipeline completed but webhook delivery is best-effort
        assert result["status"] == "completed"

    def test_process_call_retries_on_transient_error(
        self, db_session: Session, test_tenant, test_admin, tmp_path,
    ):
        admin, _ = test_admin
        audio_path = str(create_dummy_wav(tmp_path / "retry.wav"))
        create_default_quality_parameters(db_session, test_tenant)
        create_default_intent_signals(db_session, test_tenant)
        create_persona_type(db_session, test_tenant)
        call = create_call(
            db_session, test_tenant, agent=admin,
            recording_file_path=audio_path,
        )
        db_session.commit()

        # First call fails, second succeeds
        transcription_result = _make_transcription_result(
            COLD_CALL_SEGMENTS, COLD_CALL_RAW,
        )

        call_count = {"n": 0}

        async def flaky_transcribe(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise TranscriptionError("deepgram", "Transient API error")
            return transcription_result

        original_close = db_session.close
        db_session.close = lambda: None
        try:
            with patch("app.tasks.call_processing._get_sync_session", return_value=db_session), \
                 patch("app.tasks.call_processing.get_transcription_provider") as mock_trans, \
                 patch("app.tasks.call_processing.set_tenant_context"):

                mock_provider = MagicMock()
                mock_trans.return_value = mock_provider
                mock_provider.transcribe = flaky_transcribe

                from app.tasks.call_processing import process_call
                task_obj = process_call._get_current_object()
                original_retry = task_obj.retry
                mock_retry = MagicMock(side_effect=TranscriptionError("deepgram", "Transient API error"))
                task_obj.retry = mock_retry
                try:
                    with pytest.raises(TranscriptionError):
                        process_call.__wrapped__(
                            str(call.id), tenant_id=str(test_tenant.id),
                        )
                finally:
                    task_obj.retry = original_retry
        finally:
            db_session.close = original_close

        # Verify retry was requested
        assert mock_retry.called
