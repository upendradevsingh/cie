# Eval Quality Improvement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve CIE extraction quality measurement and extraction recall for new types via hybrid matching, two-pass extraction, multi-tier annotation, and actionable reporting.

**Architecture:** Three matching layers (keyword → embedding → LLM judge), two extraction passes (content → behavioral), three annotation tiers (manual → LLM-assist → multi-model consensus), diagnostic reporting with delta tracking.

**Tech Stack:** Python 3.12, OpenAI embeddings API (`text-embedding-3-small`), OpenAI chat completions (LLM judge), Anthropic SDK (multi-model), Google Generative AI SDK (multi-model), pytest markers.

**Spec:** `docs/superpowers/specs/2026-03-18-eval-quality-improvement-design.md`

---

## File Structure

```
backend/
├── requirements.txt                          (modify: add anthropic, google-generativeai, numpy)
├── app/services/extraction/
│   ├── engine.py                             (modify: add two-pass mode)
│   ├── prompts.py                            (modify: split type lists for two passes)
│   └── behavioral_prompts.py                 (create: Pass 2 system prompt + builder)
├── tests/eval/
│   ├── matching/
│   │   ├── __init__.py                       (create)
│   │   ├── keyword_matcher.py                (create: extract from metrics.py)
│   │   ├── embedding_matcher.py              (create: cosine similarity via OpenAI)
│   │   ├── llm_judge.py                      (create: borderline adjudication)
│   │   └── hybrid_matcher.py                 (create: orchestrate layers 1-3)
│   ├── annotation/
│   │   ├── __init__.py                       (create)
│   │   ├── llm_assist.py                     (create: Tier 2 pipeline)
│   │   ├── multi_model.py                    (create: Tier 3 consensus)
│   │   └── adjudication.py                   (create: disagreement queue)
│   ├── reporting/
│   │   ├── __init__.py                       (create)
│   │   ├── eval_report.py                    (create: diagnostic report)
│   │   └── delta_tracker.py                  (create: compare runs)
│   ├── metrics.py                            (modify: use pluggable matchers)
│   ├── conftest.py                           (modify: add --match-mode option)
│   ├── gold_dataset.json                     (modify: add annotation_method field)
│   ├── test_extraction_quality.py            (modify: use hybrid matching)
│   ├── test_matching.py                      (create: tests for matching layers)
│   └── test_two_pass.py                      (create: A/B test single vs two-pass)
```

---

### Task 1: Keyword Matcher Extraction

Extract current keyword matching logic from `metrics.py` into its own module so matchers are pluggable.

**Files:**
- Create: `backend/tests/eval/matching/__init__.py`
- Create: `backend/tests/eval/matching/keyword_matcher.py`
- Modify: `backend/tests/eval/metrics.py`
- Test: `backend/tests/eval/test_matching.py`

- [ ] **Step 1: Create matching package**

```bash
mkdir -p backend/tests/eval/matching
touch backend/tests/eval/matching/__init__.py
```

- [ ] **Step 2: Write keyword_matcher.py — extract from metrics.py**

Move `_keywords_match` and `_fuzzy_match_extraction` into `keyword_matcher.py` with a `MatcherProtocol` interface:

```python
# backend/tests/eval/matching/keyword_matcher.py
"""Keyword-based extraction matcher (Layer 1 + basic Layer 2)."""
from typing import Optional, Protocol

KEYWORD_MATCH_THRESHOLD = 0.50

class MatcherProtocol(Protocol):
    """Interface for all matchers."""
    def match(
        self,
        expected: dict,
        actual_extractions: list[dict],
        already_matched: set[int],
    ) -> Optional[tuple[int, float]]:
        """Find best match. Returns (index, score) or None."""
        ...

class KeywordMatcher:
    """Matches extractions using extraction_type + keyword fuzzy match."""

    def __init__(self, threshold: float = KEYWORD_MATCH_THRESHOLD):
        self.threshold = threshold

    def match(self, expected, actual_extractions, already_matched):
        expected_type = expected["extraction_type"]
        keywords = expected.get("description_contains", [])
        min_confidence = expected.get("min_confidence", 0.0)
        best_idx, best_ratio = None, 0.0

        for idx, actual in enumerate(actual_extractions):
            if idx in already_matched:
                continue
            if actual.get("extraction_type", "").upper() != expected_type:
                continue
            if actual.get("confidence", 0.0) < min_confidence:
                continue
            ratio = _keywords_match(actual.get("description", ""), keywords)
            if ratio >= self.threshold and ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx

        return (best_idx, best_ratio) if best_idx is not None else None

def _keywords_match(description: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    desc_lower = description.lower()
    matched = sum(1 for kw in keywords if kw.lower() in desc_lower)
    return matched / len(keywords)
```

