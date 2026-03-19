# CIE API Spec for PMS Frontend

## Base URLs

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:7070` |
| Production | `http://{CIE_PRIVATE_IP}:8000` (read from SSM `/cie/private-ip`) |

## Authentication

All endpoints except `/health` require `Authorization: Bearer {token}`.
PMS backend generates per-tenant JWTs signed with the shared CIE secret.

---

## Endpoints

### `GET /health`
No auth required.
```json
{"status": "ok", "service": "cie"}
```

### `POST /api/v1/conversations`
Submit a conversation for extraction. Returns `202 Accepted`.

**Request:**
```json
{
  "source": "meeting_transcript",
  "profile": "performance",
  "language": "en",
  "participants": [
    {"externalId": "user-1", "name": "Sarah Chen", "role": "manager"},
    {"externalId": "user-2", "name": "James Wilson", "role": "engineer"}
  ],
  "segments": [
    {
      "speaker": "Sarah Chen",
      "text": "How's the migration going?",
      "startTime": 0.0,
      "endTime": 3.5
    }
  ],
  "callback_url": null
}
```

**Response (202):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "source": "meeting_transcript",
  "profile_id": "performance",
  "status": "pending",
  "language": "en",
  "participants": [...],
  "summary": null,
  "error_message": null,
  "processing_time_ms": null,
  "created_at": "2026-03-19T10:00:00Z",
  "updated_at": "2026-03-19T10:00:00Z"
}
```

### `GET /api/v1/conversations/{id}`
Get conversation status.

**Response:**
```json
{
  "id": "uuid",
  "status": "pending | transcribing | extracting | completed | failed",
  "summary": "Concise meeting summary...",
  "error_message": null,
  "processing_time_ms": 15234,
  ...
}
```

**Status flow:** `pending` → `extracting` → `completed` (or `failed`)

### `GET /api/v1/conversations/{id}/extractions`
Get extractions for a conversation.

- Returns `202` with empty array `[]` while conversation is still processing
- Returns `200` with extraction array when complete

**Response (200):**
```json
[
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "tenant_id": "uuid",
    "extraction_type": "COMMITMENT",
    "description": "James committed to finishing the API migration by Friday.",
    "confidence": 0.90,
    "attributed_to": {
      "externalId": "user-2",
      "name": "James Wilson",
      "role": "engineer"
    },
    "evidence": "I will have the API migration done by Friday.",
    "evidence_start_ms": null,
    "evidence_end_ms": null,
    "status": "ACTIVE",
    "attributes": {
      "deadline": "Friday",
      "owner_id": "James",
      "specificity": "high",
      "buy_in_level": "strong"
    },
    "corrected": false,
    "created_at": "2026-03-19T10:00:15Z"
  }
]
```

---

## Extraction Types (Performance Profile v3.0)

### Pass 1 — Content Extraction (10 types)

| Type | Icon Suggestion | Category | Description | Key Attributes |
|------|----------------|----------|-------------|---------------|
| `COMMITMENT` | ✊ | Execution | Promise made by a participant | `deadline`, `owner_id`, `specificity` (low/medium/high), `buy_in_level` (strong/tentative/ambiguous) |
| `BLOCKER` | 🚫 | Execution | Something preventing progress | `severity` (low-critical), `blocked_by`, `status` (open/resolved), `blocker_type` (dependency/resource/approval/technical/process/knowledge), `constraint_nature` (systemic/situational) |
| `ACTION_ITEM` | ☑️ | Execution | Task assigned to someone | `assignee`, `assigned_by`, `due_date`, `priority` (low/medium/high), `has_clear_owner` (bool) |
| `DECISION` | 💡 | Execution | Decision made or agreed upon | `decided_by`, `impact` (low/medium/high), `alternatives_considered` (list), `dissent_heard` (bool) |
| `GOAL_UPDATE` | 📊 | Progress | Progress update on goal/OKR | `progress_pct`, `direction` (on_track/at_risk/behind/completed), `metric_name`, `metric_value`, `okr_quality` (measurable/vague/missing_key_results) |
| `RECOGNITION` | 🌟 | Feedback | Appreciation — "I see you, you matter" | `recipient`, `what_for`, `visibility` (private/team/leadership/public) |
| `FOLLOW_UP` | 📅 | Project Mgmt | Scheduled meeting or review | `who`, `when`, `where`, `topic`, `follow_up_type` (meeting/review/async_discussion/escalation) |
| `RISK` | ⚠️ | Project Mgmt | Threat to project/team/delivery | `risk_type` (people/delivery/technical/resource/quality), `severity` (low-critical), `mitigation_discussed` (bool) |
| `METRIC_TARGET` | 🎯 | Project Mgmt | Quantitative target proposed | `metric_name`, `current_value`, `target_value`, `timeframe` |
| `RECOMMENDATION` | 💬 | Project Mgmt | Advice from experience | `advisor`, `topic`, `actionability` (immediately_actionable/needs_discussion/long_term) |

### Pass 2 — Behavioral Extraction (6 types)

| Type | Icon Suggestion | Category | Description | Key Attributes |
|------|----------------|----------|-------------|---------------|
| `FEEDBACK` | 📝 | Growth | Feedback with framework classification | `feedback_type` (appreciation/coaching/evaluation), `candor_quadrant` (radical_candor/ruinous_empathy/obnoxious_aggression/manipulative_insincerity), `recipient`, `giver`, `specificity` (observation/label), `direction` (forward/backward_looking), `blind_spot_surfaced` (bool) |
| `COACHING_MOMENT` | 🎓 | Growth | Developmental guidance/mentoring | `coach`, `coachee`, `skill_area`, `coaching_type` (skill_building/career_development/reframing/experience_sharing), `actionable` (bool) |
| `PSYCHOLOGICAL_SAFETY` | 🛡️ | Team Health | Edmondson's 4 stages of safety | `stage` (inclusion/learner/contributor/challenger), `signal_type` (positive/negative), `indicator`, `who` |
| `MINDSET_SIGNAL` | 🧠 | Team Health | Dweck's growth vs fixed mindset | `mindset_type` (growth/fixed), `who`, `signal`, `manager_reinforcement` (bool) |
| `ACCOUNTABILITY_SIGNAL` | 📋 | Team Health | Lencioni's accountability patterns | `accountability_type` (follow_through/carry_forward/deflection/peer_accountability/manager_follow_up), `prior_commitment_reference`, `healthy` (bool) |
| `SENTIMENT` | 💭 | Team Health | Engagement and motivation signals | `score` (1-5), `energy_level` (low/medium/high), `motivational_driver` (autonomy/mastery/purpose/none_detected), `engagement` (highly_engaged/engaged/neutral/disengaged) |

---

## Frontend Rendering Guide

### Grouping Extractions

Suggested groups for the UI:

```typescript
const GROUPS = {
  'Action Items': ['COMMITMENT', 'ACTION_ITEM'],
  'Decisions': ['DECISION'],
  'Blockers & Risks': ['BLOCKER', 'RISK'],
  'Goals & Metrics': ['GOAL_UPDATE', 'METRIC_TARGET'],
  'Follow-ups': ['FOLLOW_UP'],
  'Feedback & Recognition': ['FEEDBACK', 'RECOGNITION', 'COACHING_MOMENT', 'RECOMMENDATION'],
  'Team Health': ['PSYCHOLOGICAL_SAFETY', 'MINDSET_SIGNAL', 'ACCOUNTABILITY_SIGNAL', 'SENTIMENT'],
};
```

### Confidence Display

| Confidence | Display | Color |
|------------|---------|-------|
| >= 0.80 | High confidence | Green |
| 0.60 - 0.79 | Medium confidence | Yellow/Orange |
| < 0.60 | Low confidence | Gray (consider hiding) |

### Attribute Rendering Per Type

**COMMITMENT / ACTION_ITEM:**
```
[Owner Name] → [Description]
📅 Due: [deadline/due_date]     ⚡ Priority: [high/medium/low]
```

**BLOCKER:**
```
🚫 [Description]
Blocked by: [blocked_by]     Severity: [critical/high/medium/low]
Type: [dependency/resource/approval/technical]
```

**FOLLOW_UP:**
```
📅 [Description]
Who: [who]     When: [when]     Where: [where]
Topic: [topic]
```

**RISK:**
```
⚠️ [Description]
Type: [people/delivery/technical/resource]     Severity: [critical/high]
Mitigation discussed: [yes/no]
```

**METRIC_TARGET:**
```
🎯 [Description]
[metric_name]: [current_value] → [target_value]
Timeframe: [timeframe]
```

**FEEDBACK:**
```
📝 [Description]
Type: [appreciation/coaching/evaluation]
Candor: [radical_candor/ruinous_empathy]
From: [giver] → To: [recipient]
```

**PSYCHOLOGICAL_SAFETY:**
```
🛡️ [Description]
Stage: [inclusion/learner/contributor/challenger]
Signal: [positive ✅ / negative ❌]
```

**MINDSET_SIGNAL:**
```
🧠 [Description]
[growth 🌱 / fixed 🔒] — [who]
```

---

## TypeScript Types

```typescript
interface CieExtraction {
  id: string;
  conversation_id: string;
  tenant_id: string;
  extraction_type: ExtractionType;
  description: string;
  confidence: number;
  attributed_to?: {
    externalId: string;
    name: string;
    role: string;
  };
  evidence?: string;
  evidence_start_ms?: number;
  evidence_end_ms?: number;
  status: string;
  attributes: Record<string, any>;
  corrected: boolean;
  created_at: string;
}

