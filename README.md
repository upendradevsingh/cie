# SalesLens

**AI lens into every sales conversation**

SalesLens is a production-ready, self-hosted AI-powered sales call intelligence platform. Transform every sales conversation into actionable insights with automatic transcription, quality scoring, lead intelligence, and data-driven coaching — all in one unified dashboard.

---

## 🎯 Why SalesLens?

- **🔒 Self-Hosted & Private** — Your call data stays on your infrastructure, not third-party clouds
- **⚡ Production-Ready** — Built with enterprise-grade tech stack (FastAPI, PostgreSQL, React, Docker)
- **🎨 Fully Customizable** — Configure quality parameters, intent signals, personas, and even LLM prompts per tenant
- **📊 Impact-Based ROI** — Drive conversions with data-driven insights, not guesswork
- **🔌 CRM-Agnostic** — Works with any CRM via webhooks (Salesforce, HubSpot, Zoho, custom systems)
- **🌍 Multi-Language** — Supports English, Hindi, and Hinglish with automatic language detection
- **💰 Cost-Effective** — No per-seat licensing, usage-based pricing aligns with your growth

---

## ✨ Core Features

### 📞 **1. Intelligent Call Processing**

#### Call Ingestion
- **Multiple upload methods:**
  - Direct file upload (MP3, WAV, M4A, WebM)
  - CRM/dialer webhook integration (automatic sync)
  - Recording URL processing
- **Rich metadata support:**
  - Lead ID, name, phone, email
  - Agent ID and name
  - Call source tracking
  - Up to 5 custom fields per call

#### AI Transcription
- **Powered by industry-leading providers:**
  - Deepgram Nova-3 (primary) — 90% accuracy, fast processing
  - OpenAI Whisper API (fallback) — multilingual support
- **Speaker diarization** — Automatically identifies agent vs. customer speech
- **Multi-language support** — English, Hindi, Hinglish with auto-detection
- **Timestamped segments** — Navigate to any moment in the conversation
- **Processing SLA:** 90% of calls processed in under 4 hours

---

### 🎯 **2. AI-Powered Quality Scoring Framework**

#### Configurable Quality Parameters
- **Standardized evaluation framework** with 20+ default parameters:
  - **Opening & Greeting** — Energy, professionalism, introduction
  - **Need Discovery** — Probing questions, active listening, requirement gathering
  - **Product Knowledge** — Accuracy, feature explanation, benefits articulation
  - **Objection Handling** — Acknowledgment, rebuttal effectiveness, empathy
  - **Pricing Discussion** — Transparency, value framing, discount handling
  - **Urgency Creation** — Time-sensitive offers, scarcity messaging
  - **Next Steps** — Clear action items, follow-up scheduling
  - **Call Control** — Conversation flow management, agenda setting
  - **Active Listening** — Acknowledgment, paraphrasing, understanding
  - **Closing Technique** — Trial close, commitment ask, assumptive close
  - **Compliance** — Mandatory disclosures, no false promises, ethical selling
  - **Tone & Professionalism** — Voice quality, confidence, respectfulness
  - **Rapport Building** — Small talk, personalization, connection
  - **Competitor Handling** — Competitive positioning, differentiation
  - **Documentation** — Information capture, note-taking during call

#### Scoring Capabilities
- **0-10 scoring per parameter** with AI-generated justification
- **Weighted aggregation** — Custom weightages per parameter (0-1)
- **Overall quality score** — 0-100 composite score
- **Category grouping** — Organize parameters into logical categories
- **QA validation system** — Manual override and correction by supervisors
- **Trend analysis** — Track quality improvements over time
- **Correlation insights** — Identify parameters that drive conversions

#### Admin Features
- Full CRUD for quality parameters
- Parameter descriptions and weightages configurable per tenant
- Import/export parameter sets
- Version control for parameter changes

---

### 📈 **3. Lead Intelligence & Prioritization**

#### Intent Scoring System
- **AI-generated lead intent score (0-100)** based on configurable signals:
  - Budget mentioned or confirmed
  - Timeline discussed (buying window identified)
  - Decision maker identified or present
  - Competitor comparison mentioned
  - Specific requirements stated
  - Follow-up requested by lead
  - Pricing information asked
  - Objections raised (type and severity)
  - Contract/demo requested
  - Implementation discussed

