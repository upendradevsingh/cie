#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CIE Week Simulation — 10 conversations for one employee across a week
#
# Employee: James Wilson (Software Engineer)
# Manager: Sarah Chen
# Projects: API Gateway Migration, Dashboard Redesign
# Schedule: 3 daily meetings + 3 weekly 1:1s = ~10 conversations
# ---------------------------------------------------------------------------
set -euo pipefail

CIE_HOST="${1:-localhost:7070}"
BASE_URL="http://${CIE_HOST}"

# Generate JWT
JWT_SECRET="${JWT_SECRET:-local-dev-secret-for-testing-only}"
TOKEN=$(python3 -c "
import json, base64, hmac, hashlib, time, uuid
tid = uuid.uuid3(uuid.UUID(int=0), 'peakperf-tenant-42')
secret = '${JWT_SECRET}'
header = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}, separators=(',',':')).encode()).rstrip(b'=').decode()
payload = base64.urlsafe_b64encode(json.dumps({
    'tenant_id': str(tid), 'sub': 'pms-service',
    'iat': int(time.time()), 'exp': int(time.time()) + 3600
}, separators=(',',':')).encode()).rstrip(b'=').decode()
msg = f'{header}.{payload}'
sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
print(f'{msg}.{sig}')
")

AUTH="Authorization: Bearer ${TOKEN}"
CONV_IDS=()

submit() {
  local label="$1" body="$2"
  RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
    -d "$body" "${BASE_URL}/api/v1/conversations" 2>/dev/null)
  CID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])" 2>/dev/null)
  CONV_IDS+=("$CID")
  echo "  [$label] → $CID"
}

echo ""
echo "━━━ Simulating James Wilson's week ━━━"
echo "  Employee: James Wilson | Manager: Sarah Chen"
echo "  Projects: API Gateway Migration, Dashboard Redesign"
echo ""

# ── Monday ────────────────────────────────────────────────────────────
echo "📅 Monday"

submit "Mon Standup" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "mgr-sarah", "name": "Sarah Chen", "role": "manager"}
  ],
  "segments": [
    {"speaker": "James Wilson", "text": "Over the weekend I finished the rate limiter for the API Gateway. All tests passing. Today I am starting on the auth middleware rewrite.", "startTime": 0, "endTime": 8},
    {"speaker": "Sarah Chen", "text": "Great progress. The auth middleware is the critical path item — lets make sure we have it done by Wednesday.", "startTime": 9, "endTime": 14},
    {"speaker": "James Wilson", "text": "I will have the auth middleware done by Wednesday EOD. I might need help from the security team on the OAuth token validation spec.", "startTime": 15, "endTime": 22}
  ]
}'

submit "Mon API Gateway Sync" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "emp-priya", "name": "Priya Sharma", "role": "employee"}
  ],
  "segments": [
    {"speaker": "James Wilson", "text": "The rate limiter is deployed to staging. I saw some memory spikes under load though — the token bucket implementation might have a leak.", "startTime": 0, "endTime": 8},
    {"speaker": "Priya Sharma", "text": "I can help profile that. I noticed the same thing with the connection pooler last week — turned out to be the goroutine cleanup.", "startTime": 9, "endTime": 15},
    {"speaker": "James Wilson", "text": "That would be great. Can you look at it tomorrow? I need to focus on auth middleware today.", "startTime": 16, "endTime": 20},
    {"speaker": "Priya Sharma", "text": "Sure, I will profile the rate limiter memory usage tomorrow morning and share findings by noon.", "startTime": 21, "endTime": 26}
  ]
}'

# ── Tuesday ───────────────────────────────────────────────────────────
echo "📅 Tuesday"

submit "Tue 1:1 with Sarah" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "mgr-sarah", "name": "Sarah Chen", "role": "manager"}
  ],
  "segments": [
    {"speaker": "Sarah Chen", "text": "How are you feeling about the API Gateway timeline? The VP asked about it in leadership sync.", "startTime": 0, "endTime": 6},
    {"speaker": "James Wilson", "text": "Honestly a bit stressed. The auth middleware is more complex than estimated. The OAuth spec keeps changing — I have asked the security team three times and gotten different answers.", "startTime": 7, "endTime": 16},
    {"speaker": "Sarah Chen", "text": "That is frustrating. I will set up a meeting with the security lead tomorrow to lock down the spec. You should not have to chase them.", "startTime": 17, "endTime": 23},
    {"speaker": "James Wilson", "text": "That would help a lot. If we get the spec locked by Wednesday, I can still hit the Friday deadline for the auth middleware.", "startTime": 24, "endTime": 30},
    {"speaker": "Sarah Chen", "text": "Your work on the rate limiter was excellent by the way. The 3x throughput improvement really stood out in the demo. I mentioned it to the VP.", "startTime": 31, "endTime": 38},
    {"speaker": "James Wilson", "text": "Thanks, that means a lot. I also want to discuss the dashboard project — I have some concerns about the timeline.", "startTime": 39, "endTime": 44},
    {"speaker": "Sarah Chen", "text": "Lets talk about that Thursday. For now focus on the gateway — that is priority one.", "startTime": 45, "endTime": 50}
  ]
}'

