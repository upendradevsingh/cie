#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CIE — Production endpoint tests with test data
#
# Tests all endpoints, verifies extractions, then cleans up test data.
#
# Usage:
#   ./test-production.sh <CIE_HOST>
#   ./test-production.sh 172.31.10.146        # private IP
#   ./test-production.sh 35.175.123.63        # public IP
# ---------------------------------------------------------------------------
set -euo pipefail

CIE_HOST="${1:-}"
[[ -z "$CIE_HOST" ]] && { echo "Usage: $0 <CIE_HOST>"; exit 1; }

BASE_URL="http://${CIE_HOST}:8000"
PASS=0
FAIL=0
CREATED_IDS=()

# Generate a test JWT using python-jose inside the cie-api container
# (matches the JWT_SECRET from the container's env)
TENANT_ID="11111111-1111-1111-1111-111111111111"
USER_ID="22222222-2222-2222-2222-222222222222"

TOKEN=$(cd /opt/cie && sudo docker compose -f docker-compose.prod.yml exec -T cie-api python3 -c "
from jose import jwt; import time, os
print(jwt.encode({
    'tenant_id': '${TENANT_ID}',
    'user_id': '${USER_ID}',
    'sub': '${USER_ID}',
    'iat': int(time.time()),
    'exp': int(time.time()) + 3600
}, os.environ['JWT_SECRET'], 'HS256'))
" 2>/dev/null)

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: Could not generate JWT token. Is CIE running?"
  exit 1
fi
AUTH="Authorization: Bearer ${TOKEN}"

log()  { echo -e "\033[1m[$1]\033[0m $2"; }
pass() { log "PASS" "$1"; PASS=$((PASS+1)); }
fail() { log "FAIL" "$1: $2"; FAIL=$((FAIL+1)); }

# ── Test 1: Health check (no auth) ─────────────────────────────────────
echo ""
echo "━━━ Testing CIE at ${BASE_URL} ━━━"
echo ""

RESP=$(curl -sf "${BASE_URL}/health" 2>/dev/null) || true
if echo "$RESP" | grep -q '"status":"ok"'; then
  pass "GET /health → ok"
else
  fail "GET /health" "$RESP"
fi

# ── Test 2: List profiles ──────────────────────────────────────────────
RESP=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/profiles" 2>/dev/null) || true
if echo "$RESP" | grep -q 'performance'; then
  PROFILE_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
  pass "GET /api/v1/profiles → ${PROFILE_COUNT} profiles"
else
  fail "GET /api/v1/profiles" "$RESP"
fi

# ── Test 3: Get specific profile ───────────────────────────────────────
RESP=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/profiles/performance" 2>/dev/null) || true
if echo "$RESP" | grep -q 'Performance Management'; then
  pass "GET /api/v1/profiles/performance → ok"
else
  fail "GET /api/v1/profiles/performance" "$RESP"
fi

# ── Test 4: Get non-existent profile (404) ─────────────────────────────
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "${BASE_URL}/api/v1/profiles/nonexistent" 2>/dev/null)
if [[ "$HTTP_CODE" == "404" ]]; then
  pass "GET /api/v1/profiles/nonexistent → 404"
else
  fail "GET /api/v1/profiles/nonexistent" "Expected 404, got $HTTP_CODE"
fi

# ── Test 5: Submit conversation (text segments, performance profile) ───
CONV_BODY=$(cat <<'JSON'
{
  "source": "test",
  "profile": "performance",
  "participants": [
    {"externalId": "mgr-001", "name": "Sarah Chen", "role": "manager"},
    {"externalId": "emp-001", "name": "James Wilson", "role": "employee"}
  ],
  "segments": [
    {"speaker": "Sarah Chen", "text": "Let's review your Q1 goals. How's the API migration going?", "startTime": 0.0, "endTime": 5.2},
    {"speaker": "James Wilson", "text": "The migration is about 70% done. I'm blocked on the auth service though — the team hasn't provided the new OAuth endpoints yet.", "startTime": 5.5, "endTime": 12.1},
    {"speaker": "Sarah Chen", "text": "That's a significant blocker. I'll escalate with the auth team today. Can you commit to finishing the remaining non-auth parts by Friday?", "startTime": 12.5, "endTime": 18.3},
    {"speaker": "James Wilson", "text": "Yes, I can definitely have the data layer and API routes done by Friday. The auth integration will need another week after they unblock us.", "startTime": 18.5, "endTime": 24.0},
    {"speaker": "Sarah Chen", "text": "Good. Your work on the performance improvements last sprint was excellent — the 40% latency reduction really stood out. Keep that momentum.", "startTime": 24.5, "endTime": 30.0}
  ],
  "language": "en"
}
JSON
)

RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "$CONV_BODY" "${BASE_URL}/api/v1/conversations" 2>/dev/null) || true

CONV_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [[ -n "$CONV_ID" && "$CONV_ID" != "" ]]; then
  CREATED_IDS+=("$CONV_ID")
  pass "POST /api/v1/conversations → 202, id=${CONV_ID}"
else
  fail "POST /api/v1/conversations" "$RESP"
fi

# ── Test 6: Submit conversation with sales profile ─────────────────────
SALES_BODY=$(cat <<'JSON'
{
  "source": "test",
  "profile": "sales",
  "participants": [
    {"externalId": "rep-001", "name": "Alex Taylor", "role": "sales_rep"},
    {"externalId": "prospect-001", "name": "Maria Garcia", "role": "prospect"}
  ],
  "segments": [
    {"speaker": "Alex Taylor", "text": "Thanks for taking my call, Maria. I understand you're looking to improve your team's conversation analytics.", "startTime": 0.0, "endTime": 4.5},
    {"speaker": "Maria Garcia", "text": "Yes, we have a budget of about $50K for this quarter, and our VP of Engineering has already approved the initiative.", "startTime": 5.0, "endTime": 10.2},
    {"speaker": "Alex Taylor", "text": "That's great. Our enterprise plan would fit perfectly within that budget. What's your timeline for implementation?", "startTime": 10.5, "endTime": 15.0},
    {"speaker": "Maria Garcia", "text": "We need something up and running by end of April. The main concern is integration with our existing Salesforce setup.", "startTime": 15.5, "endTime": 20.0}
  ],
  "language": "en"
}
JSON
)

RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "$SALES_BODY" "${BASE_URL}/api/v1/conversations" 2>/dev/null) || true

SALES_CONV_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [[ -n "$SALES_CONV_ID" && "$SALES_CONV_ID" != "" ]]; then
  CREATED_IDS+=("$SALES_CONV_ID")
  pass "POST /api/v1/conversations (sales) → 202, id=${SALES_CONV_ID}"
else
  fail "POST /api/v1/conversations (sales)" "$RESP"
fi

# ── Test 7: Auth required (no token) ──────────────────────────────────
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/conversations" 2>/dev/null)
if [[ "$HTTP_CODE" == "403" || "$HTTP_CODE" == "401" ]]; then
  pass "GET /api/v1/conversations (no auth) → ${HTTP_CODE}"
else
  fail "GET /api/v1/conversations (no auth)" "Expected 401/403, got $HTTP_CODE"
fi

# ── Test 8: Invalid profile (400) ─────────────────────────────────────
BAD_BODY='{"source":"test","profile":"nonexistent","segments":[{"speaker":"A","text":"Hello","startTime":0,"endTime":1}]}'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "$BAD_BODY" "${BASE_URL}/api/v1/conversations" 2>/dev/null)
if [[ "$HTTP_CODE" == "400" ]]; then
  pass "POST /api/v1/conversations (bad profile) → 400"
else
  fail "POST /api/v1/conversations (bad profile)" "Expected 400, got $HTTP_CODE"
fi

# ── Wait for async processing ─────────────────────────────────────────
echo ""
echo "Waiting for Celery to process conversations (up to 60s)..."
for i in $(seq 1 12); do
  sleep 5
  if [[ -n "$CONV_ID" ]]; then
    STATUS=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CONV_ID}" 2>/dev/null | \
      python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
      echo "  Conversation ${CONV_ID}: ${STATUS} (after $((i*5))s)"
      break
    fi
    echo "  Status: ${STATUS}... (${i}/12)"
  fi
done

