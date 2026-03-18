"""Tests for the keyword matcher module."""
from __future__ import annotations

import pytest

from tests.eval.matching.keyword_matcher import KeywordMatcher


@pytest.mark.fast
def test_exact_type_and_keywords_match():
    """Full keyword overlap on same type returns a match with ratio 1.0."""
    matcher = KeywordMatcher(threshold=0.50)
    expected = {
        "extraction_type": "GOAL",
        "description_contains": ["improve", "sales"],
    }
    actuals = [
        {
            "extraction_type": "GOAL",
            "description": "Need to improve sales numbers this quarter",
            "confidence": 0.9,
        }
    ]
    result = matcher.match(expected, actuals, set())
    assert result is not None
    idx, ratio = result
    assert idx == 0
    assert ratio == 1.0


@pytest.mark.fast
def test_no_match_wrong_type():
    """Different extraction type yields no match even if keywords overlap."""
    matcher = KeywordMatcher(threshold=0.50)
    expected = {
        "extraction_type": "GOAL",
        "description_contains": ["improve"],
    }
    actuals = [
        {
            "extraction_type": "FEEDBACK",
            "description": "Need to improve sales numbers",
            "confidence": 0.9,
        }
    ]
    result = matcher.match(expected, actuals, set())
    assert result is None


@pytest.mark.fast
def test_partial_keyword_match_below_threshold():
    """When keyword overlap is below threshold, no match is returned."""
    matcher = KeywordMatcher(threshold=0.50)
    expected = {
        "extraction_type": "GOAL",
        "description_contains": ["improve", "sales", "revenue", "growth"],
    }
    actuals = [
        {
            "extraction_type": "GOAL",
            "description": "Need to improve overall numbers",
            "confidence": 0.9,
        }
    ]
    # Only 1/4 keywords match = 0.25, below 0.50 threshold
    result = matcher.match(expected, actuals, set())
    assert result is None


@pytest.mark.fast
def test_skips_already_matched():
    """Indices in already_matched are skipped even if they would match."""
    matcher = KeywordMatcher(threshold=0.50)
    expected = {
        "extraction_type": "GOAL",
        "description_contains": ["improve"],
    }
    actuals = [
        {
            "extraction_type": "GOAL",
            "description": "Need to improve sales numbers",
            "confidence": 0.9,
        },
        {
            "extraction_type": "GOAL",
            "description": "Want to improve team morale",
            "confidence": 0.8,
        },
    ]
    # Mark first one as already matched
    result = matcher.match(expected, actuals, {0})
    assert result is not None
    idx, _ = result
    assert idx == 1
