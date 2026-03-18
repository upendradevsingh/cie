# CIE Profile Frameworks — Research-Backed Intelligence

CIE extraction profiles encode battle-tested frameworks from organizational psychology, management science, and sales methodology. Every conversation becomes an opportunity to surface insights that the best managers, coaches, and leaders would notice.

## Design Philosophy

> **Goal: Make every individual and organization super intelligent and effective.**

Most teams generate hundreds of conversations weekly — 1:1s, standups, reviews, sales calls. The intelligence in those conversations is lost within minutes. CIE extracts it, structures it, and makes it actionable.

The profiles don't just extract "what was said." They surface **patterns that predict outcomes** — using frameworks validated by decades of research and millions of data points.

---

## Performance Profile v3.0

**12 extraction types** powered by **8 frameworks**.

### Frameworks Used

| Framework | Author | Research Basis | What CIE Detects |
|-----------|--------|---------------|-----------------|
| **Thanks for the Feedback** | Stone & Heen (Harvard) | Negotiation Project research | Appreciation vs coaching vs evaluation; observation vs label; blind spots |
| **Radical Candor** | Kim Scott (Google, Apple) | Management at Google/Apple | Radical candor vs ruinous empathy vs obnoxious aggression |
| **The Fearless Organization** | Amy Edmondson (Harvard) | 20+ years of research | Psychological safety stages: inclusion → learner → contributor → challenger |
| **Mindset** | Carol Dweck (Stanford) | Decades of motivation research | Growth vs fixed mindset language; manager reinforcement patterns |
| **5 Dysfunctions of a Team** | Patrick Lencioni | Team performance research | Accountability signals: follow-through, carry-forward, deflection |
| **High Output Management / OKRs** | Andy Grove (Intel) | Intel management system | Goal quality: measurable vs vague; leading vs lagging indicators |
| **Theory of Constraints** | Eliyahu Goldratt | Manufacturing/systems theory | Systemic vs situational blockers; constraint identification |
| **Drive** | Daniel Pink | Motivation science | Autonomy, mastery, purpose signals; engagement/disengagement |
| **Principles** | Ray Dalio (Bridgewater) | Idea meritocracy | Decision quality: were alternatives considered? Was dissent heard? |

### Extraction Types

#### Execution Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `COMMITMENT` | Lencioni | WHO + WHAT + WHEN with buy-in level (strong/tentative/ambiguous) |
| `BLOCKER` | Goldratt | Severity, type (dependency/resource/approval/technical), systemic vs situational |
| `ACTION_ITEM` | Grove | Assigned tasks with owner clarity flag |
| `DECISION` | Dalio | Who decided, alternatives considered, whether dissent was heard |

#### Goal & Progress Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `GOAL_UPDATE` | Grove (OKRs) | Progress with OKR quality scoring (measurable/vague/missing key results) |
| `ACCOUNTABILITY_SIGNAL` | Lencioni | Follow-through, carry-forward patterns, deflection, peer accountability |

#### Feedback & Growth Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `FEEDBACK` | Stone & Heen + Kim Scott | Type (appreciation/coaching/evaluation), candor quadrant, observation vs label, blind spots |
| `COACHING_MOMENT` | Stone & Heen | Skill building, career development, reframing, experience sharing |
| `RECOGNITION` | Stone & Heen | Appreciation with visibility level (private/team/leadership/public) |

#### People & Team Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `PSYCHOLOGICAL_SAFETY` | Edmondson | 4 stages (inclusion/learner/contributor/challenger), positive/negative signals |
| `MINDSET_SIGNAL` | Dweck | Growth vs fixed mindset language, manager reinforcement patterns |
| `SENTIMENT` | Pink (Drive) | Energy level, motivational driver (autonomy/mastery/purpose), engagement level |

### Example: What CIE Extracts From a 1:1

**Input:** Manager-engineer 1:1 conversation (6 segments, 44 seconds)

**Output:**
```
[RECOGNITION] Sarah appreciates James for staying late to help the team.
  → visibility: private, what_for: staying late to help ship on time

[MINDSET_SIGNAL] James expresses fixed mindset about DevOps.
  → mindset_type: fixed, signal: "I just don't get DevOps stuff"

[COACHING_MOMENT] Sarah reframes limitation as growth area + suggests pair-programming.
  → coaching_type: skill_building, actionable: true

[ACCOUNTABILITY_SIGNAL] Third week of carry-forward on API docs.
  → accountability_type: carry_forward, healthy: false

[COMMITMENT] James commits to completing docs by Wednesday.
  → deadline: Wednesday, buy_in_level: strong, specificity: high
```

**Manager insight:** Sarah is doing great on appreciation and coaching, but the carry-forward pattern on API docs suggests an accountability gap that needs addressing.

---

## Sales Profile v2.0

**8 extraction types** powered by **4 methodologies**.

### Frameworks Used

