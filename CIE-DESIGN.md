# CIE (Conversation Intelligence Engine) — Implementation Design

**Date:** 2026-03-15
**Status:** BUILDING
**Repo:** `upendradevsingh/cie` (forked from SalesLens)

---

## 1. What We're Building

CIE is a headless, profile-driven conversation extraction engine. It takes conversations (voice, text, chat) and extracts structured intelligence based on configurable profiles.

**Born from:** SalesLens (95% complete sales product)
**First client:** PeakPerf (performance management)
**Second client:** SalesLens (becomes a CIE consumer)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                       CIE                            │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐          │
│  │ Ingest   │→ │Transcribe│→ │  Extract  │→ Output  │
│  │          │  │          │  │  (LLM)    │          │
│  │ voice    │  │ Deepgram │  │           │  REST    │
│  │ text     │  │ Whisper  │  │ Profile-  │  Webhook │
│  │ chat     │  │ (skip if │  │ driven    │          │
│  │ meeting  │  │  text)   │  │ prompts   │          │
│  └──────────┘  └──────────┘  └───────────┘          │
│                                                      │
│  Profiles: performance | sales | custom              │
│  DB: PostgreSQL (conversations + extractions)        │
│  Queue: Celery + Redis                               │
└─────────────────────────────────────────────────────┘
```

## 3. Project Structure (Post-Fork)

```
cie/
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app
│   │   ├── config.py                # Settings
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── base.py              # Base + TimestampMixin
│   │   │   ├── conversation.py      # Core conversation model
│   │   │   ├── extraction.py        # Extractions (JSONB attributes)
│   │   │   ├── profile.py           # Profile config model
│   │   │   └── correction.py        # User corrections/feedback
│   │   ├── schemas/                 # Pydantic schemas
│   │   │   ├── conversation.py
│   │   │   ├── extraction.py
│   │   │   └── profile.py
│   │   ├── api/                     # Route handlers
│   │   │   ├── conversations.py     # POST /conversations, GET /{id}
│   │   │   ├── extractions.py       # GET /extractions, corrections
│   │   │   ├── profiles.py          # Profile CRUD
│   │   │   └── health.py            # Health check
│   │   ├── services/
│   │   │   ├── transcription/       # FROM SalesLens (as-is)
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── deepgram_provider.py
│   │   │   │   └── whisper_provider.py
│   │   │   ├── extraction/          # FROM SalesLens (generalized)
│   │   │   │   ├── engine.py        # Profile-driven LLM extraction
│   │   │   │   └── prompts.py       # Dynamic prompt builder
│   │   │   └── auth.py              # JWT validation (no user mgmt)
│   │   ├── profiles/                # YAML profile definitions
│   │   │   ├── performance.yaml
│   │   │   └── sales.yaml
│   │   ├── tasks/                   # Celery tasks
│   │   │   ├── __init__.py
│   │   │   └── process_conversation.py
│   │   └── db/
│   │       ├── session.py
│   │       └── tenant.py            # Tenant context
│   ├── alembic/                     # Migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
└── docs/
```

## 4. Core Models

### Conversation (replaces SalesLens Call)

```python
class ConversationStatus(str, Enum):
    pending = "pending"
    transcribing = "transcribing"
    extracting = "extracting"
    completed = "completed"
    failed = "failed"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    
    # Source
    source = Column(String(50), nullable=False)  # voice|text|chat|meeting|email
    source_metadata = Column(JSONB, default={})
    
    # Audio (optional — skip if text input)
    audio_url = Column(Text, nullable=True)
    audio_file_path = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Transcript
    transcript_raw = Column(Text, nullable=True)
    transcript_segments = Column(JSONB, nullable=True)
    language = Column(String(10), default="en")
    
    # Processing
    profile_id = Column(String(50), nullable=False)  # "performance", "sales"
    status = Column(Enum(ConversationStatus), default=ConversationStatus.pending)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Participants
    participants = Column(JSONB, default=[])
    
    # Callback
    callback_url = Column(Text, nullable=True)
    
    # Summary
    summary = Column(Text, nullable=True)
    
    # Relationships
    extractions = relationship("Extraction", back_populates="conversation")
