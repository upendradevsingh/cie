"""Factory for obtaining a transcription provider by name.

Supports both explicit provider name arguments and the default configured
provider from ``settings.TRANSCRIPTION_PROVIDER``.
"""

from app.config import settings
from app.services.transcription.base import TranscriptionError, TranscriptionProvider


def get_transcription_provider(
    provider_name: str | None = None,
) -> TranscriptionProvider:
    """Return a concrete :class:`TranscriptionProvider` for *provider_name*.

    Parameters
    ----------
    provider_name:
        One of ``"deepgram"`` or ``"whisper"`` (case-insensitive).
        If ``None``, uses ``settings.TRANSCRIPTION_PROVIDER``.

    Returns
    -------
    TranscriptionProvider
        An initialised provider instance ready to call :meth:`transcribe`.

    Raises
    ------
    TranscriptionError
        If *provider_name* is not recognised.
    """
    name = (provider_name or settings.TRANSCRIPTION_PROVIDER).strip().lower()

    if name == "deepgram":
        from app.services.transcription.deepgram_provider import DeepgramProvider

        return DeepgramProvider()

    if name in ("whisper", "openai", "openai_whisper"):
        from app.services.transcription.whisper_provider import WhisperProvider

        return WhisperProvider()

    raise TranscriptionError(
        provider=name,
        message=(
            f"Unknown transcription provider '{name}'. "
            "Supported providers: deepgram, whisper."
        ),
    )
