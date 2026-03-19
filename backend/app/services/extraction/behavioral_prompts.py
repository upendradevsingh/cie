"""Behavioral extraction prompts and type classifications for two-pass extraction."""

BEHAVIORAL_SYSTEM_PROMPT = """You are an expert organizational psychologist analyzing conversation dynamics. Your task is to extract BEHAVIORAL signals — not what was said, but how it was said and what it reveals about the people and team.

Rules:
1. Focus on behavioral patterns, not content (content extraction is handled separately)
2. Return valid JSON only — no prose, no markdown
3. Assign confidence scores between 0.0 and 1.0
4. Evidence should be a direct quote showing the behavioral signal
5. Be specific about which framework concept you're identifying"""

CONTENT_TYPES = {
    "COMMITMENT", "BLOCKER", "ACTION_ITEM", "DECISION", "GOAL_UPDATE", "RECOGNITION",
    "FOLLOW_UP", "RISK", "METRIC_TARGET", "RECOMMENDATION",
}
BEHAVIORAL_TYPES = {
    "FEEDBACK", "COACHING_MOMENT", "PSYCHOLOGICAL_SAFETY", "MINDSET_SIGNAL",
    "ACCOUNTABILITY_SIGNAL", "SENTIMENT",
}
