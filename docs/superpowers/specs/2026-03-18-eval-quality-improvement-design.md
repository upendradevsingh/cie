# CIE Eval Quality Improvement — Design Spec

**Date:** 2026-03-18
**Status:** Approved
**Author:** Upendra + Claude

## Problem

CIE v3.0 has 12 extraction types powered by 8 research frameworks, but the eval suite masks real quality issues:
- New types (PSYCHOLOGICAL_SAFETY, MINDSET_SIGNAL, ACCOUNTABILITY_SIGNAL) have 0% recall
- Baselines set to 0 just to make CI green — not a real quality gate
- Keyword matching misses semantic equivalents ("Friday" ≠ "end of week")
- All 25 gold conversations are synthetic — no real transcript validation
- Single LLM call with 12 types causes prompt overload — subtle types ignored

## Design

### 1. Three-Tier Annotation Pipeline

Build infrastructure for all three tiers now; use progressively as data becomes available.

**Tier 1 — Manual (today)**
- Human writes synthetic conversations with expected extractions
- Current 25 conversations continue to serve as controlled test cases
- Used for edge cases, all-types coverage, Hinglish, empty/single-word

**Tier 2 — LLM-Assist (when real transcripts available)**
- Real transcript uploaded → CIE extracts → human reviews/corrects/adds
- UI: show extractions with accept/reject/edit per item
- Much faster than manual — editing is easier than creating from scratch
- Target: 10-15 real transcripts annotated this way

**Tier 3 — Multi-Model Consensus (at scale)**
- Same transcript sent to gpt-4o, claude-sonnet, gemini-pro independently
- Consensus engine compares outputs:
  - 3/3 agree → auto-accept as gold label
  - 2/3 agree → accept with flag
  - 1/3 only → human adjudication queue
  - 0/3 → discard
- Agreement computed via embedding similarity (>0.75 cosine = agree)
- Cost: ~$0.03/transcript (3 LLM calls + embeddings)

**All tiers produce the same gold dataset format:**
```json
{
  "id": "gold_026",
  "annotation_method": "manual|llm_assist|multi_model_consensus",
  "annotated_by": "upendra",
  "annotation_date": "2026-03-18",
  "consensus_models": ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"],
  "agreement_rate": 0.85,
  "adjudicated_items": [],
  "...existing gold format fields..."
}
```

### 2. Hybrid Matching Engine

Replace keyword-only matching with a three-layer pipeline:

```
Layer 1: Type Match (instant, free)
  → extraction_type must match expected type
  → Eliminates ~60% of comparisons

Layer 2: Embedding Similarity (~$0.001/run)
  → Cosine similarity between actual description and expected keywords
  → Score > 0.75 → match
  → Score < 0.50 → no match
  → 0.50-0.75 → borderline → Layer 3

Layer 3: LLM-as-Judge (only borderline, ~$0.002/call)
  → "Is this extraction a correct match? yes/partial/no"
  → Only fires for ~10-15% of comparisons
```

**Configurable per run:**
```bash
pytest -m llm --match-mode=keyword     # current (free, fast)
pytest -m llm --match-mode=embedding   # embeddings only (cheap, better)
pytest -m llm --match-mode=hybrid      # embeddings + LLM judge (best)
```

**Total cost per full eval run:** ~$0.01 (hybrid mode, 25 conversations)

### 3. Two-Pass Extraction

Split 12 extraction types into two focused LLM calls:

**Pass 1 — Content Extraction (what was said)**
- COMMITMENT, BLOCKER, ACTION_ITEM, DECISION, GOAL_UPDATE, RECOGNITION
- Clear textual markers, current prompts work well
- Focused prompt: ~1500 tokens

**Pass 2 — Behavioral Extraction (how it was said)**
- FEEDBACK, COACHING_MOMENT, PSYCHOLOGICAL_SAFETY, MINDSET_SIGNAL, ACCOUNTABILITY_SIGNAL, SENTIMENT
- Requires reading between the lines, detecting tone/patterns
- Different system prompt optimized for behavioral analysis
- Focused prompt: ~1500 tokens

**Why two passes:**
- Each pass gets focused instructions instead of competing with 12 types
- Pass 2 gets a behavioral-analysis-specific system prompt
- Expected: new types go from 0% recall to meaningful numbers
- Cost: ~2x per conversation ($0.004 → $0.008 with gpt-4o)
- A/B testable: compare single-pass vs two-pass in eval

