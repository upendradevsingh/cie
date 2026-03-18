"""Tests for keyword, embedding, and LLM judge matcher modules."""
from __future__ import annotations

import pytest

from tests.eval.matching.keyword_matcher import KeywordMatcher
from tests.eval.matching.embedding_matcher import EmbeddingMatcher
from tests.eval.matching.llm_judge import LLMJudgeMatcher


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


# ── EmbeddingMatcher tests ───────────────────────────────────────────


class TestEmbeddingMatcher:
    """Tests that require an OpenAI API call (marked with @pytest.mark.llm)."""

    @pytest.mark.llm
    def test_semantic_match_synonyms(self):
        """Semantically similar descriptions should match (e.g. 'Friday' ~ 'end of week')."""
        matcher = EmbeddingMatcher(threshold=0.50)
        expected = {
            "extraction_type": "GOAL",
            "description_contains": ["Friday"],
        }
        actuals = [
            {
                "extraction_type": "GOAL",
                "description": "Complete the report by end of week",
                "confidence": 0.9,
            }
        ]
        result = matcher.match(expected, actuals, set())
        assert result is not None
        idx, score = result
        assert idx == 0
        assert score >= 0.50

    @pytest.mark.llm
    def test_no_semantic_match_unrelated(self):
        """Completely unrelated descriptions should not match."""
        matcher = EmbeddingMatcher(threshold=0.50)
        expected = {
            "extraction_type": "GOAL",
            "description_contains": ["database", "migration"],
        }
        actuals = [
            {
                "extraction_type": "GOAL",
                "description": "The weather is nice today for a walk in the park",
                "confidence": 0.9,
            }
        ]
        result = matcher.match(expected, actuals, set())
        assert result is None


# ── LLMJudgeMatcher tests ───────────────────────────────────────────


class TestLLMJudge:
    """Tests that use LLM-as-Judge for borderline matching (marked with @pytest.mark.llm)."""

    @pytest.mark.llm
    def test_judges_correct_match(self):
        """Paraphrased but semantically equivalent extraction should be judged yes or partial."""
        matcher = LLMJudgeMatcher()
        expected = {
            "extraction_type": "GOAL",
            "description_contains": ["API", "Friday"],
        }
        actuals = [
            {
                "extraction_type": "GOAL",
                "description": "Complete API integration by end of week",
                "confidence": 0.85,
            }
        ]
        result = matcher.match(expected, actuals, set())
        assert result is not None
        idx, score = result
        assert idx == 0
        assert score >= 0.7  # "yes" → 1.0 or "partial" → 0.7

    @pytest.mark.llm
    def test_judges_incorrect_match(self):
        """Completely unrelated extraction should be judged no."""
        matcher = LLMJudgeMatcher()
        expected = {
            "extraction_type": "GOAL",
            "description_contains": ["database", "migration"],
        }
        actuals = [
            {
                "extraction_type": "GOAL",
                "description": "Team morale is low and needs attention",
                "confidence": 0.9,
            }
        ]
        result = matcher.match(expected, actuals, set())
        assert result is None
