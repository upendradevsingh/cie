# Correction Productisation: Review Queue + Analytics

**Date:** 2026-03-23
**Status:** Approved

## Problem

The correction feedback loop works (corrections improve future extractions via few-shot injection), but clients have no way to:
1. Know which extractions need review
2. See correction history
3. Track whether corrections are improving quality over time

Without these, the RL loop has no input — nobody submits corrections because nobody knows what to correct.

## Design

### 1. Review Queue: `GET /api/v1/extractions/review-queue`

Returns uncorrected extractions ranked by review priority using a composite score:

```
priority = (1 - confidence) * 0.4
         + type_correction_rate * 0.35
         + recency_score * 0.25
```

- **confidence**: extraction's own confidence score (lower = more likely wrong)
- **type_correction_rate**: historical correction rate for this extraction_type + tenant (0.0-1.0). Higher rate = this type is error-prone.
- **recency_score**: linear decay — 1.0 for today, 0.0 for 30+ days old. Recent extractions matter more.

**Query params:** `?limit=20&offset=0&extraction_type=BLOCKER&profile_id=performance`

**Response:** List of extractions with added `review_priority` field, sorted descending.

### 2. Correction History: `GET /api/v1/extractions/{id}/corrections`

Returns all corrections for a given extraction. Simple query — data already exists.

**Response:** List of `CorrectionResponse` objects with field_name, original_value, corrected_value, correction_type, correction_note, created_at.

### 3. Correction Analytics: `GET /api/v1/analytics/corrections`

Returns per-type correction rates and improvement trends.

**Query params:** `?days=30&profile_id=performance`

**Response:**
```json
{
  "by_type": {
    "BLOCKER": {
      "total_extractions": 45,
      "corrected_count": 12,
      "correction_rate": 0.267,
      "trend": "improving"
    }
  },
  "overall": {
    "total_extractions": 200,
    "corrected_count": 34,
    "correction_rate": 0.17,
    "trend": "improving"
  },
  "period_days": 30
}
```

**Trend computation:** Compare correction rate in the recent half of the period vs the older half. If rate decreased by >5%, trend is "improving". If increased by >5%, "degrading". Otherwise "stable".

### File Changes

- `backend/app/schemas/extraction.py` — Add `ReviewQueueItem`, `CorrectionAnalyticsResponse`, `CorrectionHistoryResponse`
- `backend/app/api/extractions.py` — Add review-queue and correction-history endpoints
- `backend/app/api/analytics.py` — New file, correction analytics endpoint
- `backend/app/main.py` — Register analytics router

### Client Integration Flow

1. CIE extracts → client receives extractions (callback or polling)
2. Client renders extractions in their UI with accept/modify/reject buttons
3. User reviews → `POST /extractions/{id}/corrections`
4. Client fetches `GET /extractions/review-queue` to surface items needing review
5. Client shows `GET /analytics/corrections` dashboard to track improvement
6. CIE automatically uses corrections to improve future extractions (few-shot RL)