**Configurable:**
- `extraction_mode: single_pass | two_pass` in profile config
- Can disable pass 2 for cost-sensitive tenants

### 4. Actionable Reporting

Replace raw precision/recall tables with diagnostic reports:

**Report sections:**
1. **Overall scores** with delta tracking (↑/↓ from previous run)
2. **Per-type breakdown** split by Pass 1 (content) and Pass 2 (behavioral)
3. **Worst misses** — specific gold items the LLM keeps failing on
4. **Confusion patterns** — which types get mixed up (e.g., ACTION_ITEM ↔ COMMITMENT)
5. **Annotation coverage** — synthetic vs real transcript ratio
6. **Auto-recommendations** — generated from score patterns ("improve X prompt", "add real transcripts for Y")

**Status indicators:** ✅ strong (F1 > 0.60) | ⚠️ needs work (0.30-0.60) | 🔧 early (< 0.30)

### 5. Baseline Tightening Strategy

Current baselines are too loose. Tightening schedule:

| Phase | When | Core types baseline | New types baseline |
|-------|------|--------------------|--------------------|
| Now | v3.0 calibration | F1 ≥ 0.40 | F1 ≥ 0.00 |
| After two-pass | +1 week | F1 ≥ 0.50 | F1 ≥ 0.15 |
| After 10 real transcripts | +2 weeks | F1 ≥ 0.55 | F1 ≥ 0.25 |
| After multi-model consensus | +1 month | F1 ≥ 0.60 | F1 ≥ 0.35 |

Baselines ratchet up only — never relaxed without explicit justification.

## File Structure

```
backend/
├── tests/eval/
│   ├── gold_dataset.json            (existing — add annotation_method field)
│   ├── baseline_scores.json         (existing — tighten over time)
│   ├── metrics.py                   (extend: embedding matcher, LLM judge, report generator)
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── keyword_matcher.py       (extract current logic)
│   │   ├── embedding_matcher.py     (new: cosine similarity via OpenAI embeddings)
│   │   ├── llm_judge.py             (new: borderline adjudication)
│   │   └── hybrid_matcher.py        (new: orchestrates all three layers)
│   ├── annotation/
│   │   ├── __init__.py
│   │   ├── llm_assist.py            (Tier 2: CIE extract → human review format)
│   │   ├── multi_model.py           (Tier 3: consensus across models)
│   │   └── adjudication.py          (disagreement queue for human review)
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── eval_report.py           (diagnostic report generator)
│   │   └── delta_tracker.py         (compare against previous run)
│   ├── test_extraction_parsing.py   (existing — unchanged)
│   ├── test_extraction_quality.py   (existing — update to use hybrid matching)
│   ├── test_api_integration.py      (existing — unchanged)
│   └── test_prompt_stability.py     (existing — unchanged)
├── app/services/extraction/
│   ├── engine.py                    (extend: two-pass mode)
│   ├── prompts.py                   (split: content_prompt + behavioral_prompt)
│   └── behavioral_prompts.py        (new: Pass 2 system prompt + builder)
```

## Implementation Order

1. **Hybrid matching engine** — embedding + LLM judge (improves eval accuracy without changing extraction)
2. **Two-pass extraction** — split content vs behavioral (improves extraction quality)
3. **Actionable reporting** — diagnostic reports with deltas and recommendations
4. **Tier 2 annotation pipeline** — LLM-assist for real transcripts
5. **Tier 3 multi-model consensus** — gpt-4o + claude + gemini voting
6. **Baseline tightening** — ratchet up thresholds as quality improves

## Success Criteria

- New types (PSYCH_SAFETY, MINDSET, ACCOUNTABILITY) achieve F1 > 0.25
- Core types (COMMITMENT, BLOCKER) maintain F1 > 0.60
- At least 10 real transcripts in gold dataset within 2 weeks
- Eval cost per full run < $0.05
- All 47+ tests pass with tightened baselines

## Cost

| Component | Per run | Monthly (daily runs) |
|-----------|---------|---------------------|
| Extraction (25 convs × 2 passes) | ~$0.20 | ~$6 |
| Embedding matching | ~$0.001 | ~$0.03 |
| LLM judge (borderline only) | ~$0.01 | ~$0.30 |
| Multi-model annotation (per transcript) | ~$0.03 | On-demand |
| **Total eval run** | **~$0.21** | **~$6.30** |
