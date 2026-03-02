"""Transcription service package.

Provides a provider-agnostic interface for converting audio recordings into
speaker-diarised transcripts.  Supported backends:

* **Deepgram Nova-3** — primary provider with native diarization.
* **OpenAI Whisper** — fallback provider (no native diarization).

Use :func:`factory.get_transcription_provider` to obtain a concrete provider
instance based on the configured ``TRANSCRIPTION_PROVIDER`` setting.
"""

from app.services.transcription.base import (
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptSegment,
)
from app.services.transcription.factory import get_transcription_provider

__all__ = [
    "TranscriptionProvider",
    "TranscriptionResult",
    "TranscriptSegment",
    "get_transcription_provider",
]
