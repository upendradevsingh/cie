# SalesLens — AI-Powered Sales Call Intelligence Platform

## What You're Building
A complete, production-ready sales call analysis platform. Think "Zipteams but open-source and self-hosted."

## Product Name: SalesLens
Tagline: "AI lens into every sales conversation"

## Architecture

```
Call Recording (upload/webhook) → Transcription (Deepgram/Whisper) → LLM Analysis → Storage → Dashboards + CRM Sync
```

## Tech Stack
- **Backend:** Python 3.12+ / FastAPI
- **Database:** PostgreSQL with SQLAlchemy/Alembic migrations
- **Task Queue:** Celery + Redis (for async call processing)
- **Transcription:** Deepgram Nova-3 (primary), OpenAI Whisper API (fallback), with provider abstraction
- **LLM Analysis:** OpenAI GPT-4o-mini (primary), GPT-4o (QA sample), with provider abstraction
- **Frontend:** React 19 + TypeScript + Vite + TailwindCSS + shadcn/ui
- **Auth:** JWT-based, multi-tenant
- **Containerization:** Docker + docker-compose for one-command deployment

## Core Features to Build

### 1. Call Ingestion
- REST API to upload call recordings (mp3, wav, m4a, webm)
- Webhook endpoint for CRM/dialer integration (receive recording URL + metadata)
- Metadata: lead_id, agent_name, agent_id, lead_name, lead_phone, source, custom fields (up to 5)
- Background processing via Celery task queue

### 2. Transcription Service
- Provider abstraction (Deepgram, Whisper, easy to add more)
- Speaker diarization (agent vs customer)
- Multi-language support (English, Hindi, Hinglish)
- Store raw transcript + speaker-labeled segments

### 3. LLM Analysis Pipeline
Single structured prompt per call that extracts ALL of the following in one shot:

**a. Call Quality Score**
- Configurable parameters (admin can CRUD scoring parameters)
- Each parameter: name, description, weight (0-1), category
- Default parameters (ship with 15-20 sensible defaults):
  - Opening & Greeting (proper introduction, energy)
  - Need Discovery (asked probing questions, understood requirements)
  - Product Knowledge (accurate info, handled features well)
  - Objection Handling (addressed concerns, provided rebuttals)
  - Pricing Discussion (transparent, value-framed)
  - Urgency Creation (time-sensitive offers, scarcity)
  - Next Steps (clear action items, follow-up scheduled)
  - Call Control (managed conversation flow)
  - Active Listening (acknowledged, paraphrased)
  - Closing Technique (asked for commitment)
  - Compliance (mandatory disclosures, no false promises)
  - Tone & Professionalism
  - Rapport Building
  - Competitor Handling
  - Documentation (captured key info during call)
- Score per parameter (0-10) with justification text
- Overall weighted score (0-100)

**b. Lead Intelligence**
- Lead intent score (0-100) with breakdown
- Configurable intent signals (admin can CRUD):
  - Budget mentioned/confirmed
  - Timeline discussed
  - Decision maker identified
  - Competitor comparison
  - Specific requirements stated
  - Follow-up requested by lead
  - Pricing asked
  - Objections raised (and type)
- Buying intent classification: Hot / Warm / Cold
- Key objections extracted (list with category)

**c. Persona Identification**
- BANT analysis (Budget, Authority, Need, Timeline) — each scored
- Auto-persona classification based on BANT profile
- Custom persona types (admin configurable)
- Discovery insights (what was learned about the customer)

**d. Action Items & Next Steps**
- Extracted next steps from conversation (list)
- AI-generated "path to conversion" — suggested talking points for follow-up
- Objection-specific rebuttals for next call
- Follow-up urgency rating (immediate / this week / next week / nurture)

**e. Call Metadata Extraction**
- Key data points captured from conversation (configurable, up to 10 fields)
- Example: "Has quote from competitor: Yes, Company X at ₹Y"
- Structured JSON output for CRM sync

### 4. Database Schema (PostgreSQL)
Design a clean, normalized schema:
- `tenants` (multi-tenant support)
- `users` (with roles: admin, team_lead, agent)
- `calls` (recording_url, duration, transcript, analysis JSON, scores, status)
- `quality_parameters` (tenant-configurable scoring params)
- `intent_signals` (tenant-configurable intent signals)
- `persona_types` (tenant-configurable personas)
- `lead_scores` (per-call lead intelligence)
- `action_items` (extracted next steps per call)
- `weekly_reports` (generated report snapshots)
- `integrations` (CRM config per tenant)
- `api_keys` (for webhook auth)

