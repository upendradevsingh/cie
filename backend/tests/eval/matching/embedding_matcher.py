"""Embedding-based extraction matcher using OpenAI text-embedding-3-small.

Uses cosine similarity between embedding vectors instead of keyword
overlap, enabling semantic matching (e.g. "Friday" ~ "end of week").
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import openai

EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.50
STRONG_MATCH_THRESHOLD = 0.75


class EmbeddingMatcher:
    """Matches extractions by exact type + semantic similarity on description."""

    def __init__(self, threshold: float = SIMILARITY_THRESHOLD) -> None:
        self.threshold = threshold
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        self._cache: dict[str, list[float]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_embedding(self, text: str) -> list[float]:
        """Return the embedding for *text*, using a per-instance cache."""
        if text in self._cache:
            return self._cache[text]
        resp = self._client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        embedding = resp.data[0].embedding
        self._cache[text] = embedding
        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        a_arr, b_arr = np.array(a), np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    # ------------------------------------------------------------------
    # MatcherProtocol implementation
    # ------------------------------------------------------------------

    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find the best matching actual extraction for an expected one.

        Uses extraction_type exact match + cosine similarity of OpenAI
        embeddings on the description text.
        Returns (index, similarity_score) or None if no match found.
        """
        expected_type = expected["extraction_type"]
        keywords = expected.get("description_contains", [])
        expected_text = " ".join(keywords) if keywords else expected_type
        expected_emb = self._get_embedding(expected_text)
        min_confidence = expected.get("min_confidence", 0.0)

        best_idx: Optional[int] = None
        best_score = 0.0

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

            # Semantic similarity on description
            actual_desc = actual.get("description", "")
            actual_emb = self._get_embedding(actual_desc)
            score = self._cosine_similarity(expected_emb, actual_emb)

            if score >= self.threshold and score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None:
            return (best_idx, best_score)
        return None
