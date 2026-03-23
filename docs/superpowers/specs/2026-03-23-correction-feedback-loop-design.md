# Few-Shot Correction Feedback Loop

**Date:** 2026-03-23
**Status:** Approved

## Problem

CIE captures corrections via `POST /extractions/{id}/corrections` but never consumes them. The extraction engine makes the same mistakes repeatedly because it has no memory of past corrections. We need a reinforcement loop where corrections improve future extractions.

## Design

### Approach: Few-Shot Correction Injection

When building extraction prompts, query recent corrections and inject them as few-shot examples per extraction type. The LLM sees past mistakes before extracting, learning to avoid them.

### Scoping: Hierarchical (Tenant → Profile)

1. Query corrections for this `tenant_id + extraction_type`, ordered by `created_at DESC`, limit 3
2. If fewer than 3: supplement with profile-wide corrections (other tenants, same profile), anonymized, limit `3 - tenant_count`
3. Only `modify` and `reject` corrections — `accept` confirmations don't teach anything
4. Skip types with zero corrections (zero token overhead)

### Dynamic Cap

Up to 3 examples per extraction type, only for types that have corrections. Types with no correction history get no few-shot examples — zero overhead.

### New File

`backend/app/services/extraction/correction_feedback.py`

```python
def get_correction_examples(
    db: Session,
    tenant_id: UUID,
    profile_id: str,
    extraction_types: set[str],
) -> dict[str, str]:
    """Query corrections and format as few-shot prompt examples.

    Returns {"BLOCKER": "formatted text", ...} — only types with corrections.
    """
```

### Query Logic

```sql
-- Step 1: Tenant-specific corrections
SELECT c.*, e.extraction_type, e.description, e.confidence, e.attributed_to
FROM corrections c
JOIN extractions e ON c.extraction_id = e.id
JOIN conversations conv ON e.conversation_id = conv.id
WHERE e.tenant_id = :tenant_id
  AND conv.profile_id = :profile_id
  AND e.extraction_type IN :types
  AND c.correction_type IN ('modify', 'reject')
ORDER BY c.created_at DESC
LIMIT 3 per type

-- Step 2: Profile-wide fallback (if tenant < 3 per type)
-- Same query but e.tenant_id != :tenant_id
-- Anonymize: strip attributed_to names
```

### Prompt Injection Format

Appended after each extraction type section that has corrections:

```
#### Prior corrections for BLOCKER (learn from these mistakes):
- ORIGINAL: "Validation doubts about model" (confidence: 0.8)
  CORRECTED FIELD: description → "RCA investigation on model validation failures in production"
  REVIEWER NOTE: "This was an RCA discussion, not a knowledge gap"
- ORIGINAL: "Waiting on deployment" (confidence: 0.7)
  REJECTED: This was a status update, not a blocker
```

### Anonymization for Profile-Wide Fallback

Cross-tenant examples strip:
- `attributed_to` names (replace with "a team member")
- Any tenant-specific identifiers in evidence

Keep: extraction type, description, corrected field, correction note — these are the learning signal.

### Integration Points

1. **`prompts.py`**: `build_extraction_prompt_for_types()` accepts optional `correction_examples: dict[str, str]`. Appends examples after each type's section.
2. **`engine.py`**: `extract()` accepts optional `db: Session`. Calls `get_correction_examples()` before building prompts. Passes result through.
3. **`process_conversation.py`**: Passes the existing `db` session to `engine.extract()`.

### Performance

- One DB query per extraction (two if fallback needed) — negligible vs LLM latency
- Token overhead: ~100-150 tokens per corrected type, only for types with corrections
- Zero overhead when no corrections exist

## Testing

1. Submit a correction for a BLOCKER extraction (modify the description)
2. Re-run the same transcript
3. Verify the correction appears in the prompt via worker logs
4. Verify the new extraction reflects the learned pattern