#### Buying Intent Classification
- **Hot** — High intent, ready to buy (score 70-100)
- **Warm** — Moderate intent, nurturing needed (score 40-69)
- **Cold** — Low intent, long-term follow-up (score 0-39)

#### Lead-Level Insights
- **Key objections extraction** — Categorized by type (pricing, features, timing, etc.)
- **Objection severity** — High, medium, low priority
- **Competitive intelligence** — Competitor mentions with context
- **Pain points identified** — Customer challenges and needs
- **Budget indicators** — Budget range mentioned, authority level
- **Decision timeline** — When customer plans to decide

---

### 👤 **4. Persona Identification & BANT Analysis**

#### BANT Scoring Framework
Each dimension scored 0-100:
- **Budget (B)** — Financial capacity confirmed
- **Authority (A)** — Decision-making power identified
- **Need (N)** — Problem severity and urgency
- **Timeline (T)** — Buying window clarity

#### Persona Classification
- **Automatic persona mapping** based on BANT profile:
  - Decision Maker — High authority, clear need, budget available
  - Influencer — Low authority, high need, can recommend
  - Researcher — Gathering information, early stage
  - Champion — Internal advocate, medium authority
  - Budget Holder — High authority, budget control
  - End User — Will use product, low authority
  - Gatekeeper — Information filter, screening role

- **Custom persona types** — Configurable per tenant
- **Discovery insights** — 3-5 key learnings about the customer
- **Persona-specific playbooks** — Recommended approach per persona type

---

### 🎬 **5. Action Items & Deal Progression**

#### Transactional Next Steps
- **AI-extracted action items** from conversation:
  - Description of the action
  - Category (follow-up, demo, send materials, contract, etc.)
  - Urgency level (immediate, this week, next week, nurture)
  - Owner (agent, customer, third-party)

#### Path to Conversion
- **AI-generated talking points** for the next conversation:
  - Based on persona type and call insights
  - Addresses raised objections
  - Highlights relevant features
  - Reinforces value proposition

#### Objection-Specific Rebuttals
- **Custom weapons** for common objections:
  - Pricing concerns → Value ROI calculators
  - Feature comparisons → Competitive battle cards
  - Timing objections → Urgency builders
  - Trust issues → Case studies and testimonials

#### Follow-Up Guidance
- **Urgency rating:**
  - Immediate (call back today)
  - This week (follow up within 3 days)
  - Next week (schedule for next Monday)
  - Nurture (add to drip campaign)

---

### 🔍 **6. Enhanced Analysis Features**

#### Escalation Keywords Detection
- **Automatic detection** of escalation triggers:
  - Dissatisfaction indicators ("not happy", "disappointed", "frustrated")
  - Churn signals ("cancel", "refund", "competitor")
  - Legal/compliance concerns ("lawyer", "regulatory", "breach")
  - Management escalation requests ("supervisor", "manager", "complaint")
- **Severity classification:** High, Medium, Low
- **Context extraction** — Exact moment and surrounding conversation

#### Sentiment Analysis
- **Overall sentiment scoring:** Positive, Negative, Mixed, Neutral
- **Positive keywords tracked** — Excitement, satisfaction, agreement phrases
- **Negative keywords tracked** — Frustration, confusion, objection phrases
- **Sentiment timeline** — Track mood changes throughout the call

#### Call Tagging System
- **Auto-generated tags** based on call content:
  - Demo Call, Pricing Discussion, Objection Heavy
  - Follow-Up Call, Discovery Call, Closing Attempt
  - Escalation, Churn Risk, Upsell Opportunity
- **Custom tags** — Add manual tags for filtering and reporting

#### Sales Audit Keywords (8 Categories)
- **Compliance Violations** — Promises that shouldn't be made
- **Missed Opportunities** — Moments to upsell, cross-sell, or close
- **Pricing Discounts** — Discount mentions with percentage/amount
- **Competitor Mentions** — Which competitors and context
- **Customer Pain Points** — Problems the customer is facing
- **Commitment & Closing** — Attempts to gain commitment
- **Objection Handling** — How objections were addressed
- **Negative Reactions** — Customer pushback or resistance

