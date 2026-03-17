# CIE Client Onboarding Guide

A comprehensive guide for integrating your service with the **Conversation Intelligence Engine (CIE)**.

## What CIE Does

CIE is a headless, profile-driven extraction engine. You send it conversations (text segments or audio), and it returns structured intelligence — commitments, blockers, feedback, action items, sentiment, and more.

CIE does **not** manage users, sessions, or UI. It validates JWTs from your service and isolates data by tenant.

## Quick Start

### 1. Get Your Shared JWT Secret

CIE authenticates via **HS256 JWT tokens signed with a shared secret**. You sign tokens on your side; CIE validates them.

**Local development:**
```
JWT_SECRET=local-dev-secret-for-testing-only
CIE_URL=http://localhost:7070
```

**Production:**
```bash
# Read from AWS SSM Parameter Store
aws ssm get-parameter --name /cie/secrets/jwt-secret --with-decryption --query Parameter.Value --output text --region us-east-1
```

### 2. Generate a JWT Token

Sign a short-lived JWT (5 min recommended) with these claims:

| Claim | Type | Required | Description |
|-------|------|----------|-------------|
| `tenantId` or `tenant_id` | string/number | **Yes** | Your org/tenant identifier (any format — UUID, Long, string) |
| `userId` or `user_id` | string/number | No | The calling user or service ID |
| `sub` | string | No | JWT subject (typically same as userId) |
| `iat` | number | Yes | Issued-at timestamp (epoch seconds) |
| `exp` | number | Yes | Expiration timestamp (epoch seconds) |

**Java example:**
```java
String token = Jwts.builder()
    .claim("tenantId", orgId)           // your org ID (Long, UUID, or String)
    .claim("userId", "my-service")
    .setSubject("my-service")
    .setIssuedAt(new Date())
    .setExpiration(Date.from(Instant.now().plus(5, ChronoUnit.MINUTES)))
    .signWith(Keys.hmacShaKeyFor(jwtSecret.getBytes()), SignatureAlgorithm.HS256)
    .compact();
```

**Python example:**
```python
from jose import jwt
import time

token = jwt.encode({
    "tenant_id": "your-org-id",
    "user_id": "your-service",
    "sub": "your-service",
    "iat": int(time.time()),
    "exp": int(time.time()) + 300,
}, JWT_SECRET, algorithm="HS256")
```

