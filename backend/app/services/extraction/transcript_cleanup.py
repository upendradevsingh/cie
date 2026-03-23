"""Pass 0: Transcript cleanup before extraction.

Cleans messy auto-transcribed text to improve extraction quality:
- Fixes speaker names (matches to participant list)
- Fixes acronyms (TRD, PRD, HLD, OKR, etc.)
- Cleans Hinglish → readable English where possible
- Removes filler/noise words
- Preserves all meaning — never adds or removes substance
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

CLEANUP_SYSTEM_PROMPT = """You are a transcript editor. Your job is to clean up a messy auto-transcribed meeting transcript to make it readable and accurate, while preserving ALL meaning.

The transcript is formatted as speaker-tagged lines: "Speaker Name: text". Each line's speaker attribution comes from the original ASR system.

Rules:
1. FIX speaker names — match to the participant list provided. "cresh" → "Krish", "dinesh" → "Dinesh"
2. FIX technical acronyms — "trd" → "TRD", "prd" → "PRD", "hld" → "HLD", "okr" → "OKR", "qa" → "QA", "ut" → "unit tests"
3. FIX Hinglish — translate Hindi words to English where meaning is clear. Keep original if ambiguous.
4. REMOVE filler — "basically", "like", "you know", "correct correct", repeated words. But keep "correct" when it's a confirmation.
5. FIX broken sentences — merge consecutive fragments FROM THE SAME SPEAKER into coherent sentences
6. PRESERVE dates, deadlines, names, numbers, and all commitments exactly as stated
7. NEVER CHANGE SPEAKER ATTRIBUTION — the "Speaker Name:" prefix on each line is ground truth from the audio diarization system. You MUST NOT move text from one speaker to another. If Speaker A said something, it stays attributed to Speaker A even if it seems contextually odd.
8. You MAY merge consecutive lines from the SAME speaker into one line. You MUST NOT merge lines from DIFFERENT speakers.
9. DO NOT add information that wasn't in the original
10. DO NOT summarize or shorten — output should be similar length to input
11. Output format: keep the "Speaker Name: text" format. One speaker per line.
12. Output clean text only — no commentary, no markdown, no JSON"""

CLEANUP_PROMPT_TEMPLATE = """{meeting_context}## Participants
{participants}

## Meeting Date
{meeting_date}

## Raw Transcript (auto-transcribed, may have errors)
{transcript}

## Task
Clean up this transcript following the rules. Output ONLY the cleaned transcript text."""


def build_cleanup_prompt(
    transcript: str,
    participants: list[dict[str, Any]],
    meeting_date: str = "not specified",
    meeting_type: str | None = None,
) -> str:
    """Build the transcript cleanup prompt."""
    from app.services.extraction.meeting_types import get_meeting_config

    if participants:
        participant_str = "\n".join(
            f"- {p.get('name', 'Unknown')} ({p.get('role', 'participant')})"
            for p in participants
        )
    else:
        participant_str = "Not specified"

    config = get_meeting_config(meeting_type)
    meeting_context = config.cleanup_preamble + "\n" if config.cleanup_preamble else ""

    return CLEANUP_PROMPT_TEMPLATE.format(
        meeting_context=meeting_context,
        participants=participant_str,
        meeting_date=meeting_date,
        transcript=transcript,
    )