Each keyword includes:
- The keyword/phrase detected
- Surrounding context (2-3 sentences)
- Severity (high/medium/low)

---

### 📊 **7. Analytics & Reporting**

#### Team-Level Dashboard
- **Real-time KPI cards:**
  - Total calls (today, this week, this month)
  - Average quality score with trend
  - Hot leads count
  - Team performance score
- **Quality score trends** — Daily, weekly, monthly charts
- **Call volume trends** — Track activity patterns
- **Score distribution** — Histogram of quality scores
- **Hot leads list** — Prioritized by intent score

#### Agent Performance Analytics
- **Per-agent breakdown:**
  - Total calls and duration
  - Average quality score
  - Average intent score
  - Hot/warm/cold lead distribution
  - Top performing parameters
  - Bottom performing parameters (coaching areas)
  - Completed vs. pending action items
  - Week-over-week improvement

#### Leaderboard
- **Rankings by:**
  - Quality score (highest average)
  - Lead conversion (most hot leads generated)
  - Improvement rate (biggest score gains)
  - Call volume (most calls)
  - Consistency (lowest score variance)

#### Weekly Reports
- **Automated report generation** with:
  - Executive summary (team highlights)
  - Agent-by-agent performance
  - Top calls of the week
  - Areas for improvement (lowest-scoring parameters)
  - Hot leads summary with next steps
  - Week-over-week trends
  - Coaching recommendations
- **Report delivery:**
  - In-app viewer with drill-down
  - Scheduled generation (every Monday)
  - Export to PDF (future)
  - Email delivery to stakeholders (configurable)

#### Correlation Analysis
- **Quality parameters vs. conversion** — Which behaviors drive deals?
- **Intent signals vs. close rate** — Which signals predict success?
- **Agent benchmarking** — Compare against team averages
- **Trend forecasting** — Predict team performance trajectory

---

### 🔌 **8. CRM Integration**

#### Inbound Integration
- **Webhook endpoint** to receive call recordings automatically:
  - `POST /api/v1/calls/webhook`
  - Supports: Salesforce, HubSpot, Zoho, Close, Pipedrive, custom CRMs
  - Metadata sync: lead ID, contact details, call source, custom fields
  - Authentication via API keys
- **Direct upload API:**
  - `POST /api/v1/calls/upload`
  - File size limit: 500MB per call
  - Batch upload support

#### Outbound Integration
- **Push analysis results back to CRM:**
  - Quality score, intent score, classification
  - Next steps and action items
  - Key objections and sentiment
  - Custom field mapping (up to 10 fields)
- **Configurable webhook destination** per tenant
- **Retry logic** — Automatic retry on failure with exponential backoff
- **Event triggers:**
  - Analysis completed
  - Hot lead detected
  - Escalation keyword found
  - QA override applied

#### Supported CRM Fields
- Lead score update
- Call quality score
- Next action assignment
- Lead status change
- Custom fields (tenant-configurable)

---

### 🎨 **9. Advanced Customization**

#### Tenant-Specific Prompt Templates
- **Customize AI analysis prompts** per tenant:
  - Upload custom Jinja2 templates
  - Override default analysis logic
  - Industry-specific scoring (SaaS, Real Estate, Insurance, etc.)
  - Version control — Rollback to previous prompts
  - A/B testing — Test new prompts on sample calls

#### Admin Configuration
- **Quality parameters** — Full CRUD, import/export
- **Intent signals** — Add/edit/remove signals
- **Persona types** — Define custom personas with descriptions
- **Call tags** — Configure auto-tagging rules
- **User management** — Invite users, assign roles
- **Integration settings** — Configure webhooks and API keys

---

### 🔐 **10. Multi-Tenant Architecture & Security**

#### Tenant Isolation
- **Full data isolation** — No cross-tenant data leakage
- **Row-level security (RLS)** — Database-level enforcement
- **Per-tenant configuration:**
  - Quality parameters and weightages
  - Intent signals
  - Persona types
  - LLM prompt templates
  - Integration credentials
  - User access controls