```

### Extraction (generic, profile-driven)

```python
class Extraction(Base):
    __tablename__ = "extractions"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    conversation_id = Column(UUID, ForeignKey("conversations.id"), nullable=False)
    tenant_id = Column(UUID, nullable=False, index=True)
    
    # Core
    extraction_type = Column(String(30), nullable=False)  # COMMITMENT, BLOCKER, etc.
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Attribution
    attributed_to = Column(JSONB, nullable=True)  # {externalId, name, role}
    
    # Evidence
    evidence = Column(Text, nullable=True)
    evidence_start_ms = Column(Integer, nullable=True)
    evidence_end_ms = Column(Integer, nullable=True)
    
    # Lifecycle
    status = Column(String(20), default="ACTIVE")  # ACTIVE, RESOLVED, DELETED
    
    # Profile-specific attributes (extensible via JSONB)
    attributes = Column(JSONB, default={})
    
    # Correction tracking
    corrected = Column(Boolean, default=False)
    corrected_at = Column(DateTime, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="extractions")
```

## 5. Profile System

### Performance Profile (`profiles/performance.yaml`)

```yaml
profile_id: performance
version: "1.0"
display_name: "Performance Management"
description: "Extract commitments, blockers, feedback, and sentiment from 1:1s, check-ins, and team meetings"

llm:
  model: "gpt-4o-mini"        # Cost-efficient for routine extractions
  temperature: 0.15
  max_tokens: 2048
  fallback_model: "gpt-4o"    # For complex/ambiguous cases

extraction_types:
  COMMITMENT:
    enabled: true
    confidence_threshold: 0.80
    description: "A specific promise or commitment made by a participant"
    prompt_hint: "Look for personal ownership (I will, I'll, Let me) + specific deliverable. Exclude vague aspirations."
    attributes:
      - name: deadline
        type: date
        required: false
      - name: specificity
        type: enum
        values: [low, medium, high]
      - name: owner_id
        type: string
        required: false

  BLOCKER:
    enabled: true
    confidence_threshold: 0.75
    description: "Something preventing progress on work"
    attributes:
      - name: severity
        type: enum
        values: [low, medium, high, critical]
      - name: blocked_by
        type: string
      - name: status
        type: enum
        values: [open, resolved]

  FEEDBACK:
    enabled: true
    confidence_threshold: 0.70
    description: "Feedback given about a person's performance or behavior"
    attributes:
      - name: recipient
        type: string
      - name: sentiment
        type: enum
        values: [positive, constructive, negative]
      - name: competency
        type: string

  GOAL_UPDATE:
    enabled: true
    confidence_threshold: 0.70
    description: "Implicit or explicit progress update on a tracked goal"
    attributes:
      - name: progress_pct
        type: number
        required: false
      - name: direction
        type: enum
        values: [on_track, at_risk, behind, completed]

  ACTION_ITEM:
    enabled: true
    confidence_threshold: 0.75
    description: "A task or action that needs to be done"
    attributes:
      - name: assignee
        type: string
      - name: due_date
        type: date
        required: false
      - name: priority
        type: enum
        values: [low, medium, high]

  SENTIMENT:
    enabled: true
    confidence_threshold: 0.60
    description: "Overall emotional tone and engagement level"
    attributes:
      - name: score
        type: number
        min: 1
        max: 5
      - name: indicators
        type: list
      - name: energy_level
        type: enum
        values: [low, medium, high]

  DECISION:
    enabled: true
    confidence_threshold: 0.80
    description: "A decision that was made during the conversation"
    attributes:
      - name: decided_by
        type: string
      - name: impact
        type: enum
        values: [low, medium, high]

summary:
  enabled: true
  max_length: 200
  style: "concise, action-oriented"
```

### Sales Profile (`profiles/sales.yaml`)

```yaml
profile_id: sales
version: "1.0"
display_name: "Sales Intelligence"
description: "Extract quality scores, intent signals, BANT analysis from sales calls"

