"""Deepgram Nova-3 transcription provider with speaker diarization.

This is the primary transcription backend for SalesLens.  It uses the
Deepgram SDK to submit audio files for transcription with the following
features enabled:

* Speaker diarization (speakers mapped to "Agent" / "Customer")
* Smart formatting and punctuation
* Multi-language support (English, Hindi, Hinglish)
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

# Map internal language codes to Deepgram-supported BCP-47 codes.
_LANGUAGE_MAP: Dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "hinglish": "hi",  # Deepgram handles code-mixed Hindi/English under "hi"
}

# Speaker index to label mapping.  Speaker 0 is assumed to be the sales
# agent (the one who initiates the call).
_SPEAKER_LABELS: Dict[int, str] = {
    0: "Agent",
    1: "Customer",
}


class DeepgramProvider(TranscriptionProvider):
    """Transcription provider backed by the Deepgram Nova-3 API."""

    def __init__(self) -> None:
        if not settings.DEEPGRAM_API_KEY:
            raise TranscriptionError(
                provider="deepgram",
                message="DEEPGRAM_API_KEY is not configured",
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
        """Send *audio_path* to Deepgram and return a diarised transcript.

        Parameters
        ----------
        audio_path:
            Path to the audio file on disk.
        language:
            Language code (``"en"``, ``"hi"``, ``"hinglish"``).

        Returns
        -------
        TranscriptionResult

        Raises
        ------
        TranscriptionError
            On API or file-system errors.
        """
        # Lazy import so that the SDK is only required at call time.
        try:
            from deepgram import DeepgramClient, PrerecordedOptions, FileSource
        except ImportError as exc:
            raise TranscriptionError(
                provider="deepgram",
                message=f"deepgram-sdk is not installed: {exc}",
            )

        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise TranscriptionError(
                provider="deepgram",
                message=f"Audio file not found: {audio_path}",
            )

        dg_language = _LANGUAGE_MAP.get(language, "en")

        logger.info(
            "Deepgram transcription started — file=%s lang=%s",
            audio_path,
            dg_language,
        )

        try:
            client = DeepgramClient(settings.DEEPGRAM_API_KEY)

            with open(audio_path, "rb") as fh:
                buffer_data = fh.read()

            payload: FileSource = {"buffer": buffer_data}

            options = PrerecordedOptions(
                model="nova-3",
                language=dg_language,
                smart_format=True,
                punctuate=True,
                diarize=True,
                utterances=True,
                paragraphs=True,
            )

            response = client.listen.rest.v("1").transcribe_file(
                payload,
                options,
            )

            return self._parse_response(response, language=language)

        except TranscriptionError:
            raise
        except Exception as exc:
            logger.exception("Deepgram transcription failed for %s", audio_path)
            raise TranscriptionError(
                provider="deepgram",
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
        """Convert the Deepgram API response into a ``TranscriptionResult``.

        The method handles both the structured SDK response object and a
        plain ``dict`` (for easier testing).
        """
        # Support both dict and object access patterns from the SDK.
        if hasattr(response, "to_dict"):
            data = response.to_dict()
        elif isinstance(response, dict):
            data = response
        else:
            data = response.__dict__ if hasattr(response, "__dict__") else {}

        results = data.get("results", {})
        channels = results.get("channels", [])

        if not channels:
            raise TranscriptionError(
                provider="deepgram",
                message="No channels returned in Deepgram response",
            )

        channel = channels[0]
        alternatives = channel.get("alternatives", [])

        if not alternatives:
            raise TranscriptionError(
                provider="deepgram",
                message="No alternatives returned in Deepgram response",
            )

        best = alternatives[0]
        raw_text: str = best.get("transcript", "")

        # ------ Build segments from utterances (preferred) or words ------
        segments: List[TranscriptSegment] = []

        # Prefer utterances — they give sentence-level segments with
        # speaker labels already assigned.
        utterances = results.get("utterances", [])
        if utterances:
            segments = self._segments_from_utterances(utterances)
        else:
            # Fall back to word-level diarization and merge into segments.
            words = best.get("words", [])
            segments = self._segments_from_words(words)

        # Duration
        metadata = data.get("metadata", {})
        duration = metadata.get("duration", 0.0)
        if not duration and segments:
            duration = max(seg.end_time for seg in segments)

        return TranscriptionResult(
            raw_text=raw_text,
            segments=segments,
            duration_seconds=float(duration),
            language=language,
        )

    @staticmethod
    def _segments_from_utterances(
        utterances: List[dict],
    ) -> List[TranscriptSegment]:
        """Map Deepgram utterance objects to ``TranscriptSegment`` instances."""
        segments: List[TranscriptSegment] = []
        for utt in utterances:
            speaker_idx = utt.get("speaker", 0)
            speaker_label = _SPEAKER_LABELS.get(speaker_idx, f"Speaker {speaker_idx}")
            segments.append(
                TranscriptSegment(
                    speaker=speaker_label,
                    start_time=float(utt.get("start", 0.0)),
                    end_time=float(utt.get("end", 0.0)),
                    text=utt.get("transcript", "").strip(),
                )
            )
        return segments

    @staticmethod
    def _segments_from_words(
        words: List[dict],
    ) -> List[TranscriptSegment]:
        """Merge word-level diarization data into contiguous speaker segments.

        Adjacent words from the same speaker are merged into a single
        segment so the output is human-readable.
        """
        if not words:
            return []

        segments: List[TranscriptSegment] = []
        current_speaker: int | None = None
        current_words: List[str] = []
        seg_start: float = 0.0
        seg_end: float = 0.0

        for word_info in words:
            speaker_idx = word_info.get("speaker", 0)
            word_text = word_info.get("punctuated_word", word_info.get("word", ""))
            word_start = float(word_info.get("start", 0.0))
            word_end = float(word_info.get("end", 0.0))

            if speaker_idx != current_speaker:
                # Flush the previous segment.
                if current_words and current_speaker is not None:
                    segments.append(
                        TranscriptSegment(
                            speaker=_SPEAKER_LABELS.get(
                                current_speaker, f"Speaker {current_speaker}"
                            ),
                            start_time=seg_start,
                            end_time=seg_end,
                            text=" ".join(current_words),
                        )
                    )
                current_speaker = speaker_idx
                current_words = [word_text]
                seg_start = word_start
                seg_end = word_end
            else:
                current_words.append(word_text)
                seg_end = word_end

        # Flush final segment.
        if current_words and current_speaker is not None:
            segments.append(
                TranscriptSegment(
                    speaker=_SPEAKER_LABELS.get(
                        current_speaker, f"Speaker {current_speaker}"
                    ),
                    start_time=seg_start,
                    end_time=seg_end,
                    text=" ".join(current_words),
                )
            )

        return segments
