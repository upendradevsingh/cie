"""Meeting-type-aware prompt preambles.

Each meeting type provides cleanup and extraction preambles that are
injected into the LLM prompts to improve extraction quality for
specific meeting formats (DSM, 1:1, retro, etc.).

Usage:
    config = get_meeting_config("dsm")
    config.cleanup_preamble   # prepend to cleanup prompt
    config.extraction_preamble  # prepend to extraction prompt
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MeetingTypeConfig:
    """Prompt preambles for a specific meeting type."""

    meeting_type: str
    cleanup_preamble: str
    extraction_preamble: str


# Default config — no preambles, current behavior
_DEFAULT = MeetingTypeConfig(
    meeting_type="default",
    cleanup_preamble="",
    extraction_preamble="",
)

# Registry populated lazily on first access
_registry: dict[str, MeetingTypeConfig] | None = None


def _load_registry() -> dict[str, MeetingTypeConfig]:
    from app.services.extraction.meeting_types.dsm import DSM_CONFIG

    return {
        "dsm": DSM_CONFIG,
    }


def get_meeting_config(meeting_type: str | None) -> MeetingTypeConfig:
    """Get the prompt config for a meeting type. Returns default if unknown."""
    if not meeting_type:
        return _DEFAULT

    global _registry
    if _registry is None:
        _registry = _load_registry()

    return _registry.get(meeting_type.lower(), _DEFAULT)
