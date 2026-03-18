"""Pluggable keyword-based matcher for extraction evaluation.

Extracts the matching logic from metrics.py into a standalone module
so alternative matchers (e.g. semantic) can be swapped in via the
MatcherProtocol interface.
"""
from __future__ import annotations

from typing import Optional, Protocol


KEYWORD_MATCH_THRESHOLD = 0.50


class MatcherProtocol(Protocol):
    """Interface that any extraction matcher must satisfy."""

    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find the best matching actual extraction for an expected one.

        Returns (index, match_ratio) or None if no match found.
        """
        ...


def _keywords_match(description: str, keywords: list[str]) -> float:
    """Check what fraction of keywords appear in the description (case-insensitive).

    Returns a ratio between 0.0 and 1.0.
    """
    if not keywords:
        return 1.0
    desc_lower = description.lower()
    matched = sum(1 for kw in keywords if kw.lower() in desc_lower)
    return matched / len(keywords)


class KeywordMatcher:
    """Matches extractions by exact type + keyword overlap on description."""

    def __init__(self, threshold: float = KEYWORD_MATCH_THRESHOLD) -> None:
        self.threshold = threshold

    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find the best matching actual extraction for an expected one.

        Uses extraction_type match + keyword fuzzy matching on description.
        Returns (index, match_ratio) or None if no match found.
        """
        expected_type = expected["extraction_type"]
        keywords = expected.get("description_contains", [])
        min_confidence = expected.get("min_confidence", 0.0)

        best_idx: Optional[int] = None
        best_ratio = 0.0

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

            # Fuzzy match on description keywords
            actual_desc = actual.get("description", "")
            ratio = _keywords_match(actual_desc, keywords)

            if ratio >= self.threshold and ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx

        if best_idx is not None:
            return (best_idx, best_ratio)
        return None