- [ ] **Step 3: Write failing test for KeywordMatcher**

```python
# backend/tests/eval/test_matching.py
import pytest
from tests.eval.matching.keyword_matcher import KeywordMatcher

@pytest.mark.fast
class TestKeywordMatcher:
    def test_exact_type_and_keywords_match(self):
        matcher = KeywordMatcher()
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "Will finish API by Friday", "confidence": 0.9}]
        result = matcher.match(expected, actual, set())
        assert result is not None
        assert result[1] == 1.0

    def test_no_match_wrong_type(self):
        matcher = KeywordMatcher()
        expected = {"extraction_type": "BLOCKER", "description_contains": ["API"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "API work", "confidence": 0.9}]
        assert matcher.match(expected, actual, set()) is None

    def test_partial_keyword_match_below_threshold(self):
        matcher = KeywordMatcher()
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday", "deploy", "test"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "Will finish API", "confidence": 0.9}]
        assert matcher.match(expected, actual, set()) is None  # 1/4 = 0.25 < 0.50

    def test_skips_already_matched(self):
        matcher = KeywordMatcher()
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API"]}
        actual = [
            {"extraction_type": "COMMITMENT", "description": "API work", "confidence": 0.9},
            {"extraction_type": "COMMITMENT", "description": "API task", "confidence": 0.8},
        ]
        result = matcher.match(expected, actual, {0})
        assert result is not None
        assert result[0] == 1  # skipped index 0
```

- [ ] **Step 4: Run tests**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_matching.py -v --tb=short
```

Expected: All pass.

- [ ] **Step 5: Update metrics.py to use KeywordMatcher**

Replace inline `_fuzzy_match_extraction` calls in `evaluate_conversation` with `KeywordMatcher().match()`. Remove the old `_fuzzy_match_extraction` and `_keywords_match` functions from metrics.py.

- [ ] **Step 6: Run full eval to verify no regression**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_extraction_parsing.py tests/eval/test_api_integration.py -q
```

Expected: 29 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/eval/matching/ backend/tests/eval/test_matching.py backend/tests/eval/metrics.py
git commit -m "refactor: extract keyword matcher into pluggable module"
```

---

### Task 2: Embedding Matcher

**Files:**
- Create: `backend/tests/eval/matching/embedding_matcher.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/eval/test_matching.py` (extend)

- [ ] **Step 1: Add numpy to requirements**

```bash
echo "numpy>=1.26.0" >> backend/requirements.txt
```

- [ ] **Step 2: Write failing test for EmbeddingMatcher**

```python
# Append to backend/tests/eval/test_matching.py
@pytest.mark.llm
class TestEmbeddingMatcher:
    def test_semantic_match_synonyms(self):
        """'Friday' and 'end of week' should match semantically."""
        from tests.eval.matching.embedding_matcher import EmbeddingMatcher
        matcher = EmbeddingMatcher()
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "Will complete API by end of week", "confidence": 0.9}]
        result = matcher.match(expected, actual, set())
        assert result is not None
        assert result[1] >= 0.70  # semantic similarity should be high

    def test_no_semantic_match_unrelated(self):
        from tests.eval.matching.embedding_matcher import EmbeddingMatcher
        matcher = EmbeddingMatcher()
        expected = {"extraction_type": "BLOCKER", "description_contains": ["database", "migration"]}
        actual = [{"extraction_type": "BLOCKER", "description": "Weather is nice today", "confidence": 0.9}]
        result = matcher.match(expected, actual, set())
        assert result is None  # cosine similarity should be low