type ExtractionType =
  // Content (Pass 1)
  | 'COMMITMENT'
  | 'BLOCKER'
  | 'ACTION_ITEM'
  | 'DECISION'
  | 'GOAL_UPDATE'
  | 'RECOGNITION'
  | 'FOLLOW_UP'
  | 'RISK'
  | 'METRIC_TARGET'
  | 'RECOMMENDATION'
  // Behavioral (Pass 2)
  | 'FEEDBACK'
  | 'COACHING_MOMENT'
  | 'PSYCHOLOGICAL_SAFETY'
  | 'MINDSET_SIGNAL'
  | 'ACCOUNTABILITY_SIGNAL'
  | 'SENTIMENT';

// Attribute types per extraction
interface CommitmentAttrs {
  deadline?: string;
  owner_id?: string;
  specificity?: 'low' | 'medium' | 'high';
  buy_in_level?: 'strong' | 'tentative' | 'ambiguous';
}

interface BlockerAttrs {
  severity?: 'low' | 'medium' | 'high' | 'critical';
  blocked_by?: string;
  status?: 'open' | 'resolved';
  blocker_type?: 'dependency' | 'resource' | 'approval' | 'technical' | 'process' | 'knowledge';
  constraint_nature?: 'systemic' | 'situational';
}

interface ActionItemAttrs {
  assignee?: string;
  assigned_by?: string;
  due_date?: string;
  priority?: 'low' | 'medium' | 'high';
  has_clear_owner?: boolean;
}