### 5. REST API (FastAPI)
Full CRUD API with OpenAPI docs:
- `POST /api/v1/calls/upload` — upload recording
- `POST /api/v1/calls/webhook` — receive from CRM/dialer
- `GET /api/v1/calls` — list calls (filters: agent, date range, score range, intent)
- `GET /api/v1/calls/{id}` — full call detail (transcript, analysis, scores)
- `GET /api/v1/calls/{id}/transcript` — transcript with speaker labels
- `PUT /api/v1/calls/{id}/qa-override` — manual QA correction of scores
- `GET /api/v1/analytics/team` — team-level aggregates
- `GET /api/v1/analytics/agent/{id}` — per-agent performance
- `GET /api/v1/analytics/trends` — score trends over time
- CRUD for quality_parameters, intent_signals, persona_types
- `POST /api/v1/reports/weekly` — trigger weekly report generation
- `GET /api/v1/reports/weekly/{id}` — get generated report
- Admin endpoints for tenant config, user management, integrations

### 6. Frontend Dashboard
Modern, clean UI (think Linear/Vercel aesthetic — dark mode default):

**Pages:**
- **Dashboard** — overview cards (calls today, avg quality score, hot leads count, team performance), trend charts
- **Calls List** — searchable/filterable table, quick-view scores, click to expand
- **Call Detail** — full transcript (speaker-labeled, timestamped), quality scores breakdown, lead intelligence, action items, persona analysis. Transcript should highlight key moments.
- **Analytics** — team performance charts, agent comparison, quality trends, conversion funnel
- **Leaderboard** — agent ranking by quality score, conversion, improvement rate
- **Settings** — quality parameters CRUD, intent signals CRUD, persona types CRUD, integration config
- **Reports** — weekly report viewer, per-agent breakdowns

**UI Components:**
- Score gauges (circular, color-coded: red/yellow/green)
- Transcript viewer with speaker colors and timestamp navigation
- Parameter breakdown as horizontal bar charts
- Lead intent as a funnel visualization
- BANT radar chart for persona view

### 7. Integrations
- **Inbound webhook** — generic format for any CRM/dialer
- **Outbound CRM sync** — push analysis results back via configurable webhook
- **Weekly email reports** — per-agent summary emails (use templates)

### 8. Docker Deployment
- `docker-compose.yml` with: app, worker (Celery), PostgreSQL, Redis
- `.env.example` with all config vars
- Health check endpoints
- One-command startup: `docker-compose up`

## File Structure
```
saleslens/
├── README.md (product overview, setup guide, screenshots section)
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI app)
│   │   ├── config.py (settings from env)
│   │   ├── models/ (SQLAlchemy models)
│   │   ├── schemas/ (Pydantic schemas)
│   │   ├── api/ (route handlers)
│   │   ├── services/ (business logic)
│   │   │   ├── transcription/ (provider abstraction)
│   │   │   ├── analysis/ (LLM pipeline)
│   │   │   └── reports/ (weekly report generation)
│   │   ├── tasks/ (Celery tasks)
│   │   ├── db/ (database setup, migrations)
│   │   └── prompts/ (LLM prompt templates as .txt or .jinja2)
│   ├── alembic/ (migrations)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/ (API client)
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
└── docs/
    ├── API.md
    ├── DEPLOYMENT.md
    └── CONFIGURATION.md
```

## Quality Bar
- Clean, well-structured code — no shortcuts
- Proper error handling everywhere
- Type hints on all Python functions
- TypeScript strict mode on frontend
- Comprehensive .env.example with comments
- README that a developer can follow to get running in 5 minutes
- LLM prompts should be carefully crafted for consistent structured JSON output
- All API endpoints documented in OpenAPI

## What NOT to Build (keep scope tight)
- No real-time call analysis (batch only, T+minutes is fine)
- No mobile app
- No SSO/OAuth (simple JWT auth is enough)
- No billing/subscription management
- No Kubernetes configs (docker-compose only)

## Brand
- Product: SalesLens
- Tagline: "AI lens into every sales conversation"
- Color palette: Deep blue (#1e3a5f) primary, teal (#0d9488) accent, dark slate bg
- Logo: just use text "SalesLens" with a lens icon (◎) in the frontend

Build everything. Ship it complete. Make it impressive.
