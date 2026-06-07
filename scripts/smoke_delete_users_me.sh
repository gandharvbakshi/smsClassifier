#!/usr/bin/env bash
# Smoke test for DELETE /api/users/me
#
# Prerequisites:
#   1. Start the server in a separate terminal:
#        uvicorn backend.scripts.android_backend_server:app --port 8765
#      (run from D:\Projects\SMS datasets and project\ with required env vars set)
#   2. Ensure curl is available.
#
# Usage:
#   bash scripts/smoke_delete_users_me.sh

set -euo pipefail

BASE="http://localhost:8765/api"

echo "=== Seeding two rows for installId=test-A ==="
curl -sf -X POST "$BASE/feedback" \
  -H "Content-Type: application/json" \
  -H "User-Agent: okhttp/4.12.0" \
  -d '{"installId":"test-A","appVersionCode":1,"appVersionName":"1.0","sender":"TESTBANK","body":"Your OTP is 123456","clientCreatedAt":1700000000000}' \
  | jq .

curl -sf -X POST "$BASE/feedback" \
  -H "Content-Type: application/json" \
  -H "User-Agent: okhttp/4.12.0" \
  -d '{"installId":"test-A","appVersionCode":1,"appVersionName":"1.0","sender":"TESTBANK","body":"Your OTP is 654321","clientCreatedAt":1700000001000}' \
  | jq .

echo ""
echo "=== Seeding one row for installId=test-B ==="
curl -sf -X POST "$BASE/feedback" \
  -H "Content-Type: application/json" \
  -H "User-Agent: okhttp/4.12.0" \
  -d '{"installId":"test-B","appVersionCode":1,"appVersionName":"1.0","sender":"TESTBANK","body":"Your OTP is 999999","clientCreatedAt":1700000002000}' \
  | jq .

echo ""
echo "=== DELETE test-A with correct bearer — expect 204 ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "$BASE/users/me?installId=test-A" \
  -H "Authorization: Bearer test-A")
echo "HTTP $STATUS"
[ "$STATUS" = "204" ] && echo "PASS" || { echo "FAIL (expected 204)"; exit 1; }

echo ""
echo "=== DELETE test-A again (idempotent) — expect 204 ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "$BASE/users/me?installId=test-A" \
  -H "Authorization: Bearer test-A")
echo "HTTP $STATUS"
[ "$STATUS" = "204" ] && echo "PASS" || { echo "FAIL (expected 204)"; exit 1; }

echo ""
echo "=== DELETE test-A with WRONG bearer — expect 401 ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "$BASE/users/me?installId=test-A" \
  -H "Authorization: Bearer wrong-token")
echo "HTTP $STATUS"
[ "$STATUS" = "401" ] && echo "PASS" || { echo "FAIL (expected 401)"; exit 1; }

echo ""
echo "=== DELETE with missing installId — expect 400 or 422 ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "$BASE/users/me" \
  -H "Authorization: Bearer test-B")
echo "HTTP $STATUS"
([ "$STATUS" = "400" ] || [ "$STATUS" = "422" ]) && echo "PASS" || { echo "FAIL (expected 400 or 422)"; exit 1; }

FEEDBACK_FILE="${FEEDBACK_LOG_DIR:-/tmp/sms_feedback}/feedback.jsonl"
echo ""
echo "=== Inspecting JSONL (only test-B rows should remain) ==="
if [ -f "$FEEDBACK_FILE" ]; then
  echo "File: $FEEDBACK_FILE"
  echo "Remaining rows:"
  cat "$FEEDBACK_FILE"
  REMAINING_A=$(grep -c '"installId":"test-A"' "$FEEDBACK_FILE" || true)
  REMAINING_B=$(grep -c '"installId":"test-B"' "$FEEDBACK_FILE" || true)
  echo ""
  echo "test-A rows remaining: $REMAINING_A  (expected 0)"
  echo "test-B rows remaining: $REMAINING_B  (expected 1)"
  [ "$REMAINING_A" = "0" ] && [ "$REMAINING_B" = "1" ] && echo "PASS" || { echo "FAIL"; exit 1; }
else
  echo "JSONL file not found at $FEEDBACK_FILE — local storage not enabled or wrong path."
fi

echo ""
echo "All smoke tests passed."