llm:
  model: "gpt-4o-mini"
  temperature: 0.15
  max_tokens: 4096

extraction_types:
  QUALITY_SCORE:
    enabled: true
    confidence_threshold: 0.80
    description: "Quality assessment for a scoring parameter"
    attributes:
      - name: parameter_name
        type: string
      - name: score
        type: number
        min: 0
        max: 10
      - name: justification
        type: string
      - name: weight
        type: number

  INTENT_SIGNAL:
    enabled: true
    confidence_threshold: 0.75
    attributes:
      - name: signal_name
        type: string
      - name: detected
        type: boolean
      - name: details
        type: string

  PERSONA_BANT:
    enabled: true
    confidence_threshold: 0.70
    attributes:
      - name: budget_score
        type: number
      - name: authority_score
        type: number
      - name: need_score
        type: number
      - name: timeline_score
        type: number
      - name: persona_type
        type: string

  OBJECTION:
    enabled: true
    confidence_threshold: 0.75
    attributes:
      - name: category
        type: string
      - name: rebuttal
        type: string
      - name: resolved
        type: boolean

  LEAD_INTENT:
    enabled: true
    confidence_threshold: 0.80
    attributes:
      - name: intent_score
        type: number
        min: 0
        max: 100
      - name: classification
        type: enum
        values: [hot, warm, cold]
      - name: follow_up_urgency
        type: enum
        values: [immediate, this_week, next_week, nurture]

summary:
  enabled: true
  max_length: 300
  style: "sales-focused, highlight intent and next steps"
```

## 6. Extraction Engine (Core Innovation)

The engine is profile-driven. One codebase handles any domain.

```python
class ExtractionEngine:
    """Profile-driven extraction using LLM.
    
    Reads profile YAML → builds dynamic prompt → calls LLM → 
    parses structured output → returns typed Extractions.
    """
    
    def __init__(self, profile: ExtractionProfile):
        self.profile = profile
        self.model = profile.llm.model
        self.temperature = profile.llm.temperature
    
    async def extract(self, transcript: str, participants: list) -> ExtractionResult:
        # 1. Build prompt from profile
        prompt = self._build_prompt(transcript, participants)
        
        # 2. Call LLM (with retry)
        raw_json = await self._call_llm(prompt)
        
        # 3. Parse into Extractions
        extractions = self._parse_extractions(raw_json)
        
        # 4. Filter by confidence threshold
        filtered = [e for e in extractions 
                    if e.confidence >= self.profile.get_threshold(e.extraction_type)]
        
        return ExtractionResult(
            extractions=filtered,
            summary=raw_json.get("summary", ""),
            model_used=self.model,
            tokens_used=self._last_token_count
        )
    
    def _build_prompt(self, transcript, participants):
        """Dynamically build prompt from profile config.
        
        Each extraction type in the profile becomes a section in the prompt
        with its description, attributes, and examples.
        """
        sections = []
        for ext_type, config in self.profile.extraction_types.items():
            if not config.enabled:
                continue
            section = f"""
## {ext_type}
{config.description}
{f'Hint: {config.prompt_hint}' if config.prompt_hint else ''}

Expected attributes: {json.dumps([a.dict() for a in config.attributes])}

Confidence threshold: {config.confidence_threshold}
Only extract if confidence >= {config.confidence_threshold}
"""
            sections.append(section)
        
        return EXTRACTION_PROMPT_TEMPLATE.format(
            profile_name=self.profile.display_name,
            extraction_sections="\n".join(sections),
            transcript=transcript,
            participants=json.dumps(participants)
        )
```

## 7. Cost Optimization

| Component | Model | Cost | Rationale |
|-----------|-------|------|-----------|
| Performance extraction | gpt-4o-mini | ~$0.002/conv | Routine 1:1 check-ins are simple |
| Sales extraction | gpt-4o-mini | ~$0.003/conv | Already proven in SalesLens |
| Complex/ambiguous cases | gpt-4o (fallback) | ~$0.02/conv | Only when mini confidence < threshold |
| Transcription | Deepgram Nova-3 | ~$0.0043/min | Best price-performance for diarization |
| Transcription fallback | Whisper | ~$0.006/min | When Deepgram unavailable |

**Estimated cost per conversation:** $0.005-0.01 (mostly under 1 cent)

## 8. PeakPerf Integration

### How PeakPerf Calls CIE

```java
// PeakPerf: CieClient.java
@Service
public class CieClient {
    
