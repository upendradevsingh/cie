# SalesLens

**AI lens into every sales conversation**

SalesLens is a self-hosted, AI-powered sales call intelligence platform. Upload call recordings, get automatic transcription with speaker diarization, and receive detailed analysis including quality scores, lead intelligence, persona identification, and actionable next steps -- all through a modern dashboard.

---

## Features

- **Call Ingestion** -- Upload recordings (MP3, WAV, M4A, WebM) via REST API or receive them through CRM/dialer webhooks with full metadata support.
- **AI Transcription** -- Automatic speech-to-text with speaker diarization (agent vs. customer) powered by Deepgram Nova-3 or OpenAI Whisper, with multi-language support (English, Hindi, Hinglish).
- **Quality Scoring** -- Configurable scoring parameters (15+ defaults) covering greeting, need discovery, objection handling, closing technique, compliance, and more. Each parameter scored 0-10 with justification, rolled up to a weighted 0-100 overall score.
- **Lead Intelligence** -- Intent scoring (0-100), buying classification (Hot/Warm/Cold), configurable intent signals, key objection extraction, and BANT analysis.
- **Persona Identification** -- Automatic BANT-based persona classification with admin-configurable persona types and discovery insights.
- **Action Items** -- Extracted next steps, AI-generated path-to-conversion talking points, objection-specific rebuttals, and follow-up urgency rating.
- **Team Analytics** -- Agent performance comparison, quality score trends, conversion funnels, and leaderboards.
- **Weekly Reports** -- Automated per-agent summary reports delivered via email or viewed in-app.
- **CRM Integration** -- Inbound webhooks for any CRM/dialer, outbound webhook sync to push analysis results back.
- **Multi-Tenant** -- Full tenant isolation with role-based access (admin, team lead, agent).
- **One-Command Deployment** -- Docker Compose setup with PostgreSQL, Redis, Celery workers, and the React frontend.

---

## Architecture

```
                           SalesLens Architecture
 ============================================================================

  Call Sources                    Processing Pipeline
 +----------------+     +--------------------------------------------+
 | Upload API     |---->|                                            |
 | (mp3/wav/m4a)  |     |   Celery Worker                           |
 +----------------+     |   +----------+    +-------------------+   |
                        |   |Transcribe|--->| LLM Analysis      |   |
 +----------------+     |   |Deepgram/ |    | (GPT-4o-mini)     |   |
 | CRM Webhook    |---->|   |Whisper   |    |                   |   |
 | (recording URL)|     |   +----------+    | - Quality scores  |   |
 +----------------+     |                   | - Lead intel      |   |
                        |                   | - Persona/BANT    |   |
                        |                   | - Action items    |   |
                        |                   +-------------------+   |
                        +--------------------------------------------+
                                        |
                                        v
                              +-----------------+
                              |   PostgreSQL    |
                              |   (all data)    |
                              +-----------------+
                                        |
                        +---------------+---------------+
                        |                               |
                        v                               v
              +------------------+            +------------------+
              | FastAPI Backend  |            | React Frontend   |
              | REST API (:8000) |<---------->| Dashboard (:3000)|
              +------------------+            +------------------+
                        |
                        v
              +------------------+
              | CRM Sync         |
              | (outbound hooks) |
              +------------------+
```

---

## Quick Start