submit "Tue Dashboard Kickoff" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "emp-mike", "name": "Mike Chen", "role": "employee"},
    {"externalId": "emp-lisa", "name": "Lisa Park", "role": "employee"}
  ],
  "segments": [
    {"speaker": "James Wilson", "text": "Alright, the dashboard redesign kicks off this week. I have reviewed the designs and the main risk is the real-time data pipeline. We need websocket support.", "startTime": 0, "endTime": 10},
    {"speaker": "Mike Chen", "text": "I can own the websocket layer. I built something similar at my last company. Should take about a week.", "startTime": 11, "endTime": 17},
    {"speaker": "Lisa Park", "text": "I will handle the React components. The design system update is blocking me though — the new chart library is not compatible with our current theme.", "startTime": 18, "endTime": 26},
    {"speaker": "James Wilson", "text": "Lisa, file a ticket for the design system incompatibility. Mike, lets sync Thursday on the websocket architecture. I will draft the data model by Wednesday.", "startTime": 27, "endTime": 35}
  ]
}'

# ── Wednesday ─────────────────────────────────────────────────────────
echo "📅 Wednesday"

submit "Wed Standup" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "mgr-sarah", "name": "Sarah Chen", "role": "manager"}
  ],
  "segments": [
    {"speaker": "James Wilson", "text": "Auth middleware is 80% done. The security team finally locked down the OAuth spec yesterday after Sarah escalated. I will finish implementation today.", "startTime": 0, "endTime": 9},
    {"speaker": "Sarah Chen", "text": "Good. What about the memory leak Priya was looking at?", "startTime": 10, "endTime": 13},
    {"speaker": "James Wilson", "text": "Priya found the issue — it was the token bucket not releasing expired entries. She already has a fix in review. Should be merged today.", "startTime": 14, "endTime": 22},
    {"speaker": "Sarah Chen", "text": "Excellent teamwork. Once auth middleware is done, I want you to shift fully to the dashboard project Thursday and Friday.", "startTime": 23, "endTime": 29}
  ]
}'

submit "Wed API Gateway Deep Dive" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "emp-priya", "name": "Priya Sharma", "role": "employee"}
  ],
  "segments": [
    {"speaker": "Priya Sharma", "text": "I profiled the rate limiter. The memory leak was in the cleanup goroutine — expired tokens were not being garbage collected. My fix reduces memory usage by 60% under load.", "startTime": 0, "endTime": 12},
    {"speaker": "James Wilson", "text": "That is a huge improvement. Can you also add a metric for token bucket utilization? We need observability before production.", "startTime": 13, "endTime": 19},
    {"speaker": "Priya Sharma", "text": "Already on it. I will add Prometheus metrics and a Grafana dashboard by end of day.", "startTime": 20, "endTime": 25},
    {"speaker": "James Wilson", "text": "Perfect. I decided we should also add circuit breaker pattern to the gateway. If the upstream auth service goes down, we should fail open with cached tokens for 30 seconds.", "startTime": 26, "endTime": 35}
  ]
}'

# ── Thursday ──────────────────────────────────────────────────────────
echo "📅 Thursday"

submit "Thu 1:1 with Sarah" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "mgr-sarah", "name": "Sarah Chen", "role": "manager"}
  ],
  "segments": [
    {"speaker": "Sarah Chen", "text": "Auth middleware shipped yesterday — nice work hitting the Wednesday deadline. How is the dashboard project looking?", "startTime": 0, "endTime": 7},
    {"speaker": "James Wilson", "text": "Thanks. Dashboard is my concern. The real-time pipeline needs websockets and our current infrastructure does not support it. Mike is owning that piece but it might take two weeks, not one.", "startTime": 8, "endTime": 18},
    {"speaker": "Sarah Chen", "text": "Can we descope for v1? Maybe start with polling instead of websockets and add real-time in v2?", "startTime": 19, "endTime": 25},
    {"speaker": "James Wilson", "text": "That is actually a smart call. Polling with 5-second intervals would cover 90% of use cases. I will talk to Mike about pivoting today.", "startTime": 26, "endTime": 33},
    {"speaker": "Sarah Chen", "text": "Good decision. Also, I want to give you feedback on your technical leadership this sprint. You have been excellent at unblocking others — helping Priya debug, coordinating with security team, mentoring Mike on the architecture.", "startTime": 34, "endTime": 45},
    {"speaker": "James Wilson", "text": "I appreciate that. I am also thinking about my growth — I would like to take on more architecture ownership. Maybe lead the next system design review?", "startTime": 46, "endTime": 53},
    {"speaker": "Sarah Chen", "text": "Absolutely. I will nominate you for the Q2 architecture review committee. You have earned it.", "startTime": 54, "endTime": 59}
  ]
}'

