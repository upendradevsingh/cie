"""Abstract base class and data structures for transcription providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class TranscriptSegment:
    """A single speaker-labelled segment within a transcript.

    Attributes
    ----------
    speaker:
        Human-readable speaker label, e.g. ``"Agent"`` or ``"Customer"``.
    start_time:
        Segment start offset in seconds from the beginning of the recording.
    end_time:
        Segment end offset in seconds.
    text:
        The spoken text for this segment.
    """

    speaker: str
    start_time: float
    end_time: float
    text: str


@dataclass
class TranscriptionResult:
    """Complete transcription output returned by every provider.

    Attributes
    ----------
    raw_text:
        The full transcript as a single plain-text string (no speaker labels).
    segments:
        Ordered list of speaker-diarised segments.
    duration_seconds:
        Total audio duration in seconds (as reported by the provider).
    language:
        Detected or requested language code (e.g. ``"en"``, ``"hi"``).
    speaker_labeled_text:
        Human-readable transcript with speaker labels and timestamps.
        Generated automatically from *segments* if not provided.
    """

    raw_text: str
    segments: List[TranscriptSegment]
    duration_seconds: float
    language: str
    speaker_labeled_text: str = ""

    def __post_init__(self) -> None:
        if not self.speaker_labeled_text and self.segments:
            self.speaker_labeled_text = self._build_labeled_text()

    def _build_labeled_text(self) -> str:
        """Build a readable transcript from segments.

        Format:
            [MM:SS] Speaker: text
        """
        lines: List[str] = []
        for seg in self.segments:
            minutes = int(seg.start_time // 60)
            seconds = int(seg.start_time % 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {seg.speaker}: {seg.text}")
        return "\n".join(lines)


class TranscriptionProvider(ABC):
    """Abstract interface that every transcription backend must implement.

    Subclasses must override :meth:`transcribe` to accept a local file path
    and return a :class:`TranscriptionResult`.
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: str = "en",
    ) -> TranscriptionResult:
        """Transcribe an audio file and return a structured result.

        Parameters
        ----------
        audio_path:
            Absolute path to the audio file on disk.
        language:
            BCP-47 language code.  Supported values depend on the concrete
            provider but at minimum ``"en"`` (English) and ``"hi"`` (Hindi)
            must be handled.

        Returns
        -------
        TranscriptionResult
            The complete transcription with speaker-diarised segments.

        Raises
        ------
        TranscriptionError
            When the provider fails to process the audio.
        """
        ...


class TranscriptionError(Exception):
    """Raised when a transcription provider encounters an unrecoverable error."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")
