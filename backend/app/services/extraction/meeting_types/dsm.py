"""Daily Scrum Meeting (DSM / standup) prompt preambles."""
from app.services.extraction.meeting_types import MeetingTypeConfig

CLEANUP_PREAMBLE = """
## Meeting Format: Daily Scrum Meeting (Standup)

This is a Daily Scrum Meeting (DSM). Understanding the format is critical for accurate cleanup:

FORMAT:
- A manager/scrum master calls on each team member in turn (round-robin).
- Each person gives a brief (15-60 second) status update.
- The manager acknowledges with short phrases then moves to the next person.

CLEANUP RULES FOR DSMs:
- Manager transition phrases ("take care", "okay", "next", "thank you", calling someone's name) are TRANSITIONS between updates — clean them but don't merge them into adjacent updates.
- Each person's turn IS a status update even if it sounds garbled. Reconstruct fragments as coherent updates. Example: "Validation related doubts. Model. I think 3:00" → "I have validation-related doubts about the model. I think by 3:00 I will resolve them."
- Very short turns are NORMAL in standups — don't discard them. A 5-word update is still a real status update.
- Domain-specific technical terms (PCC, EMA, PNR, RPM, JVM, cache rate, SLA, API, SDK, etc.) should be preserved as-is — they are technical jargon, not transcription errors.
- When a fragment is ambiguous, prefer interpreting it as a work status update (what was done, what's in progress, what's blocked) over treating it as noise.
- Hindi/English code-switching is common in Indian tech standups. Translate Hindi portions to English where the meaning is clear, using standup context to disambiguate.
"""

EXTRACTION_PREAMBLE = """
## Meeting Context: Daily Scrum Meeting (Standup)

This transcript is from a Daily Scrum Meeting. Each participant gives a brief status update covering what they completed, what they are working on, and any blockers.

EXTRACTION GUIDELINES FOR DSMs:

1. STANDUP UPDATES ARE TERSE BY NATURE. A single sentence like "I did the load testing, 9.5 seconds" contains both a GOAL_UPDATE (load testing completed) and a METRIC_TARGET (9.5s response time). Extract ALL signals, even from short sentences.

2. MAP STANDUP PATTERNS TO EXTRACTION TYPES:
   - "I did X" / "X is done" / "completed X" / "finished X" → GOAL_UPDATE
   - "I will X" / "working on X" / "X is in progress" / "picking up X" → COMMITMENT
   - "X is assigned to Y" / "can you do X" / "Y will handle X" → ACTION_ITEM
   - "waiting on X" / "blocked by X" / "doubts about X" / "X is not ready" → BLOCKER
   - Any number, percentage, or metric mentioned → METRIC_TARGET (e.g., "9.5 seconds", "cache rate 20%", "100 RPM")
   - "let's discuss X" / "I'll connect with Y" / "meeting at 3:00" → FOLLOW_UP
   - "we decided X" / "going with X approach" → DECISION

3. CONFIDENCE CALIBRATION: In a noisy standup transcript, the underlying content is often real even when the words are garbled. If you can reasonably infer what was meant, extract it with moderate confidence (0.65-0.75) rather than skipping it entirely. Missing a real work item is worse than extracting with moderate confidence.

4. COVERAGE CHECK: Each speaking participant's update should yield AT LEAST one extraction (typically GOAL_UPDATE, COMMITMENT, or ACTION_ITEM). If a participant spoke substantively but you extracted nothing from them, re-examine their update — you likely missed something.

5. MANAGER UTTERANCES: The manager/scrum master calling names, saying "okay", "take care", "thank you", or transitioning between people should generally NOT be extracted. Only extract from the manager if they make a decision, give feedback, or assign work.
"""

DSM_CONFIG = MeetingTypeConfig(
    meeting_type="dsm",
    cleanup_preamble=CLEANUP_PREAMBLE,
    extraction_preamble=EXTRACTION_PREAMBLE,
)