submit "Thu Dashboard Architecture" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "emp-mike", "name": "Mike Chen", "role": "employee"},
    {"externalId": "emp-lisa", "name": "Lisa Park", "role": "employee"}
  ],
  "segments": [
    {"speaker": "James Wilson", "text": "After talking with Sarah, we are pivoting the dashboard v1 to use polling instead of websockets. This cuts the timeline from 3 weeks to 10 days.", "startTime": 0, "endTime": 9},
    {"speaker": "Mike Chen", "text": "That makes sense for v1. I will build the polling service this week and design the websocket upgrade path for v2.", "startTime": 10, "endTime": 17},
    {"speaker": "Lisa Park", "text": "The chart library issue is resolved — I found a workaround using the adapter pattern. Components are 50% done.", "startTime": 18, "endTime": 24},
    {"speaker": "James Wilson", "text": "Great problem solving Lisa. Here is the plan: Mike finishes polling by Monday, Lisa finishes components by Tuesday, I will wire everything together Wednesday. Demo to stakeholders Thursday next week.", "startTime": 25, "endTime": 36}
  ]
}'

# ── Friday ────────────────────────────────────────────────────────────
echo "📅 Friday"

submit "Fri 1:1 with Sarah — Week Wrap" '{
  "source": "pms-checkin", "profile": "performance", "language": "en",
  "participants": [
    {"externalId": "emp-james", "name": "James Wilson", "role": "employee"},
    {"externalId": "mgr-sarah", "name": "Sarah Chen", "role": "manager"}
  ],
  "segments": [
    {"speaker": "Sarah Chen", "text": "Lets do a quick week recap. API Gateway — where do we stand?", "startTime": 0, "endTime": 4},
    {"speaker": "James Wilson", "text": "Gateway is production-ready. Rate limiter deployed, memory leak fixed, auth middleware shipped, Priya added observability. We are cutting the release Monday.", "startTime": 5, "endTime": 14},
    {"speaker": "Sarah Chen", "text": "Incredible week. And the dashboard?", "startTime": 15, "endTime": 18},
    {"speaker": "James Wilson", "text": "Dashboard v1 plan is locked. Polling instead of websockets for v1. Mike on backend, Lisa on frontend, I am doing data model and integration. Demo next Thursday.", "startTime": 19, "endTime": 28},
    {"speaker": "Sarah Chen", "text": "One concern — Lisa mentioned she is feeling overloaded with the design system work on top of dashboard components. Can you help redistribute?", "startTime": 29, "endTime": 36},
    {"speaker": "James Wilson", "text": "I will take over the design system adapter from Lisa this weekend so she can focus purely on the dashboard components next week. She should not be doing both.", "startTime": 37, "endTime": 45},
    {"speaker": "Sarah Chen", "text": "That is the kind of leadership I want to see. Have a good weekend James — you have earned it.", "startTime": 46, "endTime": 51}
  ]
}'

echo ""
echo "━━━ Submitted ${#CONV_IDS[@]} conversations ━━━"
echo ""
echo "Waiting for all extractions to complete (up to 5 min)..."

# Poll until all complete or timeout
MAX_WAIT=300
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
  sleep 10
  WAITED=$((WAITED + 10))

  DONE=0
  PENDING=0
  for CID in "${CONV_IDS[@]}"; do
    STATUS=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CID}" 2>/dev/null | \
      python3 -c "import sys,json;print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
      DONE=$((DONE + 1))
    else
      PENDING=$((PENDING + 1))
    fi
  done

  echo "  [${WAITED}s] ${DONE}/${#CONV_IDS[@]} done, ${PENDING} pending..."

  if [ $DONE -eq ${#CONV_IDS[@]} ]; then
    break
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  WEEK SUMMARY — James Wilson's Intelligence Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Fetch and display all extractions
# Regenerate token (original may have expired during processing)
TOKEN=$(python3 -c "
import json, base64, hmac, hashlib, time, uuid
tid = uuid.uuid3(uuid.UUID(int=0), 'peakperf-tenant-42')
secret = '${JWT_SECRET}'
header = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}, separators=(',',':')).encode()).rstrip(b'=').decode()
payload = base64.urlsafe_b64encode(json.dumps({
    'tenant_id': str(tid), 'sub': 'pms-service',
    'iat': int(time.time()), 'exp': int(time.time()) + 3600
}, separators=(',',':')).encode()).rstrip(b'=').decode()
msg = f'{header}.{payload}'
sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
print(f'{msg}.{sig}')
")
AUTH="Authorization: Bearer ${TOKEN}"

