"""Tests for transcription providers: Deepgram and Whisper with mocked APIs."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from app.services.transcription.base import (
    TranscriptionError,
    TranscriptionResult,
    TranscriptSegment,
)
from tests.fixtures.audio import create_dummy_wav


def _run(coro):
    """Helper to run async functions in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestDeepgramProvider:
    """Tests for DeepgramProvider with mocked Deepgram SDK."""

    def _make_provider(self):
        from app.services.transcription.deepgram_provider import DeepgramProvider
        return DeepgramProvider()

    def test_deepgram_provider_success(self, tmp_path):
        """Mock Deepgram SDK and verify TranscriptionResult."""
        audio_file = create_dummy_wav(tmp_path / "test.wav")

        mock_response = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Hello, this is a test call.",
                    }],
                }],
                "utterances": [
                    {"speaker": 0, "start": 0.0, "end": 3.0, "transcript": "Hello, this is a test call."},
                    {"speaker": 1, "start": 3.5, "end": 6.0, "transcript": "Hi, thanks for calling."},
                ],
            },
            "metadata": {"duration": 6.0},
        }

        provider = self._make_provider()

        with patch("deepgram.DeepgramClient") as MockDG:
            mock_client = MagicMock()
            MockDG.return_value = mock_client
            mock_client.listen.rest.v.return_value.transcribe_file.return_value = mock_response

            result = _run(provider.transcribe(str(audio_file), language="en"))

        assert isinstance(result, TranscriptionResult)
        assert result.raw_text == "Hello, this is a test call."
        assert len(result.segments) == 2
        assert result.segments[0].speaker == "Agent"
        assert result.segments[1].speaker == "Customer"
        assert result.duration_seconds == 6.0

    def test_deepgram_provider_diarization(self, tmp_path):
        """Verify speaker labels from diarization."""
        audio_file = create_dummy_wav(tmp_path / "test.wav")

        mock_response = {
            "results": {
                "channels": [{
                    "alternatives": [{"transcript": "Test"}],
                }],
                "utterances": [
                    {"speaker": 0, "start": 0.0, "end": 2.0, "transcript": "I am the agent"},
                    {"speaker": 1, "start": 2.5, "end": 5.0, "transcript": "I am the customer"},
                    {"speaker": 0, "start": 5.5, "end": 8.0, "transcript": "Agent speaking again"},
                ],
            },
            "metadata": {"duration": 8.0},
        }

        provider = self._make_provider()

        with patch("deepgram.DeepgramClient") as MockDG:
            mock_client = MagicMock()
            MockDG.return_value = mock_client
            mock_client.listen.rest.v.return_value.transcribe_file.return_value = mock_response

            result = _run(provider.transcribe(str(audio_file)))

        assert result.segments[0].speaker == "Agent"
        assert result.segments[1].speaker == "Customer"
        assert result.segments[2].speaker == "Agent"

    def test_deepgram_provider_file_not_found(self):
        """Non-existent file raises TranscriptionError."""
        provider = self._make_provider()

        with patch("deepgram.DeepgramClient"):
            with pytest.raises(TranscriptionError, match="not found"):
                _run(provider.transcribe("/nonexistent/file.wav"))

    def test_deepgram_provider_api_error(self, tmp_path):
        """API error raises TranscriptionError."""
        audio_file = create_dummy_wav(tmp_path / "test.wav")
        provider = self._make_provider()

        with patch("deepgram.DeepgramClient") as MockDG:
            mock_client = MagicMock()
            MockDG.return_value = mock_client
            mock_client.listen.rest.v.return_value.transcribe_file.side_effect = Exception("API error")

            with pytest.raises(TranscriptionError, match="Transcription failed"):
                _run(provider.transcribe(str(audio_file)))

    def test_deepgram_provider_no_api_key(self):
        """Missing API key raises TranscriptionError on init."""
        import app.config
        original = app.config.settings.DEEPGRAM_API_KEY
        try:
            app.config.settings.DEEPGRAM_API_KEY = ""
            from app.services.transcription.deepgram_provider import DeepgramProvider
            with pytest.raises(TranscriptionError, match="not configured"):
                DeepgramProvider()
        finally:
            app.config.settings.DEEPGRAM_API_KEY = original


class TestWhisperProvider:
    """Tests for WhisperProvider with mocked OpenAI SDK."""

    def _make_provider(self):
        from app.services.transcription.whisper_provider import WhisperProvider
        return WhisperProvider()

    def test_whisper_provider_success(self, tmp_path):
        """Mock OpenAI SDK and verify TranscriptionResult."""
        audio_file = create_dummy_wav(tmp_path / "test.wav")

        mock_response = {
            "text": "Hello from whisper transcription.",
            "duration": 10.0,
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hello from whisper"},
                {"start": 5.5, "end": 10.0, "text": "transcription."},
            ],
        }

        provider = self._make_provider()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            result = _run(provider.transcribe(str(audio_file)))

        assert isinstance(result, TranscriptionResult)
        assert "Hello from whisper" in result.raw_text
        assert len(result.segments) == 2
        assert result.duration_seconds == 10.0

    def test_whisper_provider_no_diarization(self, tmp_path):
        """All speakers should be 'Unknown' since Whisper has no diarization."""
        audio_file = create_dummy_wav(tmp_path / "test.wav")

        mock_response = {
            "text": "Test",
            "duration": 5.0,
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Segment one"},
                {"start": 2.5, "end": 5.0, "text": "Segment two"},
            ],
        }

        provider = self._make_provider()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            result = _run(provider.transcribe(str(audio_file)))

        for seg in result.segments:
            assert seg.speaker == "Unknown"

    def test_whisper_provider_file_not_found(self):
        """Non-existent file raises TranscriptionError."""
        provider = self._make_provider()

        with patch("openai.OpenAI"):
            with pytest.raises(TranscriptionError, match="not found"):
                _run(provider.transcribe("/nonexistent/file.wav"))


class TestTranscriptionFactory:
    """Tests for the factory function."""

    def test_transcription_factory_deepgram(self):
        from app.services.transcription.factory import get_transcription_provider
        from app.services.transcription.deepgram_provider import DeepgramProvider
        provider = get_transcription_provider("deepgram")
        assert isinstance(provider, DeepgramProvider)

    def test_transcription_factory_whisper(self):
        from app.services.transcription.factory import get_transcription_provider
        from app.services.transcription.whisper_provider import WhisperProvider
        provider = get_transcription_provider("whisper")
        assert isinstance(provider, WhisperProvider)


class TestSpeakerLabeledText:
    """Tests for the labeled text generation."""

    def test_speaker_labeled_text_generation(self):
        """Verify [MM:SS] format in speaker_labeled_text."""
        segments = [
            TranscriptSegment(speaker="Agent", start_time=0.0, end_time=5.0, text="Hello"),
            TranscriptSegment(speaker="Customer", start_time=65.0, end_time=70.0, text="Hi there"),
        ]
        result = TranscriptionResult(
            raw_text="Hello Hi there",
            segments=segments,
            duration_seconds=70.0,
            language="en",
        )
        assert "[00:00] Agent: Hello" in result.speaker_labeled_text
        assert "[01:05] Customer: Hi there" in result.speaker_labeled_text
