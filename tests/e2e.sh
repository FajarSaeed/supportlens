#!/usr/bin/env bash
# =============================================================================
# SupportLens end-to-end test script
#
# Usage:
#   BASE_URL=http://localhost:8000 bash tests/e2e.sh
#
# Exits 0 on success, 1 on any failure.
# Designed to run in CI with no LLM API key (keyword fallback is active).
# =============================================================================

set -euo pipefail

BASE="${BASE_URL:-http://localhost:8000}"
PASS=0
FAIL=0

# ── helpers ───────────────────────────────────────────────────────────────────
green() { printf '\033[32m✓ %s\033[0m\n' "$*"; }
red()   { printf '\033[31m✗ %s\033[0m\n' "$*"; }

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    green "$label"
    PASS=$((PASS + 1))
  else
    red "$label — expected '$expected', got '$actual'"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    green "$label"
    PASS=$((PASS + 1))
  else
    red "$label — '$needle' not found in response"
    echo "  Response: $haystack"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local label="$1" needle="$2" haystack="$3"
  if ! echo "$haystack" | grep -q "$needle"; then
    green "$label"
    PASS=$((PASS + 1))
  else
    red "$label — '$needle' unexpectedly found in response"
    FAIL=$((FAIL + 1))
  fi
}

# ── wait for backend ──────────────────────────────────────────────────────────
echo "Waiting for backend at $BASE ..."
for i in $(seq 1 30); do
  if curl -sf "$BASE/health" > /dev/null 2>&1; then
    echo "Backend is up."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "Backend did not start in time."
    exit 1
  fi
  sleep 2
done

echo ""
echo "=== SupportLens E2E Tests ==="
echo ""

# ── Test 1: health endpoint ───────────────────────────────────────────────────
echo "--- Health ---"
HEALTH=$(curl -sf "$BASE/health")
assert_contains "health returns status field"   '"status"'   "$HEALTH"
assert_contains "health reports database check" '"database"' "$HEALTH"
assert_contains "health reports llm check"      '"llm"'      "$HEALTH"
assert_contains "health reports uptime"         '"uptime_seconds"' "$HEALTH"
# DB should be reachable
assert_contains "health db is ok" '"database":"ok"' "$(echo "$HEALTH" | tr -d ' ')"

# ── Test 2: analytics baseline ────────────────────────────────────────────────
echo ""
echo "--- Analytics baseline ---"
ANALYTICS_BEFORE=$(curl -sf "$BASE/analytics")
TOTAL_BEFORE=$(echo "$ANALYTICS_BEFORE" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_traces'])")
echo "  Traces before test: $TOTAL_BEFORE"

# ── Test 3: POST /chat ────────────────────────────────────────────────────────
echo ""
echo "--- Chat ---"
CHAT_RESP=$(curl -sf -X POST "$BASE/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I need a refund for my last invoice"}')
assert_contains "chat returns bot_response"      '"bot_response"'      "$CHAT_RESP"
assert_contains "chat returns response_time_ms"  '"response_time_ms"'  "$CHAT_RESP"

BOT_RESPONSE=$(echo "$CHAT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['bot_response'])")
RESP_MS=$(echo "$CHAT_RESP"      | python3 -c "import sys,json; print(json.load(sys.stdin)['response_time_ms'])")

# ── Test 4: POST /traces — creates a trace and classifies it ──────────────────
echo ""
echo "--- Create trace ---"
TRACE_RESP=$(curl -sf -X POST "$BASE/traces" \
  -H "Content-Type: application/json" \
  -d "{\"user_message\": \"I need a refund for my last invoice\", \"bot_response\": \"$BOT_RESPONSE\", \"response_time_ms\": $RESP_MS}")
assert_contains "trace has id"           '"id"'           "$TRACE_RESP"
assert_contains "trace has category"     '"category"'     "$TRACE_RESP"
assert_contains "trace has timestamp"    '"timestamp"'    "$TRACE_RESP"

TRACE_ID=$(echo "$TRACE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
TRACE_CAT=$(echo "$TRACE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['category'])")
echo "  Created trace id=$TRACE_ID category=$TRACE_CAT"

# ── Test 5: analytics total incremented ──────────────────────────────────────
echo ""
echo "--- Analytics increment ---"
ANALYTICS_AFTER=$(curl -sf "$BASE/analytics")
TOTAL_AFTER=$(echo "$ANALYTICS_AFTER" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_traces'])")
EXPECTED_TOTAL=$((TOTAL_BEFORE + 1))
assert_eq "analytics total incremented by 1" "$EXPECTED_TOTAL" "$TOTAL_AFTER"

# ── Test 6: GET /traces returns the new trace ─────────────────────────────────
echo ""
echo "--- List traces ---"
TRACES=$(curl -sf "$BASE/traces")
assert_contains "traces list contains new trace id" "$TRACE_ID" "$TRACES"

# ── Test 7: category filter — only matching traces returned ───────────────────
echo ""
echo "--- Category filter ---"
FILTERED=$(curl -sf "$BASE/traces?category=Billing")
# If the category is Billing, it should appear; if not, it should not appear
# Either way, no other categories should appear in a Billing-only filter
assert_not_contains "billing filter excludes Cancellation" '"Cancellation"' "$FILTERED"
assert_not_contains "billing filter excludes Refund"       '"Refund"'       "$FILTERED"

# ── Test 8: keyword search filter ────────────────────────────────────────────
echo ""
echo "--- Keyword search ---"
SEARCH_RESP=$(curl -sf "$BASE/traces?search=refund")
assert_contains "search for 'refund' returns results" '"id"' "$SEARCH_RESP"

# Search for something that definitely won't match
NO_MATCH=$(curl -sf "$BASE/traces?search=xyzzy_no_match_ever_12345")
assert_eq "search for nonsense returns empty array" "[]" "$NO_MATCH"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
echo "================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