Get SalesLens running in under 5 minutes.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- A [Deepgram API key](https://console.deepgram.com) (for transcription)
- An [OpenAI API key](https://platform.openai.com/api-keys) (for LLM analysis)

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/your-org/saleslens.git
cd saleslens
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Open `.env` in your editor and set at minimum:

| Variable | What to change |
|---|---|
| `SECRET_KEY` | A random string of 32+ characters |
| `DEEPGRAM_API_KEY` | Your Deepgram API key |
| `OPENAI_API_KEY` | Your OpenAI API key |

**3. Start all services**

```bash
docker-compose up -d
```

This launches PostgreSQL, Redis, the FastAPI backend, a Celery worker, and the React frontend.

**4. Verify everything is running**

```bash
# Check service health
docker-compose ps

# Test the API
curl http://localhost:8000/health
```

**5. Access SalesLens**

| Service | URL |
|---|---|
| Frontend Dashboard | [http://localhost:3000](http://localhost:3000) |
| Backend API | [http://localhost:8000](http://localhost:8000) |
| API Documentation (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| API Documentation (ReDoc) | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

**6. Create your first tenant and admin user**

```bash
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "your-secure-password",
    "admin_name": "Admin User"
  }'
```

Save the `access_token` from the response to authenticate subsequent requests.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+ / FastAPI |
| Database | PostgreSQL 16 |
| Task Queue | Celery + Redis 7 |
| Transcription | Deepgram Nova-3 (primary), OpenAI Whisper (fallback) |
| LLM Analysis | OpenAI GPT-4o-mini (primary), GPT-4o (QA sample) |
| Frontend | React 19 + TypeScript + Vite + TailwindCSS + shadcn/ui |
| Auth | JWT-based, multi-tenant |
| Deployment | Docker + Docker Compose |

---

## Project Structure

```
saleslens/
├── README.md
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Settings from environment variables
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # Route handlers (controllers)
│   │   ├── services/            # Business logic layer
│   │   │   ├── transcription/   # Provider abstraction (Deepgram, Whisper)
│   │   │   ├── analysis/        # LLM analysis pipeline
│   │   │   └── reports/         # Weekly report generation
│   │   ├── tasks/               # Celery async tasks
│   │   ├── db/                  # Database session and setup
│   │   └── prompts/             # LLM prompt templates (Jinja2)
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components (shadcn/ui)
│   │   ├── pages/               # Page-level components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── lib/                 # API client, utilities
│   │   ├── types/               # TypeScript type definitions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
└── docs/
    ├── API.md                   # Full API reference
    ├── DEPLOYMENT.md            # Production deployment guide
    └── CONFIGURATION.md         # Configuration and setup guide
```

---

## API Documentation

The FastAPI backend auto-generates interactive API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

For the full API reference with examples and curl commands, see [docs/API.md](docs/API.md).

---

## Configuration

SalesLens is configured entirely through environment variables. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed documentation on:

- Quality scoring parameters
- Intent signal configuration
- Persona type setup
- CRM integration (inbound/outbound webhooks)
- Transcription and LLM provider setup
- Multi-tenant configuration
- Email/SMTP setup for weekly reports

---

## Deployment

For production deployment guidance including SSL/TLS, security hardening, database backups, and scaling, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Screenshots

> Screenshots will be added after the initial UI is complete.

| Dashboard | Call Detail |
|---|---|
| *Overview with KPI cards, trend charts, and team performance* | *Full transcript with speaker labels, quality breakdown, lead intelligence* |

| Analytics | Leaderboard |
|---|---|
| *Agent comparison, quality trends, conversion funnels* | *Agent rankings by quality score and improvement rate* |

---

## Development

### Backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
uvicorn app.main:app --reload --port 8000
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts at `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

### Running Celery Worker (without Docker)

```bash
cd backend
celery -A app.tasks worker --loglevel=info --concurrency=4
```

### Database Migrations

```bash
cd backend

# Create a new migration
alembic revision --autogenerate -m "describe your changes"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository and create a feature branch from `main`.
2. Write clear, descriptive commit messages.
3. Add type hints to all Python functions.
4. Use TypeScript strict mode for frontend code.
5. Include proper error handling.
6. Test your changes before submitting a pull request.
7. Update documentation if you change any API endpoints or configuration.

### Code Style

- **Python**: Follow PEP 8. Use `ruff` for linting and formatting.
- **TypeScript**: Follow the ESLint configuration in the project.
- **Commits**: Use conventional commit messages (e.g., `feat:`, `fix:`, `docs:`).

---

## License

This project is licensed under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2024 SalesLens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