interface DecisionAttrs {
  decided_by?: string;
  impact?: 'low' | 'medium' | 'high';
  alternatives_considered?: string[];
  dissent_heard?: boolean;
}

interface GoalUpdateAttrs {
  progress_pct?: number;
  direction?: 'on_track' | 'at_risk' | 'behind' | 'completed';
  metric_name?: string;
  metric_value?: string;
  okr_quality?: 'measurable' | 'vague' | 'missing_key_results';
}

interface RecognitionAttrs {
  recipient?: string;
  what_for?: string;
  visibility?: 'private' | 'team' | 'leadership' | 'public';
}

interface FollowUpAttrs {
  who?: string;
  when?: string;
  where?: string;
  topic?: string;
  follow_up_type?: 'meeting' | 'review' | 'async_discussion' | 'escalation';
}

interface RiskAttrs {
  risk_type?: 'people' | 'delivery' | 'technical' | 'resource' | 'quality';
  severity?: 'low' | 'medium' | 'high' | 'critical';
  mitigation_discussed?: boolean;
}

interface MetricTargetAttrs {
  metric_name?: string;
  current_value?: string;
  target_value?: string;
  timeframe?: string;
}

interface RecommendationAttrs {
  advisor?: string;
  topic?: string;
  actionability?: 'immediately_actionable' | 'needs_discussion' | 'long_term';
}

