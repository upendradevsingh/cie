"""OpenAI Whisper API transcription provider.

This is the **fallback** transcription backend for SalesLens.  It uses
the OpenAI ``audio/transcriptions`` endpoint (Whisper) to transcribe
audio files.

Limitations
-----------
* **No native speaker diarization** — the Whisper API does not assign
  speaker labels.  All segments are attributed to ``"Unknown"`` and a
  downstream diarization step (or manual correction) would be required
  to separate Agent from Customer.  This limitation is noted in the
  ``TranscriptSegment.speaker`` field.
* Whisper has a 25 MB upload limit per request.  Larger files should be
  split before uploading (not implemented here — callers are expected to
  enforce file-size limits at the upload stage).
"""

import logging
from pathlib import Path
from typing import Dict, List

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.services.transcription.base import (
    TranscriptionError,
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

# Map internal language codes to Whisper-supported ISO-639-1 codes.
_LANGUAGE_MAP: Dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "hinglish": "hi",  # Whisper handles code-mixed Hindi/English reasonably
}


class WhisperProvider(TranscriptionProvider):
    """Transcription provider backed by the OpenAI Whisper API.

    .. warning::

        Whisper does **not** perform speaker diarization.  All transcript
        segments will have ``speaker="Unknown"``.  For accurate Agent /
        Customer attribution, use the Deepgram provider or add a
        post-processing diarization step.
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise TranscriptionError(
                provider="whisper",
                message="OPENAI_API_KEY is not configured",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def transcribe(
        self,
        audio_path: str,
        language: str = "en",
    ) -> TranscriptionResult:
        """Transcribe *audio_path* via the OpenAI Whisper API.

        Parameters
        ----------
        audio_path:
            Path to the audio file on disk.
        language:
            Language code (``"en"``, ``"hi"``, ``"hinglish"``).

        Returns
        -------
        TranscriptionResult
            Note: ``segments[*].speaker`` will always be ``"Unknown"``
            because Whisper does not perform diarization.

        Raises
        ------
        TranscriptionError
            On API or file-system errors.
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TranscriptionError(
                provider="whisper",
                message=f"openai SDK is not installed: {exc}",
            )

        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise TranscriptionError(
                provider="whisper",
                message=f"Audio file not found: {audio_path}",
            )

        whisper_language = _LANGUAGE_MAP.get(language, "en")

        logger.info(
            "Whisper transcription started — file=%s lang=%s",
            audio_path,
            whisper_language,
        )

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            with open(audio_path, "rb") as fh:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=fh,
                    language=whisper_language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            return self._parse_response(response, language=language)

        except TranscriptionError:
            raise
        except Exception as exc:
            logger.exception("Whisper transcription failed for %s", audio_path)
            raise TranscriptionError(
                provider="whisper",
                message=f"Transcription failed: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response: object,
        language: str,
    ) -> TranscriptionResult:
        """Convert the Whisper API response into a ``TranscriptionResult``.

        Whisper returns segments with start/end timestamps but without
        speaker information.  Each segment is labelled ``"Unknown"`` to
        signal that downstream processing is needed for diarization.
        """
        # The verbose_json response has .text, .segments, .duration etc.
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif isinstance(response, dict):
            data = response
        else:
            data = {"text": str(response)}

        raw_text: str = data.get("text", "")
        duration: float = float(data.get("duration", 0.0))
        api_segments: List[dict] = data.get("segments", [])

        segments: List[TranscriptSegment] = []
        for seg in api_segments:
            segments.append(
                TranscriptSegment(
                    # NOTE: Whisper does not provide speaker diarization.
                    # All segments are attributed to "Unknown".  A
                    # post-processing pipeline could use voice embeddings
                    # or channel separation to assign Agent/Customer labels.
                    speaker="Unknown",
                    start_time=float(seg.get("start", 0.0)),
                    end_time=float(seg.get("end", 0.0)),
                    text=seg.get("text", "").strip(),
                )
            )

        if not duration and segments:
            duration = max(seg.end_time for seg in segments)

        return TranscriptionResult(
            raw_text=raw_text,
            segments=segments,
            duration_seconds=duration,
            language=language,
        )
