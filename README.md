# CIE — Conversation Intelligence Engine

A headless, profile-driven conversation extraction engine. Ingest voice, text, chat, or meeting conversations — extract structured intelligence based on configurable YAML profiles.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

The API runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Architecture

```
voice/text/chat → CIE API → Celery Worker → LLM (gpt-4o-mini)
                                ↑                    ↓
                           Transcription      Extractions (JSONB)
                         (Deepgram/Whisper)   stored per profile
```

## Profiles

Profiles are YAML files in `backend/app/profiles/` that define what to extract:

| Profile | Use Case | Extraction Types |
|---------|----------|-----------------|
| `performance` | 1:1s, check-ins, team meetings | COMMITMENT, BLOCKER, FEEDBACK, GOAL_UPDATE, ACTION_ITEM, SENTIMENT, DECISION |
| `sales` | Sales calls, discovery calls | QUALITY_SCORE, INTENT_SIGNAL, PERSONA_BANT, OBJECTION, LEAD_INTENT |

## API

### Submit a Conversation

```bash
POST /api/v1/conversations
Authorization: Bearer <jwt>

{
  "source": "text",
  "profile": "performance",
  "participants": [
    {"externalId": "u1", "name": "Alice", "role": "manager"},
    {"externalId": "u2", "name": "Bob", "role": "engineer"}
  ],
  "segments": [
    {"speaker": "u1", "text": "How are things going?"},
    {"speaker": "u2", "text": "I'll have the feature done by Friday."}
  ]
}

→ 202 Accepted
{ "id": "uuid", "status": "pending", ... }
```

### Get Extractions

```bash
GET /api/v1/conversations/{id}/extractions
Authorization: Bearer <jwt>

→ 200 OK
[
  {
    "extraction_type": "COMMITMENT",
    "description": "Bob committed to completing the feature by Friday",
    "confidence": 0.92,
    "attributes": { "deadline": "Friday", "specificity": "high" }
  }
]
```

### Audio Conversations

```bash
POST /api/v1/conversations
{
  "source": "voice",
  "profile": "sales",
  "audio_url": "https://...",
  "participants": [...]
}
```

Audio is transcribed by Deepgram (primary) or Whisper (fallback), then extracted.

## JWT Auth

CIE validates JWTs issued by the calling service. The shared secret is `JWT_SECRET` in `.env`.

Token must contain:
- `tenant_id` (UUID) — required
- `user_id` (UUID) — optional

```python
import jwt
token = jwt.encode(
    {"tenant_id": "your-tenant-uuid", "user_id": "user-uuid", "exp": ...},
    secret,
    algorithm="HS256"
)
```

## Custom Profiles

Add `backend/app/profiles/myprofile.yaml`:

```yaml
profile_id: myprofile
version: "1.0"
display_name: "My Custom Profile"
description: "Extract X from Y conversations"

llm:
  model: gpt-4o-mini
  temperature: 0.15
  max_tokens: 2048

extraction_types:
  MY_TYPE:
    enabled: true
    confidence_threshold: 0.80
    description: "Description of what to extract"
    attributes:
      - name: my_field
        type: string
```

## Development

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## First Client: PeakPerf

CIE was built for PeakPerf (Java/Spring Boot performance management). PeakPerf submits 1:1 transcripts using the `performance` profile and maps extractions to its domain models:

```
CIE COMMITMENT  → PeakPerf Commitment table
CIE BLOCKER     → PeakPerf BlockerTracking
CIE FEEDBACK    → PeakPerf FeedbackNote
CIE SENTIMENT   → PeakPerf CheckInMood
CIE GOAL_UPDATE → PeakPerf GoalProgress
```
