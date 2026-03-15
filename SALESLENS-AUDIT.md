# SalesLens Audit — CIE Feasibility Analysis

**Date:** 2026-03-15
**Question:** Can SalesLens itself serve as the CIE (Conversation Intelligence Engine)?

---

## 1. Codebase Overview

| Dimension | Detail |
|-----------|--------|
| **Backend** | Python 3.12 / FastAPI, ~16K lines across 91 .py files |
| **Frontend** | React 19 + TypeScript + Vite, ~12.5K lines across 46 files |
| **DB** | PostgreSQL 16 + SQLAlchemy + Alembic migrations |
| **Task queue** | Celery + Redis |
| **Transcription** | Deepgram Nova-3 (primary), Whisper (fallback), provider abstraction |
| **LLM analysis** | OpenAI GPT-4o-mini, Jinja2 prompt templates, tenant-configurable |
| **Multi-tenant** | Full RLS at DB level, per-tenant config for everything |
| **Completion** | ~95% per FEATURES_CHECKLIST.md |

## 2. Core Extraction Pipeline (What Would Become CIE)

The pipeline lives in **3 modules:**

### a. Transcription Layer (`services/transcription/`)
- `base.py` — Abstract `TranscriptionProvider` + `TranscriptionResult` dataclass
- `factory.py` — Provider factory (Deepgram/Whisper)
- `deepgram_provider.py` / `whisper_provider.py` — Concrete providers
- **Verdict: ✅ ALREADY DOMAIN-AGNOSTIC.** Produces speaker-diarized segments with timestamps. Zero sales-specific logic.

### b. LLM Analysis Layer (`services/analysis/llm_analyzer.py`)
- `CallAnalyzer` class — renders Jinja2 prompt → calls OpenAI → parses structured JSON
- Provider abstraction via `settings.LLM_MODEL`
- Retry logic (tenacity), structured output parsing
- Tenant-specific prompt templates (DB-stored or file-based)
- **Verdict: ⚠️ PARTIALLY GENERIC.** The *mechanism* is domain-agnostic (render prompt → call LLM → parse JSON). But the *output schema* (`AnalysisResult`) is heavily sales-specific: quality scores, intent signals, BANT, rebuttals, sales audit keywords.

### c. Orchestration Layer (`tasks/call_processing.py`)
- Celery task: load call → transcribe → load tenant config → analyze → persist → webhook push
- **Verdict: ⚠️ SALES-COUPLED.** The orchestration itself is clean, but it couples to sales-specific models (QualityParameter, IntentSignal, PersonaType, ActionItem with sales urgency).

## 3. What's Sales-Specific vs Generic

### Generic (Reusable as-is):
- ✅ Audio ingestion (upload + webhook + URL download)
- ✅ Transcription service (provider abstraction, diarization)
- ✅ LLM call mechanism (template rendering, API call, JSON parsing, retry)
- ✅ Prompt template system (Jinja2, per-tenant, DB-stored, versioned)
- ✅ Multi-tenant isolation (RLS, per-tenant config)
- ✅ Storage abstraction (local + S3)
- ✅ JWT auth
- ✅ Webhook integration (inbound + outbound)
- ✅ Celery task infrastructure

### Sales-Specific (Would Need Abstraction for CIE):
- 🔴 `AnalysisResult` dataclass — 15+ sales-specific fields (quality scores, BANT, rebuttals, sales audit keywords, intent classification)
- 🔴 Call model — `overall_score`, `lead_intent_score`, `intent_classification`, `sales_audit_keywords`, `escalation_keywords`
- 🔴 Quality/Intent/Persona models — sales scoring framework baked into DB schema
- 🔴 Analytics service — agent performance, leaderboards, conversion funnels
- 🔴 Prompt template content — sales call analyst persona, scoring anchors
- 🔴 Frontend — entirely sales dashboard (gauges, BANT radar, leaderboard)

## 4. The Answer: Can SalesLens BE the CIE?

**Short answer: No — but it can BIRTH the CIE with minimal surgery.**

### Why Not Use As-Is:
SalesLens is a **complete sales product** — its models, schemas, prompts, and UI are all opinionated about sales. If PeakPerf calls `SalesLens/analyze`, it gets back BANT scores and sales rebuttals, not performance review extractions.

