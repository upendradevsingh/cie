"""Hybrid matcher: keyword -> embedding -> LLM judge.

Orchestrates all three matching layers in a cascade:
1. Keyword matcher (fast, deterministic)
2. Embedding matcher (semantic similarity)
3. LLM judge (borderline arbitration)

The `mode` parameter controls which layers are active:
- "keyword": keyword only
- "embedding": keyword + embedding
- "hybrid": keyword + embedding + LLM judge
"""
from __future__ import annotations

from typing import Optional

from tests.eval.matching.keyword_matcher import KeywordMatcher
from tests.eval.matching.embedding_matcher import EmbeddingMatcher, STRONG_MATCH_THRESHOLD
from tests.eval.matching.llm_judge import LLMJudgeMatcher


class HybridMatcher:
    """Cascading matcher that escalates through keyword, embedding, and LLM judge layers."""

    def __init__(self, mode: str = "hybrid") -> None:
        if mode not in ("keyword", "embedding", "hybrid"):
            raise ValueError(f"Invalid match mode: {mode!r}. Must be keyword, embedding, or hybrid.")
        self.mode = mode
        self._keyword = KeywordMatcher()
        self._embedding = EmbeddingMatcher() if mode in ("embedding", "hybrid") else None
        self._judge = LLMJudgeMatcher() if mode == "hybrid" else None

    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find the best matching actual extraction using a layered cascade.

        Layer 1 (keyword): Always runs. If it finds a match, return immediately.
        Layer 2 (embedding): Runs in 'embedding' and 'hybrid' modes.
            - Strong match (>= STRONG_MATCH_THRESHOLD): return immediately.
            - Borderline match: escalate to Layer 3 in hybrid mode.
        Layer 3 (LLM judge): Runs in 'hybrid' mode as final arbiter for
            borderline embedding matches, or as a pure fallback.

        Returns (index, score) or None if no match found.
        """
        # Layer 1: Keyword (always)
        result = self._keyword.match(expected, actual_extractions, already_matched)
        if result is not None:
            return result

        if self.mode == "keyword":
            return None

        # Layer 2: Embedding
        if self._embedding:
            result = self._embedding.match(expected, actual_extractions, already_matched)
            if result is not None:
                idx, score = result
                if score >= STRONG_MATCH_THRESHOLD:
                    return result
                if self.mode == "embedding":
                    return result
                # Borderline -> Layer 3
                if self._judge:
                    actual = actual_extractions[idx]
                    verdict = self._judge.judge_single(expected, actual)
                    if verdict in ("yes", "partial"):
                        return (idx, score)
            elif self.mode == "embedding":
                return None

        # Layer 3: Pure LLM judge fallback
        if self._judge:
            return self._judge.match(expected, actual_extractions, already_matched)

        return None