```

- [ ] **Step 3: Implement EmbeddingMatcher**

```python
# backend/tests/eval/matching/embedding_matcher.py
"""Embedding-based extraction matcher using OpenAI text-embedding-3-small."""
import os
from typing import Optional

import numpy as np
import openai

EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.50  # Below this = no match
STRONG_MATCH_THRESHOLD = 0.75  # Above this = definite match

class EmbeddingMatcher:
    def __init__(self, threshold: float = SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        self._cache: dict[str, list[float]] = {}

    def _get_embedding(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        resp = self._client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        embedding = resp.data[0].embedding
        self._cache[text] = embedding
        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        a_arr, b_arr = np.array(a), np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    def match(self, expected, actual_extractions, already_matched):
        expected_type = expected["extraction_type"]
        keywords = expected.get("description_contains", [])
        expected_text = " ".join(keywords) if keywords else expected.get("extraction_type", "")
        expected_emb = self._get_embedding(expected_text)
        min_confidence = expected.get("min_confidence", 0.0)

        best_idx, best_score = None, 0.0

        for idx, actual in enumerate(actual_extractions):
            if idx in already_matched:
                continue
            if actual.get("extraction_type", "").upper() != expected_type:
                continue
            if actual.get("confidence", 0.0) < min_confidence:
                continue

            actual_emb = self._get_embedding(actual.get("description", ""))
            score = self._cosine_similarity(expected_emb, actual_emb)

            if score >= self.threshold and score > best_score:
                best_score = score
                best_idx = idx

        return (best_idx, best_score) if best_idx is not None else None
```

- [ ] **Step 4: Run embedding tests**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_matching.py::TestEmbeddingMatcher -v
```

Expected: Pass (requires OPENAI_API_KEY).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/eval/matching/embedding_matcher.py backend/requirements.txt backend/tests/eval/test_matching.py
git commit -m "feat: embedding-based extraction matcher using text-embedding-3-small"
```

---

### Task 3: LLM Judge Matcher

**Files:**
- Create: `backend/tests/eval/matching/llm_judge.py`
- Test: `backend/tests/eval/test_matching.py` (extend)

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.llm
class TestLLMJudge:
    def test_judges_correct_match(self):
        from tests.eval.matching.llm_judge import LLMJudgeMatcher
        judge = LLMJudgeMatcher()
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday"]}
        actual = {"extraction_type": "COMMITMENT", "description": "Engineer will complete the API integration by end of week", "confidence": 0.9}
        verdict = judge.judge_single(expected, actual)
        assert verdict in ("yes", "partial")

    def test_judges_incorrect_match(self):
        from tests.eval.matching.llm_judge import LLMJudgeMatcher
        judge = LLMJudgeMatcher()
        expected = {"extraction_type": "BLOCKER", "description_contains": ["database", "migration"]}
        actual = {"extraction_type": "BLOCKER", "description": "Team morale is low this sprint", "confidence": 0.8}
        verdict = judge.judge_single(expected, actual)
        assert verdict == "no"
```

- [ ] **Step 2: Implement LLMJudgeMatcher**

```python
# backend/tests/eval/matching/llm_judge.py
"""LLM-as-Judge for borderline extraction matches."""
import os
from typing import Optional
import openai

JUDGE_MODEL = "gpt-4o-mini"  # Cheap, fast, good enough for yes/no judging

JUDGE_SYSTEM_PROMPT = """You are an extraction quality judge. Given an expected extraction and an actual extraction, determine if they match.

Reply with exactly one word: "yes", "partial", or "no".
- "yes": The actual extraction correctly captures the same insight as expected.
- "partial": The actual extraction captures part of the expected insight but misses key details.
- "no": The actual extraction does not match the expected insight."""

class LLMJudgeMatcher:
    def __init__(self):
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    def judge_single(self, expected: dict, actual: dict) -> str:
        keywords = expected.get("description_contains", [])
        expected_desc = f"Type: {expected['extraction_type']}. Should contain: {', '.join(keywords)}"
        actual_desc = f"Type: {actual.get('extraction_type', '')}. Description: {actual.get('description', '')}"

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
        if verdict not in ("yes", "partial", "no"):
            return "no"
        return verdict

    def match(self, expected, actual_extractions, already_matched) -> Optional[tuple[int, float]]:
        expected_type = expected["extraction_type"]
        min_confidence = expected.get("min_confidence", 0.0)

        for idx, actual in enumerate(actual_extractions):
            if idx in already_matched:
                continue
            if actual.get("extraction_type", "").upper() != expected_type:
                continue
            if actual.get("confidence", 0.0) < min_confidence:
                continue

            verdict = self.judge_single(expected, actual)
            if verdict == "yes":
                return (idx, 1.0)
            elif verdict == "partial":
                return (idx, 0.7)

        return None
```

- [ ] **Step 3: Run tests**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_matching.py::TestLLMJudge -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/tests/eval/matching/llm_judge.py backend/tests/eval/test_matching.py
git commit -m "feat: LLM-as-judge matcher for borderline extraction evaluation"
```

---

### Task 4: Hybrid Matcher (Orchestrator)

**Files:**
- Create: `backend/tests/eval/matching/hybrid_matcher.py`
- Test: `backend/tests/eval/test_matching.py` (extend)

- [ ] **Step 1: Implement HybridMatcher**

```python
# backend/tests/eval/matching/hybrid_matcher.py
"""Hybrid matcher: keyword → embedding → LLM judge."""
from typing import Optional
from tests.eval.matching.keyword_matcher import KeywordMatcher
from tests.eval.matching.embedding_matcher import EmbeddingMatcher, STRONG_MATCH_THRESHOLD
from tests.eval.matching.llm_judge import LLMJudgeMatcher

class HybridMatcher:
    """Three-layer matching: keyword fast-path, embedding for synonyms, LLM judge for borderline."""

    def __init__(self, mode: str = "hybrid"):
        self.mode = mode  # "keyword", "embedding", "hybrid"
        self._keyword = KeywordMatcher()
        self._embedding = EmbeddingMatcher() if mode in ("embedding", "hybrid") else None
        self._judge = LLMJudgeMatcher() if mode == "hybrid" else None

    def match(self, expected, actual_extractions, already_matched) -> Optional[tuple[int, float]]:
        # Layer 1: Keyword (always runs — free, fast)
        result = self._keyword.match(expected, actual_extractions, already_matched)
        if result is not None:
            return result

        if self.mode == "keyword":
            return None

        # Layer 2: Embedding similarity
        if self._embedding:
            result = self._embedding.match(expected, actual_extractions, already_matched)
            if result is not None:
                idx, score = result
                if score >= STRONG_MATCH_THRESHOLD:
                    return result  # Strong embedding match — accept
                if self.mode == "embedding":
                    return result  # No LLM judge available — accept any match
                # Borderline (0.50-0.75) — go to Layer 3
                if self._judge:
                    actual = actual_extractions[idx]
                    verdict = self._judge.judge_single(expected, actual)
                    if verdict in ("yes", "partial"):
                        return (idx, score)
            elif self.mode == "embedding":
                return None

        # Layer 3: Pure LLM judge fallback (only if embedding found nothing)
        if self._judge:
            return self._judge.match(expected, actual_extractions, already_matched)

        return None
```

- [ ] **Step 2: Write test**

```python
@pytest.mark.llm
class TestHybridMatcher:
    def test_keyword_hit_skips_embedding(self):
        from tests.eval.matching.hybrid_matcher import HybridMatcher
        matcher = HybridMatcher(mode="hybrid")
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "Will finish API by Friday", "confidence": 0.9}]
        result = matcher.match(expected, actual, set())
        assert result is not None
        assert result[1] == 1.0  # Perfect keyword match

    def test_semantic_synonym_caught_by_embedding(self):
        from tests.eval.matching.hybrid_matcher import HybridMatcher
        matcher = HybridMatcher(mode="hybrid")
        expected = {"extraction_type": "COMMITMENT", "description_contains": ["API", "Friday"]}
        actual = [{"extraction_type": "COMMITMENT", "description": "Will complete API integration by end of week", "confidence": 0.9}]
        result = matcher.match(expected, actual, set())
        assert result is not None  # Embedding or LLM judge should catch this