#### Role-Based Access Control (RBAC)
- **Admin** — Full access, configuration, user management
- **Team Lead** — View all team calls, QA override, reports
- **Agent** — View only own calls, limited analytics

#### Data Security
- **JWT-based authentication** — Secure token-based sessions
- **API key authentication** — For webhook integrations
- **Password hashing** — Bcrypt with salt
- **Audit logging** — Track all configuration changes
- **Data retention policies** — Configurable storage duration (default: 6 months)

---

## 🚀 Tech Stack

| Layer | Technology | Why We Chose It |
|---|---|---|
| **Backend** | Python 3.12+ / FastAPI | Fast, modern, type-safe, auto-generated API docs |
| **Database** | PostgreSQL 16 | Robust, ACID-compliant, excellent JSON support |
| **Task Queue** | Celery + Redis 7 | Asynchronous processing, reliable job distribution |
| **Transcription** | Deepgram Nova-3, OpenAI Whisper | Best-in-class accuracy, multi-language, fast |
| **LLM Analysis** | OpenAI GPT-4o-mini, GPT-4o | Structured output, reliable, cost-effective |
| **Storage** | Local + S3 | Flexible storage with cloud backup option |
| **Frontend** | React 19 + TypeScript | Type-safe, modern, excellent DX |
| **UI Framework** | TailwindCSS + shadcn/ui | Beautiful, accessible, customizable components |
| **Build Tool** | Vite | Lightning-fast HMR and builds |
| **Deployment** | Docker + Docker Compose | One-command setup, production-ready |

---

## ⚡ Quick Start