# Dump all extractions to a temp file via curl
ALL_EXTS_FILE=$(mktemp)
echo "[" > "$ALL_EXTS_FILE"
FIRST=true
for CID in "${CONV_IDS[@]}"; do
  EXTS=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CID}/extractions" 2>/dev/null || echo "[]")
  if [ "$FIRST" = true ]; then FIRST=false; else echo "," >> "$ALL_EXTS_FILE"; fi
  # Add conv_id to each extraction
  echo "$EXTS" | python3 -c "
import sys,json
exts=json.load(sys.stdin)
for e in exts:
    e['_conv_id']='$CID'
json.dump(exts, sys.stdout)
" >> "$ALL_EXTS_FILE" 2>/dev/null || echo "[]" >> "$ALL_EXTS_FILE"
done
echo "]" >> "$ALL_EXTS_FILE"

# Also collect conversation statuses
CONV_FILE=$(mktemp)
echo "[" > "$CONV_FILE"
FIRST=true
for CID in "${CONV_IDS[@]}"; do
  CONV_DATA=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CID}" 2>/dev/null || echo "{}")
  if [ "$FIRST" = true ]; then FIRST=false; else echo "," >> "$CONV_FILE"; fi
  echo "$CONV_DATA" >> "$CONV_FILE"
done
echo "]" >> "$CONV_FILE"

python3 -c "
import json, sys

with open('$CONV_FILE') as f:
    conversations = [c for c in json.load(f) if c]

with open('$ALL_EXTS_FILE') as f:
    raw = json.load(f)
all_extractions = []
for item in raw:
    if isinstance(item, list):
        all_extractions.extend(item)
    elif isinstance(item, dict):
        all_extractions.append(item)

# Summary stats
print(f'Total conversations: {len(conversations)}')
completed = sum(1 for c in conversations if c['status'] == 'completed')
failed = sum(1 for c in conversations if c['status'] == 'failed')
print(f'  Completed: {completed}')
if failed:
    print(f'  Failed: {failed}')
print(f'Total extractions: {len(all_extractions)}')
print()

# Group by type
from collections import Counter, defaultdict
by_type = defaultdict(list)
for e in all_extractions:
    by_type[e['extraction_type']].append(e)

type_counts = Counter(e['extraction_type'] for e in all_extractions)
print('Extractions by type:')
for t, count in type_counts.most_common():
    print(f'  {t}: {count}')
print()

# Show each type with details
for ext_type in ['COMMITMENT', 'BLOCKER', 'ACTION_ITEM', 'FEEDBACK', 'GOAL_UPDATE', 'DECISION', 'SENTIMENT']:
    items = by_type.get(ext_type, [])
    if not items:
        continue
    print(f'── {ext_type} ({len(items)}) ──')
    for e in items:
        conf = e.get('confidence', 0)
        desc = e.get('description', '')
        attrs = e.get('attributes', {})
        evidence = e.get('evidence', '')
        marker = '🟢' if conf >= 0.8 else '🟡' if conf >= 0.6 else '🔴'
        print(f'  {marker} [{conf:.2f}] {desc}')
        if attrs:
            attr_str = ', '.join(f'{k}={v}' for k,v in attrs.items() if v)
            if attr_str:
                print(f'       attrs: {attr_str}')
        if evidence:
            print(f'       evidence: \"{evidence[:100]}\"')
    print()

# Confidence distribution
confs = [e['confidence'] for e in all_extractions]
if confs:
    high = sum(1 for c in confs if c >= 0.8)
    med = sum(1 for c in confs if 0.6 <= c < 0.8)
    low = sum(1 for c in confs if c < 0.6)
    avg = sum(confs) / len(confs)
    print(f'── Confidence Distribution ──')
    print(f'  🟢 High (>=0.8): {high}')
    print(f'  🟡 Medium (0.6-0.8): {med}')
    print(f'  🔴 Low (<0.6): {low}')
    print(f'  Average: {avg:.2f}')
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cleanup
echo ""
rm -f "$ALL_EXTS_FILE" "$CONV_FILE" 2>/dev/null

echo "Cleaning up test data..."
CONV_LIST=$(printf "'%s'," "${CONV_IDS[@]}" | sed 's/,$//')
docker compose exec -T postgres psql -U cie -d cie -c "
  DELETE FROM corrections WHERE extraction_id IN (SELECT id FROM extractions WHERE conversation_id IN (${CONV_LIST}));
  DELETE FROM extractions WHERE conversation_id IN (${CONV_LIST});
  DELETE FROM conversations WHERE id IN (${CONV_LIST});
" 2>/dev/null && echo "Test data cleaned up." || echo "Could not clean up (manual cleanup may be needed)"