```

- [ ] **Step 3: Run tests**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_matching.py -v
```

- [ ] **Step 4: Wire hybrid matcher into metrics.py and conftest.py**

Update `conftest.py` to accept `--match-mode` pytest option and pass the matcher to `evaluate_conversation`. Update `metrics.py` `evaluate_conversation` to accept a matcher parameter (defaulting to `KeywordMatcher()`).

- [ ] **Step 5: Run full eval with keyword mode (regression check)**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/ -q --match-mode=keyword
```

Expected: Same results as before (47 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/eval/matching/ backend/tests/eval/metrics.py backend/tests/eval/conftest.py backend/tests/eval/test_matching.py
git commit -m "feat: hybrid matching engine — keyword + embedding + LLM judge"
```

---

### Task 5: Two-Pass Extraction Engine

**Files:**
- Create: `backend/app/services/extraction/behavioral_prompts.py`
- Modify: `backend/app/services/extraction/engine.py`
- Modify: `backend/app/services/extraction/prompts.py`
- Create: `backend/tests/eval/test_two_pass.py`

- [ ] **Step 1: Create behavioral system prompt**

```python
# backend/app/services/extraction/behavioral_prompts.py
"""Pass 2: Behavioral extraction — how things were said, not what."""

BEHAVIORAL_SYSTEM_PROMPT = """You are an expert organizational psychologist analyzing conversation dynamics. Your task is to extract BEHAVIORAL signals — not what was said, but how it was said and what it reveals about the people and team.

Rules:
1. Focus on behavioral patterns, not content (content extraction is handled separately)
2. Return valid JSON only — no prose, no markdown
3. Assign confidence scores between 0.0 and 1.0
4. Evidence should be a direct quote showing the behavioral signal
5. Be specific about which framework concept you're identifying"""

CONTENT_TYPES = {"COMMITMENT", "BLOCKER", "ACTION_ITEM", "DECISION", "GOAL_UPDATE", "RECOGNITION"}
BEHAVIORAL_TYPES = {"FEEDBACK", "COACHING_MOMENT", "PSYCHOLOGICAL_SAFETY", "MINDSET_SIGNAL", "ACCOUNTABILITY_SIGNAL", "SENTIMENT"}
```

