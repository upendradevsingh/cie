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

Rules:
1. FIX speaker names — match to the participant list provided. "cresh" → "Krish", "dinesh" → "Dinesh"
2. FIX technical acronyms — "trd" → "TRD", "prd" → "PRD", "hld" → "HLD", "okr" → "OKR", "qa" → "QA", "ut" → "unit tests"
3. FIX Hinglish — translate Hindi words to English where meaning is clear. Keep original if ambiguous.
4. REMOVE filler — "basically", "like", "you know", "correct correct", repeated words. But keep "correct" when it's a confirmation.
5. FIX broken sentences — merge fragments into coherent sentences
6. PRESERVE dates, deadlines, names, numbers, and all commitments exactly as stated
7. PRESERVE speaker attribution — if the original shows who said what, keep it
8. DO NOT add information that wasn't in the original
9. DO NOT summarize or shorten — output should be similar length to input
10. Output clean text only — no commentary, no markdown, no JSON"""

CLEANUP_PROMPT_TEMPLATE = """## Participants
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
) -> str:
    """Build the transcript cleanup prompt."""
    if participants:
        participant_str = "\n".join(
            f"- {p.get('name', 'Unknown')} ({p.get('role', 'participant')})"
            for p in participants
        )
    else:
        participant_str = "Not specified"

    return CLEANUP_PROMPT_TEMPLATE.format(
        participants=participant_str,
        meeting_date=meeting_date,
        transcript=transcript,
    )
