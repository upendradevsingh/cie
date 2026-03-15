# CIE — Conversation Intelligence Engine

## What This Is
A headless, profile-driven conversation extraction engine. Takes conversations (voice, text, chat) and extracts structured intelligence based on configurable YAML profiles.

**Forked from:** SalesLens (this repo started as a SalesLens clone)
**First client:** PeakPerf (performance management system, Java/Spring Boot)

## Architecture Reference
Read `CIE-DESIGN.md` for the full design. Read `SALESLENS-AUDIT.md` for what to keep vs strip.

## Tech Stack
- Python 3.12+ / FastAPI
- PostgreSQL with SQLAlchemy + Alembic
- Celery + Redis for async processing
- Deepgram/Whisper for transcription (keep SalesLens provider abstraction)
- OpenAI GPT-4o-mini for extraction (cost-optimized)

## What To Build

### Phase 1: Strip & Restructure
1. Remove ALL sales-specific code:
   - Delete: models/quality.py, models/intent.py, models/persona.py, models/lead.py, models/data_capture.py, models/action_item.py, models/report.py, models/integration.py, models/prompt_template.py
   - Delete: api/quality.py, api/intent.py, api/personas.py, api/leads.py, api/data_capture.py, api/reports.py, api/integrations.py, api/prompt_templates.py, api/analytics.py, api/users.py
   - Delete: services/analytics/, services/reports/, services/lead_aggregation.py, services/integration.py
   - Delete: tasks/report_generation.py
   - Delete: entire frontend/ directory
   - Delete: all tests (we'll write new ones)
   - Delete: prompts/call_analysis.jinja2
   - Keep: services/transcription/* (already generic), services/storage.py, services/auth.py (simplify to JWT validation only), db/* (keep RLS pattern), tasks/__init__.py (Celery setup)

### Phase 2: Build Generic Engine
1. **Models** (backend/app/models/):
   - conversation.py — ConversationStatus enum, Conversation model (see CIE-DESIGN.md section 4)
   - extraction.py — Extraction model with JSONB attributes
   - profile.py — Profile model for tenant overrides (optional, profiles primarily from YAML)
   - correction.py — Correction model for feedback loop

2. **Profile System** (backend/app/profiles/):
   - __init__.py — ProfileLoader class that reads YAML, merges tenant overrides
   - performance.yaml — Performance management profile (see CIE-DESIGN.md section 5)
   - sales.yaml — Sales profile (see CIE-DESIGN.md section 5)

3. **Extraction Engine** (backend/app/services/extraction/):
   - engine.py — ExtractionEngine class: reads profile → builds prompt → calls LLM → parses extractions
   - prompts.py — Dynamic prompt builder from profile config

4. **API** (backend/app/api/):
   - conversations.py — POST /api/v1/conversations, GET /api/v1/conversations/{id}
   - extractions.py — GET /api/v1/conversations/{id}/extractions, POST corrections
   - profiles.py — GET /api/v1/profiles, GET /api/v1/profiles/{id}
   - health.py — GET /health

5. **Schemas** (backend/app/schemas/):
   - conversation.py — Request/response schemas
   - extraction.py — Extraction response schemas
   - profile.py — Profile schemas

6. **Tasks** (backend/app/tasks/):
   - process_conversation.py — Celery task: ingest → transcribe (if audio) → extract → persist → callback

7. **Auth** (backend/app/services/auth.py):
   - Simplify to JWT validation ONLY (no user CRUD, no password hashing)
   - Validate signature, extract tenant_id and user_id from JWT
   - Use shared secret from config

8. **Config** (backend/app/config.py):
   - Strip SalesLens-specific settings
   - Add: PROFILES_DIR, JWT_SECRET (for validation)
   - Keep: DATABASE_URL, REDIS_URL, DEEPGRAM_API_KEY, OPENAI_API_KEY, LLM_MODEL

9. **Migrations** (backend/alembic/):
   - Fresh start: delete all SalesLens migrations
   - Create single initial migration with: conversations, extractions, corrections tables

10. **Docker** (docker-compose.yml):
    - Simplify: cie-api + cie-worker + postgres + redis
    - Update .env.example

### Phase 3: Test
1. Write tests for:
   - Profile loading (YAML parsing, merging)
   - Extraction engine (mock LLM calls, test parsing)
   - API endpoints (conversation submit, extraction retrieval)
   - JWT validation
2. Test with mock data locally

## Key Design Decisions
- Profiles are YAML files, NOT database tables. Tenant overrides stored in DB but base profiles are files.
- Extractions use JSONB `attributes` column for profile-specific data. No new tables for new extraction types.
- CIE does NOT manage users. It validates JWTs from the calling service.
- Transcription is optional — if input is text (segments provided), skip transcription.
- Use gpt-4o-mini as default (cost), with gpt-4o as fallback config option.

## Quality Bar
- Type hints everywhere
- Clean error handling with proper HTTP status codes
- Structured logging
- OpenAPI docs auto-generated
- All endpoints require JWT auth (except /health)
- Tenant isolation enforced at every query

## File Structure Target
```
cie/
├── CLAUDE.md
├── CIE-DESIGN.md
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── conversation.py
│   │   │   ├── extraction.py
│   │   │   └── correction.py
│   │   ├── schemas/
│   │   │   ├── conversation.py
│   │   │   ├── extraction.py
│   │   │   └── profile.py
│   │   ├── api/
│   │   │   ├── conversations.py
│   │   │   ├── extractions.py
│   │   │   ├── profiles.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── transcription/  (from SalesLens, as-is)
│   │   │   ├── extraction/
│   │   │   │   ├── engine.py
│   │   │   │   └── prompts.py
│   │   │   ├── storage.py (from SalesLens)
│   │   │   └── auth.py (simplified JWT validation)
│   │   ├── profiles/
│   │   │   ├── __init__.py
│   │   │   ├── performance.yaml
│   │   │   └── sales.yaml
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── process_conversation.py
│   │   └── db/
│   │       ├── session.py
│   │       └── tenant.py
│   ├── alembic/
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
```