- [ ] **Step 2: Write failing test for two-pass mode**

```python
# backend/tests/eval/test_two_pass.py
import pytest

@pytest.mark.llm
class TestTwoPassExtraction:
    def test_two_pass_produces_behavioral_types(self):
        """Two-pass mode should produce behavioral types that single-pass misses."""
        import asyncio
        from app.profiles import ProfileLoader
        from app.services.extraction.engine import ExtractionEngine

        loader = ProfileLoader()
        profile = loader.load("performance")
        engine = ExtractionEngine(profile, extraction_mode="two_pass")

        transcript = (
            "Sarah: Your code reviews have been really thorough lately, I appreciate the effort.\n"
            "James: Thanks. Though honestly I just don't get the deployment pipeline. I'm not a DevOps person.\n"
            "Sarah: That's a growth area, not a limitation. Try pairing with Priya on the next deploy."
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(engine.extract(transcript, []))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        types = {e.extraction_type for e in result.extractions}
        # Two-pass should find at least some behavioral types
        behavioral_found = types & {"FEEDBACK", "COACHING_MOMENT", "MINDSET_SIGNAL", "PSYCHOLOGICAL_SAFETY", "SENTIMENT"}
        assert len(behavioral_found) >= 1, f"Two-pass should find behavioral types, found: {types}"

    def test_single_pass_baseline(self):
        """Single-pass baseline for A/B comparison."""
        import asyncio
        from app.profiles import ProfileLoader
        from app.services.extraction.engine import ExtractionEngine

        loader = ProfileLoader()
        profile = loader.load("performance")
        engine = ExtractionEngine(profile, extraction_mode="single_pass")

        transcript = (
            "Sarah: Your code reviews have been really thorough lately, I appreciate the effort.\n"
            "James: Thanks. Though honestly I just don't get the deployment pipeline.\n"
            "Sarah: That's a growth area. Try pairing with Priya on the next deploy."
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(engine.extract(transcript, []))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        assert len(result.extractions) >= 1  # Should find at least something
```

