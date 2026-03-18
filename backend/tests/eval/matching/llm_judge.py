"""LLM-as-Judge for borderline extraction matches.

When keyword matching is ambiguous (e.g. paraphrased extractions),
this matcher uses an LLM to decide whether actual extractions
semantically match what was expected.
"""
from __future__ import annotations

import os
from typing import Optional

import openai

JUDGE_MODEL = "gpt-4o-mini"

JUDGE_SYSTEM_PROMPT = """You are an extraction quality judge. Given an expected extraction and an actual extraction, determine if they match.

Reply with exactly one word: "yes", "partial", or "no".
- "yes": The actual extraction correctly captures the same insight as expected.
- "partial": The actual extraction captures part of the expected insight but misses key details.
- "no": The actual extraction does not match the expected insight."""


class LLMJudgeMatcher:
    """Matches extractions by asking an LLM whether they are semantically equivalent."""

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    def judge_single(self, expected: dict, actual: dict) -> str:
        """Ask the LLM to judge whether a single expected/actual pair match.

        Returns one of: "yes", "partial", "no".
        """
        keywords = expected.get("description_contains", [])
        expected_desc = (
            f"Type: {expected['extraction_type']}. "
            f"Should contain: {', '.join(keywords)}"
        )
        actual_desc = (
            f"Type: {actual.get('extraction_type', '')}. "
            f"Description: {actual.get('description', '')}"
        )
        prompt = f"Expected:\n{expected_desc}\n\nActual:\n{actual_desc}\n\nVerdict:"

        resp = self._client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0,
            max_tokens=5,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        verdict = resp.choices[0].message.content.strip().lower()
        return verdict if verdict in ("yes", "partial", "no") else "no"

    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find the best matching actual extraction for an expected one.

        Uses extraction_type pre-filter + LLM judgement for semantic matching.
        Returns (index, match_ratio) or None if no match found.

        Match ratios: "yes" → 1.0, "partial" → 0.7.
        """
        expected_type = expected["extraction_type"]
        min_confidence = expected.get("min_confidence", 0.0)

        for idx, actual in enumerate(actual_extractions):
            if idx in already_matched:
                continue

            # Type must match exactly
            actual_type = actual.get("extraction_type", "").upper()
            if actual_type != expected_type:
                continue

            # Check confidence meets minimum
            actual_conf = actual.get("confidence", 0.0)
            if actual_conf < min_confidence:
                continue

            verdict = self.judge_single(expected, actual)
            if verdict == "yes":
                return (idx, 1.0)
            elif verdict == "partial":
                return (idx, 0.7)

        return None