# ── Test 9: Get conversation (should be completed or failed) ──────────
if [[ -n "$CONV_ID" ]]; then
  RESP=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CONV_ID}" 2>/dev/null) || true
  STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "unknown")
  if [[ "$STATUS" == "completed" ]]; then
    pass "GET /api/v1/conversations/${CONV_ID} → status=completed"
  else
    fail "GET /api/v1/conversations/${CONV_ID}" "status=${STATUS}"
    # Show error if failed
    ERROR=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_message',''))" 2>/dev/null || echo "")
    [[ -n "$ERROR" ]] && echo "    Error: $ERROR"
  fi
fi

# ── Test 10: List conversations ───────────────────────────────────────
RESP=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations" 2>/dev/null) || true
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [[ "$COUNT" -ge 1 ]]; then
  pass "GET /api/v1/conversations → ${COUNT} conversations"
else
  fail "GET /api/v1/conversations" "Expected >=1, got $COUNT"
fi

# ── Test 11: Get extractions ──────────────────────────────────────────
if [[ -n "$CONV_ID" ]]; then
  RESP=$(curl -sf -H "$AUTH" "${BASE_URL}/api/v1/conversations/${CONV_ID}/extractions" 2>/dev/null) || true
  EXT_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
  if [[ "$EXT_COUNT" -ge 1 ]]; then
    pass "GET /api/v1/conversations/${CONV_ID}/extractions → ${EXT_COUNT} extractions"

    # Show extraction types
    echo "$RESP" | python3 -c "
import sys, json
exts = json.load(sys.stdin)
for e in exts:
    print(f\"    [{e.get('extraction_type','')}] {e.get('description','')[:80]} (confidence: {e.get('confidence',0):.2f})\")
" 2>/dev/null || true

    # Get first extraction ID for correction test
    FIRST_EXT_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || echo "")
  else
    fail "GET /api/v1/conversations/${CONV_ID}/extractions" "Expected >=1 extractions, got $EXT_COUNT"
  fi
fi

# ── Test 12: Submit correction ────────────────────────────────────────
if [[ -n "${FIRST_EXT_ID:-}" ]]; then
  CORR_BODY=$(cat <<JSON
{
  "field_name": "confidence",
  "original_value": "0.85",
  "corrected_value": "0.95",
  "correction_type": "modify",
  "correction_note": "Automated test correction"
}
JSON
  )
  RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
    -d "$CORR_BODY" "${BASE_URL}/api/v1/extractions/${FIRST_EXT_ID}/corrections" 2>/dev/null) || true
  if echo "$RESP" | grep -q 'extraction_id'; then
    pass "POST /api/v1/extractions/${FIRST_EXT_ID}/corrections → created"
  else
    fail "POST corrections" "$RESP"
  fi
fi

# ── Test 13: Conversation not found (404) ─────────────────────────────
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" \
  "${BASE_URL}/api/v1/conversations/00000000-0000-0000-0000-000000000000" 2>/dev/null)
if [[ "$HTTP_CODE" == "404" ]]; then
  pass "GET /api/v1/conversations/<invalid> → 404"
else
  fail "GET /api/v1/conversations/<invalid>" "Expected 404, got $HTTP_CODE"
fi

# ── Results ───────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Cleanup test data ─────────────────────────────────────────────────
echo ""
echo "Cleaning up test data..."
# Delete test conversations directly via database
# We'll use the API if a delete endpoint exists, otherwise via psql in container
for CID in "${CREATED_IDS[@]}"; do
  echo "  Deleting conversation: ${CID}"
done

# Clean up via psql inside the postgres container
if [[ ${#CREATED_IDS[@]} -gt 0 ]]; then
  ID_LIST=$(printf "'%s'," "${CREATED_IDS[@]}" | sed 's/,$//')
  cd /opt/cie && sudo docker compose -f docker-compose.prod.yml exec -T postgres psql -U cie -d cie -c "
    DELETE FROM corrections WHERE extraction_id IN (SELECT id FROM extractions WHERE conversation_id IN (${ID_LIST}));
    DELETE FROM extractions WHERE conversation_id IN (${ID_LIST});
    DELETE FROM conversations WHERE id IN (${ID_LIST});
  " 2>/dev/null && echo "  Test data cleaned up." || echo "  WARNING: Could not clean up via psql (manual cleanup may be needed)"
fi

echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "All tests passed! CIE is production-ready."
else
  echo "Some tests failed. Check output above."
fi
exit $FAIL