| Framework | Author | Research Basis | What CIE Detects |
|-----------|--------|---------------|-----------------|
| **SPIN Selling** | Neil Rackham | 35,000+ sales calls analyzed across 12 years | Question quality: situation/problem/implication/need-payoff ratio |
| **MEDDPICC** | John McMahon (PTC) | Enterprise sales qualification | 8-component deal scorecard: metrics, economic buyer, pain, champion, etc. |
| **The Challenger Sale** | Dixon & Adamson (CEB) | 6,000+ reps studied | Rep behavior: teach/tailor/take-control vs relationship selling |
| **BANT** | IBM | Classic qualification | Budget, Authority, Need, Timeline scoring |

### Extraction Types

#### Discovery Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `SPIN_QUESTION` | Rackham | Each question classified (situation/problem/implication/need-payoff) with effectiveness rating |

#### Deal Qualification
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `MEDDPICC_SIGNAL` | McMahon | 8-component scorecard (metrics/economic_buyer/decision_criteria/decision_process/pain/champion/paper_process/competition) with strength rating |

#### Objection & Competitive Intelligence
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `OBJECTION` | General | Category (price/timing/authority/need/trust/competition/technical), handling quality (effective/partial/missed) |

#### Rep Behavior
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `CHALLENGER_SIGNAL` | Dixon & Adamson | Teach/tailor/take_control vs relationship_selling patterns |

#### Deal Health
| Type | Framework | What It Finds |
|------|-----------|--------------|
| `BUYING_SIGNAL` | General | Signal strength + deal stage indicator |
| `DEAL_RISK` | MEDDPICC | Risk type (no_champion/no_metrics/competitor_threat/etc.) + mitigation status |
| `NEXT_STEP` | General | Concrete (who/what/when) vs vague follow-ups |

---

## Benchmarking Results

### Performance Profile — Eval Suite (25 gold conversations)

| Metric | Score | Baseline |
|--------|-------|----------|
| Overall F1 | 0.505 | ≥ 0.40 |
| Overall Precision | 0.560 | ≥ 0.45 |
| Overall Recall | 0.461 | ≥ 0.35 |
| Ambiguous FP rate | 0.000 | ≤ 0.10 |
| Edge case FP rate | 0.000 | ≤ 0.10 |

**Per-type performance:**

| Type | Precision | Recall | F1 |
|------|-----------|--------|-----|
| BLOCKER | 0.64 | 0.82 | 0.72 |
| COMMITMENT | 0.66 | 0.61 | 0.63 |
| DECISION | 1.00 | 0.45 | 0.62 |
| ACTION_ITEM | 0.53 | 0.40 | 0.46 |
| GOAL_UPDATE | 0.67 | 0.33 | 0.44 |
| FEEDBACK | 0.18 | 0.13 | 0.15 |

**Key findings:**
- BLOCKER detection is strongest (F1=0.72) — clear language patterns
- COMMITMENT detection is reliable (F1=0.63)
- FEEDBACK needs improvement — being addressed with Stone & Heen framework
- Ambiguous conversations correctly produce 0 extractions (0% FP rate)

### Eval Suite Details

- **25 gold-standard conversations** covering 1:1s, standups, feedback, ambiguous, Hinglish, edge cases
- **4 test layers**: fast parsing (16 tests), API integration (13 tests), LLM quality (13 tests), stability
- Run: `pytest -m fast` (instant) | `pytest -m llm` (3 min, needs OPENAI_API_KEY)
- Quality gate: any code change that drops below baselines fails the eval

---

## Adding New Frameworks

To add a new framework to a profile:

1. **Research the framework** — understand the core concepts and how they manifest in conversations
2. **Define extraction type** in the profile YAML with:
   - Clear `description` referencing the framework
   - Detailed `prompt_hint` with examples and classification rules
   - Typed `attributes` for structured output
3. **Add gold conversations** to `backend/tests/eval/gold_dataset.json` that exercise the new type
4. **Run the eval suite** — `pytest -m llm` — verify no regression
5. **Calibrate baselines** — update `baseline_scores.json` if thresholds change

---

## References

### Performance Management
- Stone, D. & Heen, S. (2014). *Thanks for the Feedback*. Penguin Books.
- Scott, K. (2017). *Radical Candor*. St. Martin's Press.
- Edmondson, A. (2018). *The Fearless Organization*. Wiley.
- Dweck, C. (2006). *Mindset: The New Psychology of Success*. Ballantine Books.
- Lencioni, P. (2002). *The Five Dysfunctions of a Team*. Jossey-Bass.
- Grove, A. (1983). *High Output Management*. Vintage Books.
- Goldratt, E. (1984). *The Goal*. North River Press.
- Pink, D. (2009). *Drive*. Riverhead Books.
- Dalio, R. (2017). *Principles*. Simon & Schuster.

### Sales
- Rackham, N. (1988). *SPIN Selling*. McGraw-Hill.
- Dixon, M. & Adamson, B. (2011). *The Challenger Sale*. Portfolio/Penguin.
- McMahon, J. (1996). MEDDIC Methodology. Parametric Technology Corporation.
