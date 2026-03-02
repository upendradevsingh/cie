# SalesLens Configuration Guide

This guide covers configuring SalesLens after initial deployment, including quality scoring parameters, intent signals, persona types, CRM integrations, and provider setup.

---

## Table of Contents

- [Initial Setup](#initial-setup)
- [Quality Parameters](#quality-parameters)
- [Intent Signals](#intent-signals)
- [Persona Types](#persona-types)
- [CRM Integration](#crm-integration)
- [API Key Management](#api-key-management)
- [Multi-Tenant Setup](#multi-tenant-setup)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Transcription Provider Setup](#transcription-provider-setup)
- [Email and Reports](#email-and-reports)
- [Storage Configuration](#storage-configuration)

---

## Initial Setup

After deploying SalesLens (see [DEPLOYMENT.md](DEPLOYMENT.md)), complete these steps:

### 1. Create a Tenant

Every organization using SalesLens operates within a tenant. Create your first one:

```bash
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Your Company",
    "tenant_slug": "your-company",
    "admin_email": "admin@yourcompany.com",
    "admin_password": "a-secure-password",
    "admin_name": "Admin User"
  }'
```

Save the `access_token` from the response. Use it for all subsequent API calls.

### 2. Register Team Members

```bash
# Register a team lead
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teamlead@yourcompany.com",
    "password": "secure-password",
    "full_name": "Team Lead",
    "role": "team_lead"
  }'

# Register agents
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent1@yourcompany.com",
    "password": "secure-password",
    "full_name": "Sales Agent 1",
    "role": "agent"
  }'
```

### 3. Configure Scoring and Analysis

Follow the sections below to customize quality parameters, intent signals, and persona types for your sales process.

---

## Quality Parameters

Quality parameters define how call quality is scored. Each parameter represents a specific aspect of a sales call (e.g., "Objection Handling", "Opening & Greeting"). SalesLens ships with 15 sensible default parameters, but you can customize them for your organization.

### Default Parameters

SalesLens creates these parameters for each new tenant:

| # | Parameter | Category | Default Weight | Description |
|---|---|---|---|---|
| 1 | Opening & Greeting | Communication | 0.08 | Proper introduction with energy and professionalism |
| 2 | Need Discovery | Sales Technique | 0.10 | Asked probing questions, understood requirements |
| 3 | Product Knowledge | Product | 0.08 | Accurate information, handled features well |
| 4 | Objection Handling | Sales Technique | 0.10 | Addressed concerns, provided rebuttals |
| 5 | Pricing Discussion | Sales Technique | 0.07 | Transparent, value-framed pricing |
| 6 | Urgency Creation | Sales Technique | 0.06 | Time-sensitive offers, scarcity tactics |
| 7 | Next Steps | Process | 0.08 | Clear action items, follow-up scheduled |
| 8 | Call Control | Communication | 0.06 | Managed conversation flow effectively |
| 9 | Active Listening | Communication | 0.07 | Acknowledged, paraphrased, confirmed understanding |
| 10 | Closing Technique | Sales Technique | 0.08 | Asked for commitment, trial close |
| 11 | Compliance | Compliance | 0.06 | Mandatory disclosures, no false promises |
| 12 | Tone & Professionalism | Communication | 0.05 | Professional demeanor throughout |
| 13 | Rapport Building | Communication | 0.05 | Built connection and trust |
| 14 | Competitor Handling | Sales Technique | 0.03 | Addressed competitor mentions effectively |
| 15 | Documentation | Process | 0.03 | Captured key information during the call |

Total weight: 1.00. Weights should always sum to approximately 1.0 for meaningful scoring.

### How Scoring Works

1. Each parameter is scored from **0 to 10** by the LLM with a text justification.
2. The **overall score** (0-100) is calculated as a weighted average:
   ```
   overall_score = (sum of score_i * weight_i) / (sum of weight_i) * 10
   ```
3. Parameters with `is_active=false` are excluded from both LLM analysis and score calculation.

### Adding a Custom Parameter

```bash
curl -X POST http://localhost:8000/api/v1/quality-parameters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cross-Sell Opportunity",
    "description": "Agent identified and presented relevant cross-sell or upsell opportunities based on the customer needs discussed during the call",
    "weight": 0.05,
    "category": "Sales Technique",
    "display_order": 16
  }'
```

**Tips for writing parameter descriptions:**

- Be specific. The description is included in the LLM prompt.
- Describe what good performance looks like, not just the category name.
- Include examples where possible (e.g., "Agent mentioned at least 2 relevant add-on products").

### Updating a Parameter

```bash
# Reduce weight and update description
curl -X PUT http://localhost:8000/api/v1/quality-parameters/<parameter-id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 0.04,
    "description": "Updated description with more detail"
  }'
```

### Disabling a Parameter

```bash
# Soft-disable (parameter is preserved but excluded from future scoring)
curl -X PUT http://localhost:8000/api/v1/quality-parameters/<parameter-id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Rebalancing Weights

After adding or removing parameters, ensure weights still sum to approximately 1.0. While SalesLens normalizes weights during score calculation, keeping them balanced improves interpretability.

Example rebalancing for 16 parameters:

```bash
# List current parameters to see their IDs and weights
curl http://localhost:8000/api/v1/quality-parameters \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Intent Signals

Intent signals are binary indicators that the LLM checks for in each call. They drive the lead intent score and buying classification (Hot/Warm/Cold).

### Default Intent Signals

| Signal | Description |
|---|---|
| Budget Mentioned | Lead discussed or confirmed their budget |
| Budget Confirmed | Lead explicitly confirmed a specific budget range |
| Timeline Discussed | A specific timeframe for purchase was mentioned |
| Decision Maker Identified | The person on the call has buying authority |
| Competitor Comparison | Lead compared your offering to a competitor |
| Specific Requirements Stated | Lead articulated detailed requirements |
| Follow-up Requested by Lead | Lead proactively asked for a follow-up |
| Pricing Asked | Lead inquired about pricing details |
| Objections Raised | Lead raised concerns or objections |

### Adding a Custom Intent Signal

```bash
curl -X POST http://localhost:8000/api/v1/intent-signals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Regulatory Deadline",
    "description": "Lead mentioned a compliance or regulatory deadline driving the purchase timeline"
  }'
```

### Intent Classification Logic

The LLM classifies each call based on detected signals:

| Classification | Typical Criteria |
|---|---|
| **Hot** | 4+ positive signals, including budget + timeline + authority |
| **Warm** | 2-3 positive signals, or strong individual signals (budget confirmed, follow-up requested) |
| **Cold** | 0-1 positive signals, mostly informational call |

The intent score (0-100) is a weighted combination of signal detections plus LLM judgment.

---

## Persona Types

Persona types provide automatic buyer classification based on BANT (Budget, Authority, Need, Timeline) analysis. Each call receives BANT scores (0-10), and the LLM matches the profile against configured persona types.

### Default Persona Types

| Persona | Description | BANT Profile |
|---|---|---|
| Budget-Conscious Decision Maker | Has authority but is price-sensitive | B: 3-6, A: 7-10, N: 5-10, T: 1-5 |
| Ready Buyer | High scores across all BANT dimensions | B: 7-10, A: 7-10, N: 7-10, T: 7-10 |
| Researcher | Gathering information, no immediate intent | B: 0-3, A: 0-5, N: 3-7, T: 0-3 |
| Influencer | Strong need awareness but lacks buying authority | B: 0-5, A: 0-4, N: 7-10, T: 3-7 |
| Tire Kicker | Low engagement across all dimensions | B: 0-3, A: 0-3, N: 0-3, T: 0-3 |

### Adding a Custom Persona Type

```bash
curl -X POST http://localhost:8000/api/v1/persona-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Urgent Champion",
    "description": "Internal champion with strong need and tight timeline, but may lack final purchasing authority. Needs to be enabled to sell internally.",
    "bant_profile": {
      "budget": {"min": 4, "max": 8},
      "authority": {"min": 3, "max": 6},
      "need": {"min": 7, "max": 10},
      "timeline": {"min": 8, "max": 10}
    }
  }'
```

### BANT Score Interpretation

Each BANT dimension is scored 0-10:

| Score Range | Budget | Authority | Need | Timeline |
|---|---|---|---|---|
| 0-3 | No budget discussion | No decision power | No clear need | No timeline |
| 4-6 | Budget range mentioned | Some influence | Moderate need | Flexible timeline |
| 7-10 | Budget confirmed | Decision maker | Strong pain point | Urgent timeline |

---

## CRM Integration

SalesLens supports bidirectional CRM integration through webhooks.

### Inbound: Receiving Calls from CRM

Configure your CRM or dialer to send call recordings to SalesLens:

**Endpoint**: `POST /api/v1/calls/webhook`

**Headers**:
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

Or use an API key:
```
X-API-Key: slk_your-api-key
Content-Type: application/json
```

**Payload**:
```json
{
  "recording_url": "https://your-storage.com/recording.mp3",
  "agent_email": "agent@company.com",
  "lead_id": "SF-LEAD-001",
  "lead_name": "Customer Name",
  "lead_phone": "+1234567890",
  "source": "salesforce",
  "custom_fields": {
    "opportunity_id": "OPP-001",
    "deal_stage": "discovery"
  }
}
```

**Common CRM Setup:**

- **Salesforce**: Use a Flow or Apex trigger on the Task object to fire a webhook after a call activity is logged.
- **HubSpot**: Use a Workflow that triggers on call engagement creation.
- **Generic Dialers**: Most cloud dialers (Aircall, Dialpad, RingCentral) support post-call webhooks. Point them at the webhook endpoint.

### Outbound: Pushing Results to CRM

Configure an outbound integration to push analysis results back to your CRM:

```bash
curl -X POST http://localhost:8000/api/v1/integrations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salesforce - Update Lead Score",
    "type": "crm_webhook",
    "config": {
      "webhook_url": "https://hooks.salesforce.com/services/rest/...",
      "auth_header": "Bearer sf-access-token",
      "events": ["call.analyzed"],
      "field_mapping": {
        "overall_score": "Quality_Score__c",
        "intent_classification": "Lead_Intent__c",
        "intent_score": "Intent_Score__c",
        "follow_up_urgency": "Follow_Up_Priority__c"
      },
      "retry": {
        "max_attempts": 3,
        "backoff_seconds": 30
      }
    }
  }'
```

**Outbound Webhook Payload**:

When a call analysis completes, SalesLens sends:

```json
{
  "event": "call.analyzed",
  "call_id": "uuid",
  "lead_id": "SF-LEAD-001",
  "overall_score": 78.5,
  "intent_classification": "warm",
  "intent_score": 72.0,
  "follow_up_urgency": "this_week",
  "action_items": ["Send pricing proposal by Friday"],
  "persona_type": "Budget-Conscious Decision Maker",
  "extracted_metadata": {
    "has_competitor_quote": "Yes"
  },
  "timestamp": "2026-03-01T12:15:00Z"
}
```

**Field Mapping**: The `field_mapping` object in the integration config maps SalesLens output fields to your CRM's custom field API names.

---

## API Key Management

API keys provide a simple authentication mechanism for CRM and dialer integrations that cannot use JWT tokens.

### Creating an API Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Salesforce Integration"}'
```

Response:
```json
{
  "id": "uuid",
  "name": "Salesforce Integration",
  "key": "slk_a1b2c3d4e5f6g7h8i9j0...",
  "created_at": "2026-03-01T12:00:00Z"
}
```

**Important**: The `key` value is only returned once at creation time. Store it securely.

### Using an API Key

Include the key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/v1/calls/webhook \
  -H "X-API-Key: slk_a1b2c3d4e5f6g7h8i9j0..." \
  -H "Content-Type: application/json" \
  -d '{"recording_url": "https://...", "lead_name": "Customer"}'
```

### Listing and Revoking API Keys

```bash
# List all keys (key values are hidden)
curl http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN"

# Revoke a key
curl -X DELETE http://localhost:8000/api/v1/api-keys/<key-id> \
  -H "Authorization: Bearer $TOKEN"
```

---

## Multi-Tenant Setup

SalesLens is designed for multi-tenant operation. Each tenant has fully isolated data: users, calls, quality parameters, intent signals, persona types, and integrations.

### Creating Additional Tenants

```bash
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Second Organization",
    "tenant_slug": "second-org",
    "admin_email": "admin@secondorg.com",
    "admin_password": "secure-password",
    "admin_name": "Second Admin"
  }'
```

### Tenant Isolation

- All database queries are automatically filtered by `tenant_id`.
- Users can only access data within their own tenant.
- Quality parameters, intent signals, and persona types are tenant-specific.
- API keys are scoped to a single tenant.
- Uploaded recordings are stored in tenant-specific subdirectories.

### User Roles

| Role | Permissions |
|---|---|
| `admin` | Full access: manage users, configure parameters/signals/personas, manage integrations, view all data, QA overrides |
| `team_lead` | View all team data, analytics, QA overrides. Cannot manage tenant configuration. |
| `agent` | View own calls and performance. Cannot view other agents' data. |

---

## LLM Provider Configuration

### OpenAI (Default)

SalesLens uses OpenAI for call analysis. Set these in your `.env`:

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini     # Recommended for cost-effective bulk analysis
LLM_QA_MODEL=gpt-4o       # Higher accuracy for QA sampling
OPENAI_API_KEY=sk-...
```

### Model Selection

| Model | Cost | Speed | Quality | Recommended For |
|---|---|---|---|---|
| gpt-4o-mini | Low | Fast | Good | Primary analysis (bulk) |
| gpt-4o | Higher | Moderate | Excellent | QA audit sampling |

### Cost Estimation

Approximate costs per call analysis (based on a 10-minute call with ~3,000 word transcript):

| Model | Input Tokens | Output Tokens | Approximate Cost |
|---|---|---|---|
| gpt-4o-mini | ~4,000 | ~2,000 | ~$0.002 |
| gpt-4o | ~4,000 | ~2,000 | ~$0.03 |

At 100 calls/day using gpt-4o-mini: approximately $6/month for LLM analysis.

### Provider Abstraction

The codebase uses a provider abstraction pattern. To add a new LLM provider:

1. Create a new provider class in `backend/app/services/analysis/`.
2. Implement the analysis interface.
3. Register it in the provider factory.
4. Set `LLM_PROVIDER` to your new provider name.

---

## Transcription Provider Setup

### Deepgram Nova-3 (Recommended)

Deepgram provides fast, accurate transcription with built-in speaker diarization.

```bash
TRANSCRIPTION_PROVIDER=deepgram
DEEPGRAM_API_KEY=your-key-here
```

**Features**:
- Speaker diarization (agent vs. customer separation)
- Multi-language support (English, Hindi, Hinglish)
- Real-time streaming capable (not used in batch mode)
- Punctuation and formatting
- Word-level timestamps

**Cost**: Approximately $0.0043/minute (Pay-as-you-go tier).

### OpenAI Whisper (Fallback)

Whisper is used as a fallback when Deepgram is unavailable or for specific use cases.

```bash
TRANSCRIPTION_PROVIDER=whisper
OPENAI_API_KEY=your-key-here
```

**Features**:
- Good accuracy across many languages
- Simple API

**Limitations**:
- No built-in speaker diarization (post-processing required)
- 25 MB file size limit per API call (SalesLens handles chunking for larger files)

**Cost**: $0.006/minute.

### Provider Abstraction

To add a new transcription provider:

1. Create a new provider class in `backend/app/services/transcription/`.
2. Extend the `TranscriptionProvider` base class from `base.py`.
3. Implement the `transcribe()` method returning segments with speaker labels.
4. Register the provider in the factory (`factory.py`).
5. Set `TRANSCRIPTION_PROVIDER` to your new provider name.

---

## Email and Reports

### SMTP Configuration

To enable weekly report emails, configure SMTP in `.env`:

```bash
SMTP_HOST=smtp.gmail.com        # Or your SMTP provider
SMTP_PORT=587
SMTP_USER=reports@yourcompany.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
REPORT_FROM_EMAIL=reports@yourcompany.com
```

**For Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

**For Amazon SES**:
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=AKIA...
SMTP_PASSWORD=your-ses-smtp-password
```

### Weekly Reports

Generate reports via the API:

```bash
# Trigger report generation
curl -X POST http://localhost:8000/api/v1/reports/weekly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"week_start": "2026-02-24"}'
```

Reports include:
- Team-level summary (total calls, average quality score, hot leads)
- Week-over-week trend comparison
- Per-agent breakdown (calls, scores, strengths, areas for improvement)
- Highlights and lowlights

When SMTP is configured, reports are automatically emailed to team leads and admins.

---

## Storage Configuration

### Local Storage (Default)

By default, recordings are stored on the local filesystem:

```bash
UPLOAD_DIR=/app/uploads
```

In Docker, this is backed by the `upload_data` named volume for persistence.

### S3 Storage

For production deployments, store recordings in S3 or an S3-compatible service:

```bash
S3_BUCKET=saleslens-recordings
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

#### MinIO (Self-Hosted S3)

For on-premises deployments, use MinIO as an S3-compatible storage backend:

```bash
S3_BUCKET=saleslens-recordings
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://minio:9000
```

Add MinIO to your `docker-compose.override.yml`:

```yaml
services:
  minio:
    image: minio/minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  minio_data:
    driver: local
```

#### Cloudflare R2

```bash
S3_BUCKET=saleslens-recordings
S3_REGION=auto
AWS_ACCESS_KEY_ID=your-r2-access-key
AWS_SECRET_ACCESS_KEY=your-r2-secret-key
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
```

### Storage Sizing

Budget approximately:
- **10 MB per minute** for high-quality audio (WAV)
- **1 MB per minute** for compressed audio (MP3)
- A 10-minute call averages 1-10 MB depending on format

For 100 calls/day averaging 10 minutes each:
- Compressed: ~1 GB/day, ~30 GB/month
- Uncompressed: ~10 GB/day, ~300 GB/month