### Why It's 80% There:
The extraction *mechanism* is perfectly generic. The Jinja2 prompt system + structured JSON parsing + provider abstraction is exactly what CIE needs. The issue is only the **output schema** and **domain models** are sales-hardcoded.

## 5. Recommended Approach: Extract CIE FROM SalesLens

### Option A: Refactor SalesLens Into CIE + Sales Client (RECOMMENDED) ⭐
```
saleslens/
├── cie/                    ← Extract core engine as a package
│   ├── transcription/      ← Move as-is (already generic)
│   ├── extraction/         ← Generalize llm_analyzer
│   │   ├── engine.py       ← Generic: template → LLM → parse
│   │   └── profiles/       ← Domain configs (YAML)
│   │       ├── sales.yaml
│   │       └── performance.yaml
│   ├── prompts/            ← Template system (as-is)
│   ├── models/             ← Generic: Conversation, Extraction, Entity
│   └── api/                ← Headless API (/conversations, /extractions)
├── sales/                  ← SalesLens-specific domain logic
│   ├── models/             ← QualityParameter, IntentSignal, etc.
│   ├── services/           ← Sales scoring, analytics, reports
│   └── frontend/           ← Sales dashboard
```

**Effort:** ~2 weeks
**Risk:** Low — it's reorganization, not rewrite

### Option B: Fork SalesLens, Strip Sales Logic
Create a new repo, copy the generic parts, build new schemas.

**Effort:** ~2 weeks
**Risk:** Medium — code divergence, double maintenance

### Option C: Use SalesLens As-Is, Add PeakPerf Profile
Add a "performance" profile to the existing prompt + override the output schema.

**Effort:** ~1 week
**Risk:** HIGH — you end up with a Frankenstein. Sales and performance schemas collide. DB models don't fit. You fight the framework instead of building with it.

## 6. Surgery Map (Option A — Detailed)

### What Moves to CIE (generic):
| Current Location | CIE Location | Changes |
|-----------------|-------------|---------|
| `services/transcription/*` | `cie/transcription/*` | None — already generic |
| `services/analysis/llm_analyzer.py` | `cie/extraction/engine.py` | Replace `AnalysisResult` with generic `ExtractionResult` (profile-driven schema) |
| `prompts/__init__.py` + Jinja2 system | `cie/prompts/` | None — already generic |
| `models/call.py` (core fields only) | `cie/models/conversation.py` | Strip sales fields, keep: id, tenant, audio, transcript, status |
| `tasks/call_processing.py` | `cie/tasks/process.py` | Replace sales model writes with generic extraction writes |
| `config.py` (provider settings) | `cie/config.py` | Subset — transcription + LLM settings only |
| `db/rls.py`, `db/session.py` | `cie/db/` | As-is |

### What Stays in SalesLens (domain client):
- `models/quality.py`, `models/intent.py`, `models/persona.py`
- `models/lead.py`, `models/data_capture.py`
- `api/analytics.py`, `api/quality.py`, `api/intent.py`
- `services/analytics/`, `services/reports/`
- `prompts/call_analysis.jinja2` (becomes a sales profile template)
- Entire `frontend/`

### New for CIE:
- **Profile system:** YAML files defining extraction schema per domain
- **Generic models:** `Conversation`, `Extraction`, `ExtractedEntity`
- **Headless API:** `POST /conversations`, `GET /extractions/{id}`
- **Plugin registry:** Ingestors, extractors, enrichers, output handlers

## 7. Bottom Line

| Question | Answer |
|----------|--------|
| Is SalesLens good code? | **Yes** — clean architecture, proper abstractions, well-tested |
| Can it be CIE as-is? | **No** — output schema is sales-hardcoded |
| Can CIE be extracted from it? | **Yes, easily** — 80% of the engine is domain-agnostic |
| How long? | **~2 weeks** for clean extraction (Option A) |
| Does SalesLens break? | **No** — it becomes the first CIE client |
| Can PeakPerf then use CIE? | **Yes** — with a "performance" profile YAML |

**The CIE isn't a new build. It's SalesLens minus the opinions.**