- [ ] **Step 3: Implement two-pass in ExtractionEngine**

Modify `engine.py`:
- Add `extraction_mode` parameter to `__init__` (default: `"single_pass"`)
- In `extract()`, if mode is `"two_pass"`:
  - Call `_call_llm(content_prompt)` → parse content extractions
  - Call `_call_llm(behavioral_prompt)` → parse behavioral extractions
  - Merge both lists
- Use `CONTENT_TYPES` and `BEHAVIORAL_TYPES` from `behavioral_prompts.py` to split the profile's extraction types into two focused prompts

Modify `prompts.py`:
- Add `build_extraction_prompt_for_types(profile, transcript, participants, type_filter)` that only includes specified extraction types

- [ ] **Step 4: Run two-pass test**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_two_pass.py -v
```

- [ ] **Step 5: Run A/B eval — single-pass vs two-pass**

```bash
# Run full eval in single-pass mode
docker compose exec -T cie-api python -m pytest tests/eval/test_extraction_quality.py -v --extraction-mode=single_pass
# Run full eval in two-pass mode
docker compose exec -T cie-api python -m pytest tests/eval/test_extraction_quality.py -v --extraction-mode=two_pass
```

Compare results — two-pass should show higher recall for behavioral types.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/extraction/ backend/tests/eval/test_two_pass.py
git commit -m "feat: two-pass extraction — content pass + behavioral pass"
```

---

### Task 6: Actionable Reporting

**Files:**
- Create: `backend/tests/eval/reporting/__init__.py`
- Create: `backend/tests/eval/reporting/eval_report.py`
- Create: `backend/tests/eval/reporting/delta_tracker.py`

- [ ] **Step 1: Create reporting package**

```bash
mkdir -p backend/tests/eval/reporting
touch backend/tests/eval/reporting/__init__.py
```

- [ ] **Step 2: Implement eval_report.py**

Diagnostic report generator with: overall scores + deltas, per-type breakdown split by content/behavioral, worst misses, confusion patterns, annotation coverage, auto-recommendations. Output as formatted string and JSON.

- [ ] **Step 3: Implement delta_tracker.py**

Saves each eval run's scores to `backend/tests/eval/run_history.json`. Computes deltas vs previous run. Flags regressions.

- [ ] **Step 4: Update format_report in metrics.py to use new reporter**

Replace old `format_report` with call to `eval_report.generate()`.

- [ ] **Step 5: Run eval and verify report output**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_extraction_quality.py -v -s
```

Should print the new diagnostic report.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/eval/reporting/
git commit -m "feat: actionable eval reporting with deltas and recommendations"
```

---

### Task 7: Tier 2 — LLM-Assist Annotation Pipeline

**Files:**
- Create: `backend/tests/eval/annotation/__init__.py`
- Create: `backend/tests/eval/annotation/llm_assist.py`

- [ ] **Step 1: Create annotation package**

```bash
mkdir -p backend/tests/eval/annotation
touch backend/tests/eval/annotation/__init__.py
```

- [ ] **Step 2: Implement llm_assist.py**

CLI tool that:
1. Takes a transcript text file as input
2. Runs it through CIE extraction engine
3. Outputs a draft gold dataset entry with extractions as `expected_extractions`
4. Human reviews and edits the JSON before adding to `gold_dataset.json`

```bash
# Usage:
python -m tests.eval.annotation.llm_assist --input transcript.txt --profile performance --output draft_gold.json
```

- [ ] **Step 3: Test with a sample transcript**

```bash
echo "Manager: How's the project? Engineer: 80% done, blocked on DevOps." > /tmp/test_transcript.txt
docker compose exec -T cie-api python -m tests.eval.annotation.llm_assist --input /tmp/test_transcript.txt --profile performance
```

