# Meeting-Type-Aware Prompt System

**Date:** 2026-03-23
**Status:** Approved

## Problem

CIE's transcript cleanup and extraction prompts are meeting-format-agnostic. Daily scrum meetings (DSMs) have a specific structure — manager calls on each person round-robin, each gives a 15-30 second status update — but the prompts treat them like generic conversations. This causes:

1. **Cleanup failures**: Transition phrases ("take care", "okay") treated as content. Garbled status updates not reconstructed with standup context. The cleanup LLM doesn't know that short fragments *are* the update, not noise.
2. **Extraction gaps**: The content extraction pass returns empty results because terse standup updates don't look like confident commitments/blockers/action items to a generic extraction prompt. A DSM-aware prompt would know that each person's turn almost always contains a status update, work-in-progress, or blocker.

Evidence: DSM Flights transcript — Pass 1 (content) returned `extractions: []` despite containing load testing metrics (Sudhanshu), algorithm commitments (Pranjal), and validation blockers (Sahin).

## Design

### Approach

When `source_metadata.meeting_type` is set (e.g., `"dsm"`), inject a **meeting context preamble** into both the cleanup and extraction prompts. The preamble teaches the LLM the meeting format, typical patterns, and extraction priorities.

No new API fields, no DB changes, no profile YAML changes. The `source_metadata` dict already exists and is freeform.

### Meeting Type Config

Each meeting type provides two preambles:

- **cleanup_preamble**: Prepended to the cleanup prompt. Teaches the cleanup LLM the meeting format so it reconstructs garbled text intelligently.
- **extraction_preamble**: Prepended to the extraction prompt (before extraction type sections). Tells the extraction LLM what to expect and how to map standup patterns to extraction types.

### File Structure

```
backend/app/services/extraction/
  meeting_types/
    __init__.py       — MeetingTypeConfig dataclass, get_meeting_config(type) loader
    dsm.py            — DSM-specific cleanup + extraction preambles
    default.py        — Fallback config (empty preambles, current behavior)
```

### DSM Cleanup Preamble (key instructions)

- This is a Daily Scrum Meeting (standup). Format: manager calls each person in turn, each gives a brief status update.
- Manager phrases like "take care", "okay", "next" are transition cues — not content. Clean them but don't extract meaning from them.
- Each person's turn is a status update. Reconstruct garbled fragments as coherent updates using context: what they worked on, what they're doing next, any blockers.
- Very short turns ("Hello. Validation related doubts. Model.") are still real updates — don't discard them. Reconstruct as: "I have validation-related doubts about the model."
- Acknowledgments from the manager ("okay", "take care") between updates are transitions.
- Domain-specific terms (PCC, EMA, PNR, RPM, JVM, cache rate, etc.) should be preserved as-is — they're technical terms, not transcription errors.

### DSM Extraction Preamble (key instructions)

- This is a Daily Scrum Meeting. Each participant gives a brief status update covering: what they completed, what they're working on, and any blockers.
- In standups, updates are TERSE by nature. A single sentence like "I did the load testing, 9.5 seconds" contains both a GOAL_UPDATE (load testing done) and a METRIC_TARGET (9.5s response time). Extract aggressively.
- Map standup patterns to extraction types:
  - "I did X" / "X is done" / "completed X" → GOAL_UPDATE
  - "I will X" / "working on X" / "X is in progress" → COMMITMENT
  - "X is assigned to Y" / "can you do X" → ACTION_ITEM
  - "waiting on X" / "blocked by X" / "X is not ready" → BLOCKER
  - "X took 9.5 seconds" / "cache rate 20%" → METRIC_TARGET
  - "let's discuss X at 3:00" / "I'll connect with him" → FOLLOW_UP
  - Numbers, percentages, and metrics mentioned in updates are almost always METRIC_TARGETs — don't ignore them even if the surrounding text is garbled.
- Lower your confidence threshold expectations: in a noisy standup transcript, 0.65-0.70 confidence is acceptable for content extractions. The alternative is missing real work items entirely.
- Each person's turn should yield AT LEAST one extraction (GOAL_UPDATE, COMMITMENT, or ACTION_ITEM). If a participant spoke but you extracted nothing from them, re-examine their update.

### Integration Points

1. **`engine.py`**: Extract `meeting_type` from conversation metadata, pass to cleanup and extraction prompt builders.
2. **`transcript_cleanup.py`**: `build_cleanup_prompt()` accepts optional `meeting_type` param. If provided, load the meeting config and prepend `cleanup_preamble` to the prompt.
3. **`prompts.py`**: `build_extraction_prompt_for_types()` accepts optional `meeting_type` param. If provided, load the meeting config and prepend `extraction_preamble` before the extraction type sections.

### Adding New Meeting Types

To add support for a new meeting type (e.g., `1on1`, `retro`, `design_review`):

1. Create `backend/app/services/extraction/meeting_types/<type>.py`
2. Define `CLEANUP_PREAMBLE` and `EXTRACTION_PREAMBLE` strings
3. Register in `meeting_types/__init__.py`

No other changes needed.

## Testing

- Re-run the DSM Flights transcript with `"meeting_type": "dsm"` and verify:
  - Cleanup preserves speaker attribution (already fixed)
  - Cleanup reconstructs garbled updates with DSM context
  - Content pass extracts from Sudhanshu (metrics), Sahin (blocker), Pranjal (commitments), Ayush (work items)
  - Each speaking participant yields at least one extraction
- Run without `meeting_type` to verify default behavior is unchanged
- Run with the clean App Integration transcript to verify it still works well