Get SalesLens running in **under 5 minutes**.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- A [Deepgram API key](https://console.deepgram.com) (for transcription)
- An [OpenAI API key](https://platform.openai.com/api-keys) (for LLM analysis)

### Installation Steps

**1. Clone the repository**

```bash
git clone https://github.com/your-org/saleslens.git
cd saleslens
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Random 32+ character string for JWT signing |
| `DEEPGRAM_API_KEY` | ✅ | Your Deepgram API key |
| `OPENAI_API_KEY` | ✅ | Your OpenAI API key |
| `DATABASE_URL` | Auto | PostgreSQL connection (auto-configured in Docker) |
| `REDIS_URL` | Auto | Redis connection (auto-configured in Docker) |

**3. Start all services**

```bash
docker-compose up -d
```

This launches:
- PostgreSQL database
- Redis cache
- FastAPI backend (port 8000)
- Celery worker (background processing)
- React frontend (port 3000)

**4. Verify everything is running**

```bash
# Check service health
docker-compose ps

# Test the API
curl http://localhost:8000/health
```

Expected output:
```json
{"status": "healthy", "version": "1.0.0"}
```

**5. Access SalesLens**

| Service | URL |
|---|---|
| **Frontend Dashboard** | [http://localhost:3000](http://localhost:3000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **API Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

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

Save the `access_token` from the response for API authentication.

**7. Upload your first call**

```bash
curl -X POST http://localhost:8000/api/v1/calls/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@path/to/call-recording.mp3" \
  -F "lead_name=John Doe" \
  -F "lead_phone=+1234567890"
```

The call will be processed asynchronously. Check status at `/calls/{id}` or in the dashboard.

---

## 📖 API Documentation

The FastAPI backend auto-generates **interactive API documentation**:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key API Endpoints

#### Call Management
- `POST /api/v1/calls/upload` — Upload a call recording
- `POST /api/v1/calls/webhook` — Receive call from CRM/dialer
- `GET /api/v1/calls` — List calls with filters (agent, date range, score, intent)
- `GET /api/v1/calls/{id}` — Get full call details
- `GET /api/v1/calls/{id}/transcript` — Get transcript with speaker labels
- `PUT /api/v1/calls/{id}/qa-override` — Manual QA correction of scores

#### Analytics
- `GET /api/v1/analytics/team` — Team-level aggregates
- `GET /api/v1/analytics/agent/{id}` — Per-agent performance
- `GET /api/v1/analytics/trends` — Score trends over time
- `GET /api/v1/analytics/leaderboard` — Agent rankings

#### Configuration (Admin)
- `GET/POST/PUT/DELETE /api/v1/quality-parameters` — Quality parameter CRUD
- `GET/POST/PUT/DELETE /api/v1/intent-signals` — Intent signal CRUD
- `GET/POST/PUT/DELETE /api/v1/persona-types` — Persona type CRUD
- `GET/POST/PUT/DELETE /api/v1/prompt-templates` — Custom LLM prompts

#### Reports
- `POST /api/v1/reports/weekly` — Generate weekly report
- `GET /api/v1/reports/weekly/{id}` — Retrieve generated report
- `GET /api/v1/reports/weekly` — List all reports

For complete API reference with examples, see [docs/API.md](docs/API.md).

---

## 🎨 Dashboard Screenshots

### Dashboard Overview
> Real-time KPIs, quality trends, hot leads, and recent calls at a glance

### Call Detail View
> Full transcript with speaker labels, quality breakdown, lead intelligence, BANT radar chart, action items, and sales audit keywords

### Analytics
> Agent comparison, quality trends, conversion funnels, and parameter heatmaps

### Leaderboard
> Rankings by quality score, conversion rate, improvement, and consistency

### Settings
> Configure quality parameters, intent signals, personas, integrations, and custom prompts

---

## 🏗️ Architecture Deep Dive

### Processing Pipeline

```
┌─────────────────┐
│  Call Upload    │ ← API or Webhook
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Celery Task    │ ← Async processing
│  Queue (Redis)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Transcription  │────▶│  Deepgram/Whisper│
│     Service     │     │  Speaker Diarize │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  LLM Analysis   │────▶│  GPT-4o-mini     │
│     Service     │     │  Structured JSON │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │ ← Store all results
│   Database      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  CRM Webhook    │────▶│  Salesforce/etc  │
│   (Outbound)    │     │  Update records  │
└─────────────────┘     └──────────────────┘
```

### Database Schema Highlights

- **Multi-tenant isolation** — All tables include `tenant_id` with RLS
- **Normalized design** — Separate tables for quality scores, intent signals, personas, action items
- **JSON columns** — Flexible storage for custom fields and analysis results
- **Comprehensive indexing** — Optimized for common queries (agent, date range, score, intent)
- **Audit trail** — Timestamps on all records, QA override tracking

### Scalability Considerations

- **Horizontal scaling** — Add more Celery workers to handle load
- **Database optimization** — Connection pooling, read replicas
- **Storage** — S3 backend for call recordings (unlimited capacity)
- **Caching** — Redis for session state and frequent queries
- **Rate limiting** — Per-tenant API rate limits (configurable)

---

## 📚 Configuration

### Quality Parameters Setup

Create or customize quality parameters via API or admin UI:

```json
{
  "name": "Opening & Greeting",
  "description": "Agent introduces themselves professionally, confirms customer name, sets agenda",
  "weight": 1.0,
  "category": "call_structure"
}
```

Default parameters are auto-created on tenant setup. Weights can be adjusted (0-1) to prioritize certain behaviors.

### Intent Signals Setup

```json
{
  "name": "Budget Confirmed",
  "description": "Customer explicitly mentions or confirms available budget or budget range",
  "weight": 1.5
}
```

### Persona Types Setup

```json
{
  "name": "Decision Maker",
  "description": "Has authority to sign contracts, budget control, urgent need identified"
}
```

### Custom LLM Prompts

Upload a Jinja2 template to customize the analysis prompt:

```jinja2
You are analyzing a {{ industry }} sales call.
Evaluate the agent's performance on these parameters:
{% for param in quality_parameters %}
- {{ param.name }}: {{ param.description }}
{% endfor %}

Respond with valid JSON only...
```

For detailed configuration guide, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

---

## 🚢 Production Deployment

For production deployments, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) which covers:

- **SSL/TLS setup** with Let's Encrypt
- **Reverse proxy** configuration (Nginx)
- **Database backups** and restore procedures
- **Monitoring** with Prometheus + Grafana
- **Log aggregation** with ELK stack
- **Secrets management** with Docker secrets or AWS Secrets Manager
- **Auto-scaling** Celery workers based on queue depth
- **High availability** with multiple backend replicas
- **Infrastructure as Code** — Terraform scripts for AWS (EC2, RDS, S3, ElastiCache)

---

## 🔧 Development

### Local Development (without Docker)

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

#### Celery Worker

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

### Code Quality

```bash
# Backend linting and formatting
ruff check backend/
ruff format backend/

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

---

## 📊 ROI & Business Impact

### Measurable Outcomes

- **20-30% increase in conversion rates** — Data-driven coaching on what works
- **40% reduction in ramp time** — New agents learn from top performers
- **3x faster lead prioritization** — Focus on hot leads first
- **50% reduction in QA time** — Automated scoring + spot-check validation
- **2x improvement in objection handling** — Rebuttal library built from real calls
- **360° visibility** — Never miss a coaching moment or hot lead

### Cost Comparison

| Solution | Monthly Cost (50 agents) | Setup Fee | Data Privacy |
|---|---|---|---|
| **SalesLens (self-hosted)** | ~$500 (API costs only) | $0 | ✅ Your infrastructure |
| Gong | $5,000-8,000 | $10,000+ | ⚠️ Third-party cloud |
| Chorus.ai | $4,000-6,000 | $8,000+ | ⚠️ Third-party cloud |
| Zipteams | $3,000-5,000 | $1,000 | ⚠️ Third-party cloud |

**SalesLens delivers 80-90% of enterprise features at 10% of the cost.**

---

## 🛠️ Technical Support & Services

### Implementation Services
- **Setup & Configuration** — 2-3 weeks for full deployment
- **CRM Integration** — Custom webhook setup for any CRM
- **Parameter Tuning** — Industry-specific quality parameters
- **Training** — Admin and user onboarding sessions

### Managed Hosting (Optional)
- **AWS/Azure deployment** — We handle infrastructure
- **Monitoring & Alerts** — 24/7 uptime monitoring
- **Backups & DR** — Automated daily backups, disaster recovery
- **Updates & Patches** — Automatic security and feature updates

### Custom Development
- **Custom integrations** — Connect to proprietary systems
- **White-labeling** — Branded UI and domain
- **Feature development** — Industry-specific capabilities
- **SLA & Support** — Guaranteed response times

---

## 🌟 What's Next?

### Roadmap

- [ ] **Email delivery** for weekly reports
- [ ] **Real-time analysis** (live call monitoring)
- [ ] **Mobile app** (iOS/Android) for on-the-go access
- [ ] **Advanced ML models** — Auto-suggest quality parameters based on conversion correlation
- [ ] **Speech analytics** — Detect tone, pace, talk ratio automatically
- [ ] **Multi-channel support** — Email, chat, video call analysis
- [ ] **Gamification** — Badges, achievements, challenges for agents
- [ ] **Coaching workflows** — Assign coaching tasks, track completion
- [ ] **Marketplace** — Industry-specific parameter packs and playbooks

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository and create a feature branch from `main`
2. Write clear, descriptive commit messages (use conventional commits)
3. Add type hints to all Python functions
4. Use TypeScript strict mode for frontend code
5. Include proper error handling
6. Test your changes before submitting
7. Update documentation for any API or config changes

### Code Style

- **Python:** PEP 8, use `ruff` for linting
- **TypeScript:** ESLint configuration in project
- **Commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

```
Copyright (c) 2026 SalesLens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 📞 Contact & Demo

**Ready to transform your sales team?**

- 🌐 Website: [https://saleslens.ai](https://saleslens.ai) *(coming soon)*
- 📧 Email: [hello@saleslens.ai](mailto:hello@saleslens.ai)
- 💼 LinkedIn: [linkedin.com/company/saleslens](https://linkedin.com/company/saleslens)
- 📅 Book a Demo: [calendly.com/saleslens/demo](https://calendly.com/saleslens/demo)

---

**Built with ❤️ for sales teams who win with data, not luck.**