**cURL example:**
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:7070/api/v1/profiles
```

### 3. Choose a Profile

CIE ships with two built-in profiles. Profiles define **what** to extract.

| Profile | Use Case | Extraction Types |
|---------|----------|-----------------|
| `performance` | 1:1s, check-ins, team meetings | COMMITMENT, BLOCKER, FEEDBACK, GOAL_UPDATE, ACTION_ITEM, SENTIMENT, DECISION |
| `sales` | Sales calls, discovery, demos | QUALITY_SCORE, INTENT_SIGNAL, PERSONA_BANT, OBJECTION, LEAD_INTENT |

List profiles: `GET /api/v1/profiles`

### 4. Submit a Conversation

**POST** `/api/v1/conversations`

```json
{
  "source": "my-app",
  "profile": "performance",
  "participants": [
    {"externalId": "mgr-1", "name": "Sarah", "role": "manager"},
    {"externalId": "emp-1", "name": "James", "role": "employee"}
  ],
  "segments": [
    {"speaker": "Sarah", "text": "How's the migration going?", "startTime": 0.0, "endTime": 3.0},
    {"speaker": "James", "text": "70% done, blocked on auth endpoints.", "startTime": 3.5, "endTime": 8.0}
  ],
  "language": "en"
}
```

**Response:** `202 Accepted`
```json
{
  "id": "uuid-of-conversation",
  "status": "pending",
  "tenant_id": "your-org-id",
  ...
}
```

Processing is **asynchronous** — the conversation is queued for extraction by a background worker.

### 5. Poll for Results

**GET** `/api/v1/conversations/{id}`

Poll until `status` is `completed` or `failed`:
- `pending` → queued
- `transcribing` → processing audio (if audio_url provided)
- `extracting` → LLM is analyzing
- `completed` → extractions ready
- `failed` → check `error_message`

### 6. Get Extractions

**GET** `/api/v1/conversations/{id}/extractions`

```json
[
  {
    "id": "extraction-uuid",
    "extraction_type": "COMMITMENT",
    "description": "James committed to finishing the data layer by Friday.",
    "confidence": 0.90,
    "attributed_to": {"name": "James", "role": "employee"},
    "evidence": "I can definitely have the data layer done by Friday.",
    "attributes": {"deadline": "Friday", "specificity": "high"}
  },
  {
    "id": "extraction-uuid-2",
    "extraction_type": "BLOCKER",
    "description": "Blocked on auth service endpoints.",
    "confidence": 0.85,
    "attributes": {"severity": "high", "status": "open"}
  }
]
```

### 7. Submit Corrections (Optional)

**POST** `/api/v1/extractions/{id}/corrections`

```json
{
  "field_name": "confidence",
  "original_value": "0.85",
  "corrected_value": "0.95",
  "correction_type": "modify",
  "correction_note": "Confidence was higher than estimated"
}
```

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | No | Health check |
| `GET` | `/api/v1/profiles` | Yes | List extraction profiles |
| `GET` | `/api/v1/profiles/{id}` | Yes | Get specific profile |
| `POST` | `/api/v1/conversations` | Yes | Submit conversation (returns 202) |
| `GET` | `/api/v1/conversations/{id}` | Yes | Get conversation status |
| `GET` | `/api/v1/conversations` | Yes | List conversations for tenant |
| `GET` | `/api/v1/conversations/{id}/extractions` | Yes | Get extractions |
| `POST` | `/api/v1/extractions/{id}/corrections` | Yes | Submit correction |

## Tenant Isolation

CIE enforces **strict tenant isolation**:
- Every record is tagged with `tenant_id` from your JWT
- All queries are filtered by `tenant_id`
- Tenant A can **never** see Tenant B's data
- PostgreSQL Row-Level Security (RLS) provides database-level enforcement

Your `tenant_id` can be any string — UUID, Long, slug, etc. CIE treats it as an opaque identifier.

## Multi-Tenant Integration Pattern

For services with multiple organizations/tenants:

```
Per-request flow:
1. User in Org X triggers action in your service
2. Your service signs JWT with tenant_id = Org X's ID
3. Your service calls CIE with that JWT
4. CIE validates JWT, extracts tenant_id, isolates all data
```

**Do not** use a single static token for all tenants. Generate per-tenant tokens (cached for a few minutes is fine).

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CIE_BASE_URL` | Yes | — | CIE service URL (e.g., `http://localhost:7070`) |
| `CIE_JWT_SECRET` | Yes | — | Shared JWT secret (must match CIE's `JWT_SECRET`) |
| `CIE_ENABLED` | No | `true` | Global feature flag |
| `CIE_CONNECT_TIMEOUT_MS` | No | `5000` | HTTP connect timeout |
| `CIE_READ_TIMEOUT_MS` | No | `10000` | HTTP read timeout |
| `CIE_POLL_INTERVAL_MS` | No | `2000` | Polling interval for extraction results |
| `CIE_POLL_MAX_ATTEMPTS` | No | `10` | Max poll attempts before giving up |

### Production (AWS)

CIE runs as a private service in the VPC. Discover its address via SSM:

```bash
CIE_HOST=$(aws ssm get-parameter --name /cie/private-ip --query Parameter.Value --output text --region us-east-1)
CIE_BASE_URL="http://${CIE_HOST}:8000"
```

## Extraction Types

### Performance Profile

| Type | Description | Key Attributes |
|------|-------------|---------------|
| `COMMITMENT` | Promise or commitment by a participant | `deadline`, `specificity`, `owner_id` |
| `BLOCKER` | Something preventing progress | `severity`, `blocked_by`, `status` |
| `FEEDBACK` | Performance feedback given | `recipient`, `sentiment`, `competency` |
| `GOAL_UPDATE` | Progress update on a goal | `progress_pct`, `direction` |
| `ACTION_ITEM` | Task that needs to be done | `assignee`, `due_date`, `priority` |
| `SENTIMENT` | Emotional tone and engagement | `score` (1-5), `energy_level` |
| `DECISION` | Decision made during conversation | `decided_by`, `impact` |

### Sales Profile

| Type | Description | Key Attributes |
|------|-------------|---------------|
| `QUALITY_SCORE` | Quality assessment | `parameter_name`, `score` (0-10), `justification` |
| `INTENT_SIGNAL` | Buying intent signal | `signal_name`, `detected`, `details` |
| `PERSONA_BANT` | BANT analysis | `budget_score`, `authority_score`, `need_score`, `timeline_score` |
| `OBJECTION` | Prospect objection | `category`, `rebuttal`, `resolved` |
| `LEAD_INTENT` | Overall lead intent | `intent_score` (0-100), `classification`, `follow_up_urgency` |

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Process response |
| 202 | Accepted (async) | Poll for results |
| 400 | Bad request (invalid profile, missing segments) | Fix request |
| 401 | Invalid/expired JWT | Regenerate token |
| 403 | No auth header | Add Bearer token |
| 404 | Conversation/extraction not found | Check ID |
| 500 | Server error | Retry with backoff |

## Best Practices

1. **Short-lived tokens** — Generate JWTs with 5-minute expiry. Never use long-lived static tokens in production.
2. **Fire and forget** — Submit conversations asynchronously. Don't block your user flow on CIE processing.
3. **Poll with backoff** — Start polling after 2-3 seconds. Most text extractions complete in 10-20 seconds.
4. **Filter by type** — Only store the extraction types you need. Use tenant config to control this.
5. **Handle failures gracefully** — CIE extraction is supplementary. If it fails, your core flow should continue.
6. **Log conversation IDs** — Store the CIE conversation ID for audit trails and debugging.