- [ ] **Step 4: Commit**

```bash
git add backend/tests/eval/annotation/
git commit -m "feat: Tier 2 LLM-assist annotation pipeline for real transcripts"
```

---

### Task 8: Tier 3 — Multi-Model Consensus Pipeline

**Files:**
- Create: `backend/tests/eval/annotation/multi_model.py`
- Create: `backend/tests/eval/annotation/adjudication.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add anthropic and google-generativeai to requirements**

```bash
echo "anthropic>=0.40.0" >> backend/requirements.txt
echo "google-generativeai>=0.8.0" >> backend/requirements.txt
```

- [ ] **Step 2: Implement multi_model.py**

Takes a transcript, sends it to 3 models (gpt-4o, claude-sonnet, gemini-pro) using the same extraction prompt. Computes consensus using embedding similarity. Outputs gold dataset entry with agreement metadata.

- [ ] **Step 3: Implement adjudication.py**

Manages disagreement queue. Outputs a JSON file with items where models disagree, formatted for human adjudication (shows each model's extraction side-by-side).

- [ ] **Step 4: Test multi-model pipeline**

```bash
docker compose exec -T cie-api python -m tests.eval.annotation.multi_model --input /tmp/test_transcript.txt --profile performance
```

Requires: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` environment variables.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/eval/annotation/ backend/requirements.txt
git commit -m "feat: Tier 3 multi-model consensus annotation pipeline"
```

---

### Task 9: Gold Dataset Migration + Baseline Tightening

**Files:**
- Modify: `backend/tests/eval/gold_dataset.json`
- Modify: `backend/tests/eval/baseline_scores.json`

- [ ] **Step 1: Add annotation_method field to all existing gold entries**

Add `"annotation_method": "manual", "annotated_by": "synthetic"` to all 25 existing entries.

- [ ] **Step 2: Run full eval with hybrid matching + two-pass extraction**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/test_extraction_quality.py -v --match-mode=hybrid --extraction-mode=two_pass
```

- [ ] **Step 3: Capture actual scores and update baselines**

Take actual scores from the run, subtract 15% margin, update `baseline_scores.json`. New types should have non-zero baselines now.

- [ ] **Step 4: Run full suite to verify all pass with tightened baselines**

```bash
docker compose exec -T cie-api python -m pytest tests/eval/ -v
```

Expected: All pass with tighter thresholds.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/eval/gold_dataset.json backend/tests/eval/baseline_scores.json
git commit -m "fix: tighten baselines after two-pass + hybrid matching improvements"
```

---

### Task 10: CI Integration

**Files:**
- Modify: `.github/workflows/test.yml`

- [ ] **Step 1: Add eval jobs to CI**

```yaml
# In .github/workflows/test.yml, add:
  eval-fast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt && pip install pytest pytest-asyncio
      - run: cd backend && pytest tests/eval/test_extraction_parsing.py tests/eval/test_api_integration.py -m "fast or integration" -v

  eval-llm:
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch' || github.event.schedule
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt && pip install pytest pytest-asyncio
      - run: cd backend && pytest tests/eval/test_extraction_quality.py -m llm -v --match-mode=hybrid
```

- [ ] **Step 2: Verify fast tests run in CI**

```bash
# Simulate locally:
docker compose exec -T cie-api python -m pytest tests/eval/ -m "fast or integration" -q
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: add eval-fast (every PR) and eval-llm (nightly) jobs"
```

---

## Summary

| Task | What | Est. Time |
|------|------|-----------|
| 1 | Keyword matcher extraction | 15 min |
| 2 | Embedding matcher | 20 min |
| 3 | LLM judge matcher | 15 min |
| 4 | Hybrid matcher orchestrator | 20 min |
| 5 | Two-pass extraction engine | 30 min |
| 6 | Actionable reporting | 25 min |
| 7 | Tier 2 LLM-assist annotation | 20 min |
| 8 | Tier 3 multi-model consensus | 25 min |
| 9 | Gold dataset migration + baselines | 15 min |
| 10 | CI integration | 10 min |