    @Value("${cie.base-url}")
    private String cieBaseUrl;
    
    private final RestTemplate restTemplate;
    
    public ConversationResponse submitCheckin(
            String transcript, 
            Long userId, 
            String userName,
            String jwtToken) {
        
        var request = Map.of(
            "source", "text",
            "profile", "performance",
            "participants", List.of(Map.of(
                "externalId", userId.toString(),
                "name", userName,
                "role", "individual_contributor"
            )),
            "segments", List.of(Map.of(
                "speaker", userId.toString(),
                "text", transcript
            ))
        );
        
        var headers = new HttpHeaders();
        headers.setBearerAuth(jwtToken);
        
        return restTemplate.postForObject(
            cieBaseUrl + "/api/v1/conversations",
            new HttpEntity<>(request, headers),
            ConversationResponse.class
        );
    }
    
    public ExtractionResponse getExtractions(String conversationId, String jwtToken) {
        var headers = new HttpHeaders();
        headers.setBearerAuth(jwtToken);
        
        return restTemplate.exchange(
            cieBaseUrl + "/api/v1/conversations/" + conversationId + "/extractions",
            HttpMethod.GET,
            new HttpEntity<>(headers),
            ExtractionResponse.class
        ).getBody();
    }
}
```

### PeakPerf stores extracted data in its own domain models:

```
CIE Extraction (COMMITMENT) → PeakPerf Commitment table
CIE Extraction (BLOCKER)    → PeakPerf BlockerTracking table
CIE Extraction (FEEDBACK)   → PeakPerf FeedbackNote table
CIE Extraction (SENTIMENT)  → PeakPerf CheckInMood score
CIE Extraction (GOAL_UPDATE) → PeakPerf GoalProgress update
```

## 9. Migration Path (SalesLens → CIE Consumer)

After CIE is built, SalesLens switches from local extraction to CIE calls:

```python
# BEFORE (SalesLens local extraction):
analyzer = CallAnalyzer()
result = await analyzer.analyze_call(transcript, quality_params, ...)

# AFTER (SalesLens calls CIE):
cie_client = CieClient(base_url=settings.CIE_URL)
response = await cie_client.submit_conversation(
    source="phone",
    profile="sales",
    transcript=transcript,
    participants=participants
)
extractions = await cie_client.get_extractions(response.conversation_id)
# Map CIE extractions → SalesLens domain models
```

## 10. Build Plan

| Step | Task | Effort | Agent |
|------|------|--------|-------|
| 1 | Fork SalesLens → CIE repo | 30min | Jarvis |
| 2 | Strip sales-specific code, keep generic engine | 2-3hr | Kira |
| 3 | Create generic models (Conversation, Extraction) | 1-2hr | Kira |
| 4 | Build profile system (YAML loader + prompt builder) | 2-3hr | Kira |
| 5 | Create performance.yaml + sales.yaml profiles | 1hr | Jarvis |
| 6 | Build extraction engine (profile-driven) | 2-3hr | Kira |
| 7 | Build API endpoints (conversations, extractions) | 2hr | Kira |
| 8 | JWT validation middleware | 1hr | Kira |
| 9 | Alembic migrations for new schema | 1hr | Kira |
| 10 | Docker compose (CIE + PostgreSQL + Redis) | 30min | Jarvis |
| 11 | Integration tests | 2hr | Kira |
| 12 | PeakPerf CieClient (Java) | 2hr | Kira |
| 13 | End-to-end test on worker | 1hr | Jarvis |

**Total estimate:** ~18-20 hours of agent work (parallel execution)

---

*This doc drives the build. Every PR should reference it.*