interface FeedbackAttrs {
  feedback_type?: 'appreciation' | 'coaching' | 'evaluation';
  candor_quadrant?: 'radical_candor' | 'ruinous_empathy' | 'obnoxious_aggression' | 'manipulative_insincerity';
  recipient?: string;
  giver?: string;
  specificity?: 'observation' | 'label';
  direction?: 'forward_looking' | 'backward_looking';
  blind_spot_surfaced?: boolean;
}

interface CoachingMomentAttrs {
  coach?: string;
  coachee?: string;
  skill_area?: string;
  coaching_type?: 'skill_building' | 'career_development' | 'reframing' | 'experience_sharing';
  actionable?: boolean;
}

interface PsychologicalSafetyAttrs {
  stage?: 'inclusion' | 'learner' | 'contributor' | 'challenger';
  signal_type?: 'positive' | 'negative';
  indicator?: string;
  who?: string;
}

interface MindsetSignalAttrs {
  mindset_type?: 'growth' | 'fixed';
  who?: string;
  signal?: string;
  manager_reinforcement?: boolean;
}

interface AccountabilitySignalAttrs {
  accountability_type?: 'follow_through' | 'carry_forward' | 'deflection' | 'peer_accountability' | 'manager_follow_up';
  prior_commitment_reference?: string;
  healthy?: boolean;
}

interface SentimentAttrs {
  score?: number; // 1-5
  energy_level?: 'low' | 'medium' | 'high';
  motivational_driver?: 'autonomy' | 'mastery' | 'purpose' | 'none_detected';
  engagement?: 'highly_engaged' | 'engaged' | 'neutral' | 'disengaged';
}
```

---

## Processing Pipeline

```
Raw Transcript
      │
      ▼ Pass 0: Transcript Cleanup
      │ (fixes names, acronyms, Hinglish, filler)
      │
      ▼ Pass 1: Content Extraction (10 types)
      │ COMMITMENT, BLOCKER, ACTION_ITEM, DECISION, GOAL_UPDATE,
      │ RECOGNITION, FOLLOW_UP, RISK, METRIC_TARGET, RECOMMENDATION
      │
      ▼ Pass 2: Behavioral Extraction (6 types)
      │ FEEDBACK, COACHING_MOMENT, PSYCHOLOGICAL_SAFETY,
      │ MINDSET_SIGNAL, ACCOUNTABILITY_SIGNAL, SENTIMENT
      │
      ▼ All 16 types merged → stored → returned via API
```

**Typical processing time:** 15-30 seconds (3 LLM calls: cleanup + content + behavioral)

---

## Polling Pattern for PMS

```typescript
async function waitForExtractions(conversationId: string): Promise<CieExtraction[]> {
  const MAX_ATTEMPTS = 15;
  const INTERVAL_MS = 3000;

  for (let i = 0; i < MAX_ATTEMPTS; i++) {
    const response = await fetch(`/api/v1/conversations/${conversationId}/extractions`);

    if (response.status === 200) {
      return response.json(); // extractions ready
    }

    if (response.status === 202) {
      await sleep(INTERVAL_MS); // still processing
      continue;
    }

    throw new Error(`Unexpected status: ${response.status}`);
  }

  throw new Error('Extraction timed out');
}
```
