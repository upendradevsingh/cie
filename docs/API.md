# SalesLens API Reference

Complete REST API documentation for SalesLens v0.1.0.

**Base URL**: `http://localhost:8000/api/v1`
**Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
**ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Table of Contents

- [Authentication](#authentication)
- [Calls](#calls)
- [Quality Parameters](#quality-parameters)
- [Intent Signals](#intent-signals)
- [Persona Types](#persona-types)
- [Analytics](#analytics)
- [Reports](#reports)
- [Users](#users)
- [Integrations](#integrations)
- [API Keys](#api-keys)
- [Webhooks](#webhooks)
- [Error Codes](#error-codes)
- [Rate Limiting](#rate-limiting)

---

## Authentication

SalesLens uses JWT (JSON Web Token) bearer authentication. All endpoints except tenant setup and login require a valid token in the `Authorization` header.

### JWT Flow

1. Create a tenant and admin user via `POST /auth/tenant` (first-time setup).
2. Obtain a token via `POST /auth/login`.
3. Include the token in subsequent requests: `Authorization: Bearer <token>`.
4. Tokens expire after 24 hours by default (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

### Token Claims

The JWT payload includes:

| Claim | Description |
|---|---|
| `sub` | User ID (UUID string) |
| `tenant_id` | Tenant ID (UUID string) |
| `role` | User role (`admin`, `team_lead`, `agent`) |

---

### POST /auth/tenant

Create a new tenant and its first admin user. This is the bootstrap endpoint for new organizations.

**Authentication**: None required

**Request Body**:

```json
{
  "tenant_name": "Acme Corp",
  "tenant_slug": "acme-corp",
  "admin_email": "admin@acme.com",
  "admin_password": "secure-password-123",
  "admin_name": "Jane Admin"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `tenant_name` | string | Yes | Organization name (1-255 chars) |
| `tenant_slug` | string | Yes | URL-safe slug (2-63 chars, lowercase alphanumeric + hyphens) |
| `admin_email` | string | Yes | Email for the first admin user |
| `admin_password` | string | Yes | Password (8-128 chars) |
| `admin_name` | string | Yes | Full name for the admin user (1-255 chars) |

**Response** (`201 Created`):

```json
{
  "tenant": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "is_active": true,
    "created_at": "2026-03-01T12:00:00Z"
  },
  "user": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "admin@acme.com",
    "full_name": "Jane Admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-03-01T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "secure-password-123",
    "admin_name": "Jane Admin"
  }'
```

---

### POST /auth/login

Authenticate with email and password to receive a JWT token.

**Authentication**: None required

**Request Body**:

```json
{
  "email": "admin@acme.com",
  "password": "secure-password-123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password (8-128 chars) |

**Response** (`200 OK`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.com", "password": "secure-password-123"}'
```

**Error Responses**:

| Code | Description |
|---|---|
| 401 | Invalid email or password |
| 403 | User account is deactivated |

---

### POST /auth/register

Register a new user within an existing tenant. The first user registered for a tenant is automatically promoted to admin.

**Authentication**: None required

**Request Body**:

```json
{
  "email": "agent@acme.com",
  "password": "agent-password-123",
  "full_name": "Sales Agent",
  "role": "agent"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `email` | string | Yes | -- | User email address |
| `password` | string | Yes | -- | Password (8-128 chars) |
| `full_name` | string | Yes | -- | Display name (1-255 chars) |
| `role` | string | No | `agent` | Role: `admin`, `team_lead`, `agent` |

**Response** (`201 Created`):

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "agent@acme.com",
  "full_name": "Sales Agent",
  "role": "agent",
  "is_active": true,
  "created_at": "2026-03-01T12:05:00Z"
}
```

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@acme.com",
    "password": "agent-password-123",
    "full_name": "Sales Agent",
    "role": "agent"
  }'
```

---

### GET /auth/me

Get the currently authenticated user's profile.

**Authentication**: Required (Bearer token)

**Response** (`200 OK`):

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@acme.com",
  "full_name": "Jane Admin",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-03-01T12:00:00Z"
}
```

**Example**:

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

## Calls

### POST /calls/upload

Upload a call recording file for transcription and analysis.

**Authentication**: Required

**Content-Type**: `multipart/form-data`

**Form Fields**:

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `file` | file | Yes | -- | Audio file (mp3, wav, m4a, webm). Max 100 MB. |
| `agent_id` | string | No | Current user | UUID of the agent who handled the call |
| `lead_id` | string | No | -- | External lead/contact identifier |
| `lead_name` | string | No | -- | Name of the lead |
| `lead_phone` | string | No | -- | Lead phone number |
| `source` | string | No | -- | Lead source (e.g., website, referral) |
| `language` | string | No | `en` | Language code: `en`, `hi`, `hinglish` |

**Response** (`201 Created`):

Returns a `CallResponse` object with `status: "uploaded"`. The call will be processed asynchronously by the Celery worker.

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "agent_name": "Jane Admin",
  "lead_name": "John Lead",
  "status": "uploaded",
  "created_at": "2026-03-01T12:10:00Z",
  "...": "..."
}
```

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/calls/upload \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -F "file=@/path/to/recording.mp3" \
  -F "lead_name=John Lead" \
  -F "lead_phone=+1234567890" \
  -F "source=website" \
  -F "language=en"
```

**Error Responses**:

| Code | Description |
|---|---|
| 400 | Unsupported file type or invalid agent_id format |
| 404 | Agent not found in this tenant |
| 413 | File exceeds maximum size |

---

### POST /calls/webhook

Receive a call recording URL and metadata from an external CRM or dialer.

**Authentication**: Required

**Request Body**:

```json
{
  "recording_url": "https://storage.example.com/calls/abc123.mp3",
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "agent_email": "agent@acme.com",
  "lead_id": "LEAD-2026-001",
  "lead_name": "Jane Customer",
  "lead_phone": "+1234567890",
  "source": "dialer",
  "custom_fields": {
    "campaign": "Q1 Outbound",
    "deal_value": 15000
  },
  "language": "en"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `recording_url` | string (URL) | Yes | Publicly accessible URL of the recording |
| `agent_id` | string (UUID) | No | Agent UUID (preferred over email) |
| `agent_email` | string | No | Agent email (used if agent_id is absent) |
| `lead_id` | string | No | External lead identifier |
| `lead_name` | string | No | Lead name |
| `lead_phone` | string | No | Lead phone number |
| `source` | string | No | Lead source |
| `custom_fields` | object | No | Up to 5 arbitrary key/value pairs |
| `language` | string | No | Language code: `en`, `hi`, `hinglish` |

**Response** (`201 Created`): Returns a `CallResponse` object.

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/calls/webhook \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "recording_url": "https://storage.example.com/calls/abc123.mp3",
    "lead_name": "Jane Customer",
    "source": "dialer"
  }'
```

---

### GET /calls

List calls with filters and pagination.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `agent_id` | UUID | -- | Filter by agent |
| `date_from` | datetime | -- | Start date (inclusive, ISO-8601) |
| `date_to` | datetime | -- | End date (inclusive, ISO-8601) |
| `score_min` | float | -- | Minimum quality score (0-100) |
| `score_max` | float | -- | Maximum quality score (0-100) |
| `intent_classification` | string | -- | Filter by intent: `hot`, `warm`, `cold` |
| `status` | string | -- | Filter by status: `uploaded`, `transcribing`, `analyzing`, `completed`, `failed` |
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Results per page (1-100) |

**Response** (`200 OK`):

```json
{
  "items": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "agent_name": "Jane Admin",
      "lead_name": "John Lead",
      "duration": 342.5,
      "overall_score": 78.5,
      "intent_classification": "warm",
      "status": "completed",
      "created_at": "2026-03-01T12:10:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

**Example**:

```bash
# All completed calls with score above 70
curl "http://localhost:8000/api/v1/calls?status=completed&score_min=70&page=1&page_size=10" \
  -H "Authorization: Bearer eyJhbGciOi..."

# Hot leads from this week
curl "http://localhost:8000/api/v1/calls?intent_classification=hot&date_from=2026-02-24T00:00:00Z" \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

### GET /calls/{call_id}

Get full call detail including transcript, quality scores, lead intelligence, persona analysis, and action items.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|---|---|---|
| `call_id` | UUID | The call's unique identifier |

**Response** (`200 OK`):

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "agent_name": "Jane Admin",
  "lead_id": "LEAD-001",
  "lead_name": "John Lead",
  "lead_phone": "+1234567890",
  "source": "website",
  "recording_url": null,
  "duration": 342.5,
  "language": "en",
  "status": "completed",
  "custom_fields": null,
  "transcript_segments": [
    {
      "speaker": "agent",
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "Hi John, this is Jane from Acme Corp. How are you today?"
    },
    {
      "speaker": "customer",
      "start_time": 5.5,
      "end_time": 8.1,
      "text": "Hi Jane, I'm doing well. Thanks for calling."
    }
  ],
  "raw_transcript": "Agent: Hi John, this is Jane from Acme Corp...",
  "overall_score": 78.5,
  "quality_scores": [
    {
      "parameter_name": "Opening & Greeting",
      "parameter_category": "Communication",
      "score": 8.5,
      "weight": 0.08,
      "justification": "Agent provided a warm, professional greeting with clear identification."
    }
  ],
  "intent_score": 72.0,
  "intent_classification": "warm",
  "intent_signals": [
    {
      "signal_name": "Budget Mentioned",
      "detected": true,
      "details": "Lead mentioned a budget range of $10K-$15K."
    }
  ],
  "objections": [
    {
      "type": "price",
      "text": "That seems a bit expensive compared to what we were quoted before.",
      "handled": true
    }
  ],
  "persona": {
    "persona_type_name": "Budget-Conscious Decision Maker",
    "budget_score": 7.0,
    "authority_score": 8.5,
    "need_score": 6.0,
    "timeline_score": 5.0,
    "discovery_insights": [
      "Has existing contract ending in 3 months",
      "Looking to consolidate vendors"
    ]
  },
  "action_items": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440010",
      "description": "Send detailed pricing proposal by Friday",
      "category": "follow_up",
      "urgency": "this_week",
      "completed": false
    }
  ],
  "path_to_conversion": [
    "Reference their vendor consolidation goal in the proposal",
    "Include a comparison table vs. their current solution",
    "Offer a pilot period to reduce perceived risk"
  ],
  "follow_up_urgency": "this_week",
  "extracted_metadata": {
    "has_competitor_quote": "Yes, from CompanyX at $12K",
    "contract_end_date": "June 2026",
    "team_size": "15 users"
  },
  "analysis_raw": { "...": "full LLM response (for debugging)" },
  "created_at": "2026-03-01T12:10:00Z",
  "updated_at": "2026-03-01T12:15:00Z"
}
```

**Example**:

```bash
curl http://localhost:8000/api/v1/calls/880e8400-e29b-41d4-a716-446655440003 \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

### GET /calls/{call_id}/transcript

Get the speaker-labeled transcript for a specific call.

**Authentication**: Required

**Response** (`200 OK`):

```json
{
  "call_id": "880e8400-e29b-41d4-a716-446655440003",
  "segments": [
    {
      "speaker": "agent",
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "Hi John, this is Jane from Acme Corp. How are you today?"
    },
    {
      "speaker": "customer",
      "start_time": 5.5,
      "end_time": 8.1,
      "text": "Hi Jane, I'm doing well. Thanks for calling."
    }
  ],
  "raw_text": "Agent: Hi John, this is Jane from Acme Corp..."
}
```

**Example**:

```bash
curl http://localhost:8000/api/v1/calls/880e8400-e29b-41d4-a716-446655440003/transcript \
  -H "Authorization: Bearer eyJhbGciOi..."
```

**Error Responses**:

| Code | Description |
|---|---|
| 404 | Call not found |
| 422 | Transcript not available (call is still being processed) |

---

### PUT /calls/{call_id}/qa-override

Allow admin or team lead to manually correct quality scores for a completed call.

**Authentication**: Required (admin or team_lead role)

**Request Body**:

```json
{
  "scores": [
    {
      "parameter_id": "aaa11111-1111-1111-1111-111111111111",
      "new_score": 7.5,
      "justification": "Agent did ask probing questions, but the LLM missed the context from the Hindi portion."
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `scores` | array | Yes | List of score corrections (at least 1) |
| `scores[].parameter_id` | UUID | Yes | Quality parameter being overridden |
| `scores[].new_score` | float | Yes | Corrected score (0-10) |
| `scores[].justification` | string | Yes | Reason for the override (1-1000 chars) |

**Response** (`200 OK`): Returns the updated `CallResponse` with recalculated overall score.

**Example**:

```bash
curl -X PUT http://localhost:8000/api/v1/calls/880e8400-.../qa-override \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "scores": [
      {
        "parameter_id": "aaa11111-1111-1111-1111-111111111111",
        "new_score": 7.5,
        "justification": "LLM underscored this parameter; agent performed well."
      }
    ]
  }'
```

**Error Responses**:

| Code | Description |
|---|---|
| 403 | Only admin or team_lead roles can perform QA overrides |
| 404 | Call or quality parameter not found |
| 422 | Call is not in "completed" status |

---

## Quality Parameters

Manage tenant-configurable quality scoring parameters. These define what aspects of a call are evaluated and how they are weighted.

### GET /quality-parameters

List all quality parameters for the current tenant.

**Authentication**: Required

**Response** (`200 OK`):

```json
[
  {
    "id": "aaa11111-1111-1111-1111-111111111111",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Opening & Greeting",
    "description": "Proper introduction with energy and professionalism",
    "weight": 0.08,
    "category": "Communication",
    "is_active": true,
    "display_order": 1,
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

**Example**:

```bash
curl http://localhost:8000/api/v1/quality-parameters \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

### POST /quality-parameters

Create a new quality parameter.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "name": "Technical Depth",
  "description": "Agent demonstrates deep product knowledge and can explain technical details clearly",
  "weight": 0.06,
  "category": "Product Knowledge",
  "display_order": 16
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Parameter name (1-255 chars) |
| `description` | string | Yes | What this measures (1-1000 chars, fed to LLM prompt) |
| `weight` | float | Yes | Relative weight (0.0-1.0) |
| `category` | string | Yes | Grouping category (1-100 chars) |
| `display_order` | int | No | UI display order (default: 0) |

**Response** (`201 Created`): Returns the created `QualityParameterResponse`.

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/quality-parameters \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technical Depth",
    "description": "Agent demonstrates deep product knowledge",
    "weight": 0.06,
    "category": "Product Knowledge"
  }'
```

---

### PUT /quality-parameters/{id}

Update a quality parameter. All fields are optional.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "weight": 0.08,
  "is_active": false
}
```

**Response** (`200 OK`): Returns the updated `QualityParameterResponse`.

---

### DELETE /quality-parameters/{id}

Soft-delete a quality parameter (sets `is_active=false`).

**Authentication**: Required (admin role)

**Response** (`204 No Content`)

---

## Intent Signals

Manage tenant-configurable intent signals that the LLM evaluates for each call.

### GET /intent-signals

List all intent signals for the current tenant.

**Authentication**: Required

**Response** (`200 OK`):

```json
[
  {
    "id": "bbb22222-2222-2222-2222-222222222222",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Budget Mentioned",
    "description": "Lead discussed or confirmed their budget for the product/service",
    "is_active": true,
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

---

### POST /intent-signals

Create a new intent signal.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "name": "Regulatory Requirement",
  "description": "Lead mentioned compliance or regulatory requirements that drive the purchase"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Signal name (1-255 chars) |
| `description` | string | Yes | What this signal represents (1-1000 chars) |

**Response** (`201 Created`): Returns the created `IntentSignalResponse`.

---

### PUT /intent-signals/{id}

Update an intent signal.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "description": "Updated description",
  "is_active": false
}
```

---

### DELETE /intent-signals/{id}

Soft-delete an intent signal.

**Authentication**: Required (admin role)

**Response** (`204 No Content`)

---

## Persona Types

Manage admin-configurable persona types for automatic buyer classification.

### GET /persona-types

List all persona types for the current tenant.

**Authentication**: Required

**Response** (`200 OK`):

```json
[
  {
    "id": "ccc33333-3333-3333-3333-333333333333",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Budget-Conscious Decision Maker",
    "description": "Has authority to buy but is very price-sensitive. Needs clear ROI justification.",
    "bant_profile": {
      "budget": { "min": 3, "max": 6 },
      "authority": { "min": 7, "max": 10 },
      "need": { "min": 5, "max": 10 },
      "timeline": { "min": 1, "max": 5 }
    },
    "is_active": true,
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

---

### POST /persona-types

Create a new persona type.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "name": "Urgent Champion",
  "description": "Internal champion with strong need and tight timeline, but may lack final authority",
  "bant_profile": {
    "budget": { "min": 4, "max": 8 },
    "authority": { "min": 3, "max": 6 },
    "need": { "min": 7, "max": 10 },
    "timeline": { "min": 8, "max": 10 }
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Persona label (1-255 chars) |
| `description` | string | Yes | Behavioral description (1-1000 chars) |
| `bant_profile` | object | No | Ideal BANT score ranges for auto-matching |

**Response** (`201 Created`): Returns the created `PersonaTypeResponse`.

---

### PUT /persona-types/{id}

Update a persona type.

**Authentication**: Required (admin role)

---

### DELETE /persona-types/{id}

Soft-delete a persona type.

**Authentication**: Required (admin role)

**Response** (`204 No Content`)

---

## Analytics

### GET /analytics/team

Get team-level aggregate analytics.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_from` | datetime | 30 days ago | Start date |
| `date_to` | datetime | now | End date |

**Response** (`200 OK`):

```json
{
  "total_calls": 247,
  "avg_quality_score": 72.3,
  "hot_leads_count": 18,
  "warm_leads_count": 89,
  "cold_leads_count": 140,
  "calls_by_day": [
    { "date": "2026-02-24", "value": 32, "label": "Calls" },
    { "date": "2026-02-25", "value": 28, "label": "Calls" }
  ],
  "top_agents": [
    {
      "agent_id": "660e8400-...",
      "agent_name": "Jane Admin",
      "avg_quality_score": 85.2,
      "total_calls": 45
    }
  ],
  "score_distribution": {
    "0-20": 5,
    "21-40": 12,
    "41-60": 38,
    "61-80": 120,
    "81-100": 72
  }
}
```

**Example**:

```bash
curl "http://localhost:8000/api/v1/analytics/team?date_from=2026-02-01T00:00:00Z" \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

### GET /analytics/agent/{agent_id}

Get performance analytics for a specific agent.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_from` | datetime | 30 days ago | Start date |
| `date_to` | datetime | now | End date |

**Response** (`200 OK`):

```json
{
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "agent_name": "Jane Admin",
  "total_calls": 45,
  "avg_quality_score": 85.2,
  "avg_intent_score": 68.5,
  "score_trend": [
    { "date": "2026-02-24", "value": 82.0, "label": "Quality Score" },
    { "date": "2026-02-25", "value": 87.5, "label": "Quality Score" }
  ],
  "top_parameters": [
    { "parameter_name": "Opening & Greeting", "avg_score": 9.2 },
    { "parameter_name": "Rapport Building", "avg_score": 8.8 }
  ],
  "areas_for_improvement": [
    { "parameter_name": "Closing Technique", "avg_score": 5.1 },
    { "parameter_name": "Urgency Creation", "avg_score": 5.5 }
  ]
}
```

**Example**:

```bash
curl "http://localhost:8000/api/v1/analytics/agent/660e8400-e29b-41d4-a716-446655440001" \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

### GET /analytics/trends

Get quality score trends over time.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_from` | datetime | 30 days ago | Start date |
| `date_to` | datetime | now | End date |
| `agent_id` | UUID | -- | Optional agent filter |
| `granularity` | string | `day` | `day`, `week`, or `month` |

**Response** (`200 OK`):

```json
[
  { "date": "2026-02-24", "value": 71.2, "label": "Avg Quality Score" },
  { "date": "2026-02-25", "value": 73.8, "label": "Avg Quality Score" },
  { "date": "2026-02-26", "value": 69.5, "label": "Avg Quality Score" }
]
```

**Example**:

```bash
curl "http://localhost:8000/api/v1/analytics/trends?granularity=week" \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

## Reports

### POST /reports/weekly

Trigger generation of a weekly report for the specified time window.

**Authentication**: Required (admin or team_lead role)

**Request Body**:

```json
{
  "week_start": "2026-02-24",
  "week_end": "2026-03-02"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `week_start` | date | Yes | Start date (Monday) |
| `week_end` | date | No | End date (Sunday). Defaults to week_start + 6 days. |

**Response** (`201 Created`):

```json
{
  "id": "ddd44444-4444-4444-4444-444444444444",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "week_start": "2026-02-24",
  "week_end": "2026-03-02",
  "report_data": {},
  "status": "pending",
  "created_at": "2026-03-02T10:00:00Z"
}
```

**Example**:

```bash
curl -X POST http://localhost:8000/api/v1/reports/weekly \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{"week_start": "2026-02-24"}'
```

---

### GET /reports/weekly/{report_id}

Get a generated weekly report.

**Authentication**: Required

**Response** (`200 OK`):

```json
{
  "id": "ddd44444-4444-4444-4444-444444444444",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "week_start": "2026-02-24",
  "week_end": "2026-03-02",
  "report_data": {
    "summary": {
      "total_calls": 132,
      "avg_quality_score": 74.2,
      "hot_leads": 12,
      "improvement_vs_last_week": "+3.1%"
    },
    "agent_breakdown": [
      {
        "agent_name": "Jane Admin",
        "total_calls": 28,
        "avg_quality_score": 82.1,
        "top_strength": "Opening & Greeting",
        "key_improvement": "Closing Technique"
      }
    ],
    "highlights": [
      "Team quality score improved 3.1% week-over-week",
      "12 hot leads generated (up from 8 last week)"
    ]
  },
  "status": "completed",
  "created_at": "2026-03-02T10:00:00Z"
}
```

---

## Users

### GET /users

List all users in the current tenant.

**Authentication**: Required (admin or team_lead role)

**Response** (`200 OK`):

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "admin@acme.com",
    "full_name": "Jane Admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

---

### PUT /users/{user_id}

Update a user's profile (name, role, active status).

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "role": "team_lead",
  "is_active": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `full_name` | string | No | Updated display name |
| `role` | string | No | Updated role: `admin`, `team_lead`, `agent` |
| `is_active` | bool | No | Enable/disable the user |

---

## Integrations

### GET /integrations

List all integrations for the current tenant.

**Authentication**: Required (admin role)

---

### POST /integrations

Register a new CRM/dialer integration.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "name": "Salesforce Production",
  "type": "crm_webhook",
  "config": {
    "webhook_url": "https://hooks.salesforce.com/...",
    "auth_header": "Bearer sf-token-123",
    "field_mapping": {
      "overall_score": "Quality_Score__c",
      "intent_classification": "Lead_Intent__c"
    }
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Friendly name (1-255 chars) |
| `type` | string | Yes | Type: `crm_webhook`, `dialer`, `email`, `custom` |
| `config` | object | Yes | Integration-specific configuration |

**Response** (`201 Created`): Returns the created `IntegrationResponse`.

---

### PUT /integrations/{id}

Update an integration's name, config, or active status.

**Authentication**: Required (admin role)

---

### DELETE /integrations/{id}

Deactivate an integration.

**Authentication**: Required (admin role)

---

## API Keys

API keys provide an alternative authentication method for webhook integrations.

### GET /api-keys

List all API keys for the current tenant (key values are hidden).

**Authentication**: Required (admin role)

**Response** (`200 OK`):

```json
[
  {
    "id": "eee55555-5555-5555-5555-555555555555",
    "name": "Dialer Integration",
    "is_active": true,
    "last_used_at": "2026-03-01T15:30:00Z",
    "created_at": "2026-02-15T10:00:00Z"
  }
]
```

---

### POST /api-keys

Generate a new API key. The key value is only returned once at creation time.

**Authentication**: Required (admin role)

**Request Body**:

```json
{
  "name": "Dialer Integration"
}
```

**Response** (`201 Created`):

```json
{
  "id": "eee55555-5555-5555-5555-555555555555",
  "name": "Dialer Integration",
  "key": "slk_a1b2c3d4e5f6g7h8i9j0...",
  "created_at": "2026-03-02T10:00:00Z"
}
```

> **Important**: Store the `key` value securely. It cannot be retrieved again after this response.

---

### DELETE /api-keys/{id}

Revoke an API key.

**Authentication**: Required (admin role)

**Response** (`204 No Content`)

---

## Webhooks

### Inbound Webhook Format

When integrating with CRM or dialer systems, configure them to send POST requests to `/api/v1/calls/webhook` with the following JSON format:

```json
{
  "recording_url": "https://your-storage.com/recordings/call-123.mp3",
  "agent_id": "uuid-of-agent",
  "agent_email": "agent@company.com",
  "lead_id": "CRM-LEAD-456",
  "lead_name": "John Smith",
  "lead_phone": "+1234567890",
  "source": "outbound-dialer",
  "custom_fields": {
    "campaign_id": "CAMP-001",
    "deal_stage": "discovery"
  },
  "language": "en"
}
```

**Authentication**: Use either a JWT bearer token or an API key in the `X-API-Key` header.

### Outbound Webhook (CRM Sync)

When configured via the Integrations API, SalesLens pushes analysis results to your CRM after each call is processed. The outbound payload:

```json
{
  "event": "call.analyzed",
  "call_id": "880e8400-e29b-41d4-a716-446655440003",
  "lead_id": "CRM-LEAD-456",
  "overall_score": 78.5,
  "intent_classification": "warm",
  "intent_score": 72.0,
  "follow_up_urgency": "this_week",
  "action_items": ["Send pricing proposal by Friday"],
  "persona_type": "Budget-Conscious Decision Maker",
  "extracted_metadata": {
    "has_competitor_quote": "Yes, from CompanyX at $12K"
  },
  "timestamp": "2026-03-01T12:15:00Z"
}
```

The webhook URL, auth headers, and field mapping are configured in the integration settings.

---

## Error Codes

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|---|---|---|
| 400 | Bad Request | Invalid input, unsupported file type, validation failure |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Insufficient role permissions |
| 404 | Not Found | Resource does not exist or belongs to another tenant |
| 409 | Conflict | Duplicate email, duplicate slug |
| 413 | Payload Too Large | File exceeds MAX_FILE_SIZE_MB |
| 422 | Unprocessable Entity | Valid JSON but logically invalid (e.g., transcript not ready) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

### Validation Errors

For validation failures, the response includes field-level details:

```json
{
  "detail": [
    {
      "loc": ["body", "weight"],
      "msg": "Input should be less than or equal to 1",
      "type": "less_than_equal"
    }
  ]
}
```

---

## Rate Limiting

SalesLens applies the following default rate limits:

| Endpoint Category | Limit |
|---|---|
| Authentication | 10 requests/minute per IP |
| Call Upload | 30 requests/minute per tenant |
| Webhook Ingestion | 60 requests/minute per tenant |
| Read Endpoints | 120 requests/minute per tenant |
| Analytics | 30 requests/minute per tenant |

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 117
X-RateLimit-Reset: 1709298060
```

When rate limited, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## System Endpoints

These endpoints do not require authentication.

### GET /health

Health check used by Docker, load balancers, and monitoring.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "service": "SalesLens",
  "version": "0.1.0"
}
```

### GET /

Root endpoint with basic application information.

```bash
curl http://localhost:8000/
```

```json
{
  "app": "SalesLens",
  "version": "0.1.0",
  "tagline": "AI lens into every sales conversation",
  "docs": "/docs"
}
```
