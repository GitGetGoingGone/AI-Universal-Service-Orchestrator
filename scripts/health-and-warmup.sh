#!/usr/bin/env bash
#
# Health check and warmup script for Render-deployed USO services.
# Run before E2E chat to avoid cold-start timeouts on free tier.
#
# Usage:
#   ./scripts/health-and-warmup.sh              # health + warmup only
#   ./scripts/health-and-warmup.sh --e2e         # also run chat E2E
#   ./scripts/health-and-warmup.sh --e2e --webhook  # also test webhook push
#   ./scripts/health-and-warmup.sh --every=10    # run every 10 minutes until terminated (keep services active)
#
# Override URLs via env:
#   DISCOVERY_URL=... INTENT_URL=... CHATGPT_APP_URL=... ./scripts/health-and-warmup.sh
#   OMNICHANNEL_URL=... RESOURCING_URL=... PAYMENT_URL=...
#

set -e

# Default Render URLs (override with env vars)
DISCOVERY="${DISCOVERY_URL:-https://uso-discovery.onrender.com}"
INTENT="${INTENT_URL:-https://uso-intent.onrender.com}"
DURABLE="${DURABLE_URL:-https://uso-durable.onrender.com}"
ORCHESTRATOR="${ORCHESTRATOR_URL:-https://uso-orchestrator.onrender.com}"
WEBHOOK="${WEBHOOK_URL:-https://uso-webhook.onrender.com}"
OMNICHANNEL="${OMNICHANNEL_URL:-https://uso-omnichannel-broker.onrender.com}"
RESOURCING="${RESOURCING_URL:-https://uso-resourcing.onrender.com}"
PAYMENT="${PAYMENT_URL:-https://uso-payment.onrender.com}"
TASK_QUEUE="${TASK_QUEUE_URL:-https://uso-task-queue.onrender.com}"
HUB_NEGOTIATOR="${HUB_NEGOTIATOR_URL:-https://uso-hub-negotiator.onrender.com}"
HYBRID_RESPONSE="${HYBRID_RESPONSE_URL:-https://uso-hybrid-response.onrender.com}"
CHATGPT_APP="${CHATGPT_APP_URL:-https://uso-chatgpt-app.onrender.com}"

# Timeout for curl (seconds); Render cold starts can take 30-60s
TIMEOUT=90

run_e2e=false
run_webhook=false
every_minutes=0
for arg in "$@"; do
  case "$arg" in
    --e2e) run_e2e=true ;;
    --webhook) run_webhook=true ;;
    --loop) every_minutes="${HEALTH_LOOP_MINUTES:-10}" ;;
    --every=*) every_minutes="${arg#--every=}" ;;
  esac
done
if [ -z "$every_minutes" ] && [ -n "${HEALTH_LOOP_MINUTES:-}" ] && [ "${HEALTH_LOOP_MINUTES:-0}" -gt 0 ] 2>/dev/null; then
  every_minutes="$HEALTH_LOOP_MINUTES"
fi

echo "=== USO Health Check & Warmup ==="
echo "Core:"
echo "  Discovery:    $DISCOVERY"
echo "  Intent:       $INTENT"
echo "  Orchestrator: $ORCHESTRATOR"
echo "  Webhook:      $WEBHOOK"
echo "  Durable:      $DURABLE"
echo "Full implementation:"
echo "  Omnichannel Broker:  $OMNICHANNEL"
echo "  Re-Sourcing:         $RESOURCING"
echo "  Payment:             $PAYMENT"
echo "  Task Queue:          $TASK_QUEUE"
echo "  Hub Negotiator:      $HUB_NEGOTIATOR"
echo "  Hybrid Response:     $HYBRID_RESPONSE"
echo "  ChatGPT App (MCP):   $CHATGPT_APP"
echo ""

do_cycle() {
# --- Warmup first (wake services from cold sleep before health checks) ---
echo "--- Warmup (avoid cold-start timeouts) ---"
echo "  Warming Discovery..."
curl -sf --max-time "$TIMEOUT" "$DISCOVERY/health" > /dev/null || true
echo "  Warming Intent..."
curl -sf --max-time "$TIMEOUT" "$INTENT/health" > /dev/null || true
echo "  Warming Orchestrator..."
curl -sf --max-time "$TIMEOUT" "$ORCHESTRATOR/health" > /dev/null || true
echo "  Warming Webhook..."
curl -sf --max-time "$TIMEOUT" "$WEBHOOK/health" > /dev/null || true
echo "  Warming Durable (Docker + Azure Functions has longest cold start)..."
curl -sf --max-time "$TIMEOUT" -X POST -H "Content-Type: application/json" -d '{}' "$DURABLE/api/orchestrators/base_orchestrator" > /dev/null || true
echo "  Warming Omnichannel Broker..."
curl -sf --max-time "$TIMEOUT" "$OMNICHANNEL/health" > /dev/null || true
echo "  Warming Re-Sourcing..."
curl -sf --max-time "$TIMEOUT" "$RESOURCING/health" > /dev/null || true
echo "  Warming Payment..."
curl -sf --max-time "$TIMEOUT" "$PAYMENT/health" > /dev/null || true
echo "  Warming Task Queue..."
curl -sf --max-time "$TIMEOUT" "$TASK_QUEUE/health" > /dev/null || true
echo "  Warming Hub Negotiator..."
curl -sf --max-time "$TIMEOUT" "$HUB_NEGOTIATOR/health" > /dev/null || true
echo "  Warming Hybrid Response..."
curl -sf --max-time "$TIMEOUT" "$HYBRID_RESPONSE/health" > /dev/null || true
echo "  Warming ChatGPT App (MCP)..."
curl -sf --max-time "$TIMEOUT" "$CHATGPT_APP/health" > /dev/null || curl -sf --max-time "$TIMEOUT" "$CHATGPT_APP/" > /dev/null || true
echo "  Done."
echo ""

# --- Health checks ---
echo "--- Health checks (core) ---"
check() {
  local name="$1"
  local url="$2"
  if curl -sf --max-time "$TIMEOUT" "$url" > /dev/null 2>&1; then
    echo "  ✓ $name"
    return 0
  fi
  echo "  ✗ $name ($url)"
  return 1
}

check_post() {
  local name="$1"
  local url="$2"
  local data="${3:-{}}"
  if curl -sf --max-time "$TIMEOUT" -X POST -H "Content-Type: application/json" -d "$data" "$url" > /dev/null 2>&1; then
    echo "  ✓ $name"
    return 0
  fi
  echo "  ✗ $name ($url)"
  return 1
}

check_optional() {
  local name="$1"
  local url="$2"
  if curl -sf --max-time "$TIMEOUT" "$url" > /dev/null 2>&1; then
    echo "  ✓ $name"
    return 0
  fi
  echo "  ✗ $name ($url) [optional]"
  return 0
}

check "Discovery"    "$DISCOVERY/health"
check "Intent"       "$INTENT/health"
check "Orchestrator" "$ORCHESTRATOR/health"
check "Webhook"      "$WEBHOOK/health"
check_post "Durable" "$DURABLE/api/orchestrators/base_orchestrator" '{}'

echo "--- Health checks (full implementation) ---"
check_optional "Omnichannel Broker" "$OMNICHANNEL/health"
check_optional "Re-Sourcing"        "$RESOURCING/health"
check_optional "Payment"            "$PAYMENT/health"
check_optional "Task Queue"         "$TASK_QUEUE/health"
check_optional "Hub Negotiator"     "$HUB_NEGOTIATOR/health"
check_optional "Hybrid Response"    "$HYBRID_RESPONSE/health"
check_optional "ChatGPT App (MCP)"  "$CHATGPT_APP/health"

# --- Optional: Chat E2E ---
if [ "$run_e2e" = true ]; then
  echo "--- Chat E2E ---"
  resp=$(curl -sf --max-time "$TIMEOUT" -X POST "$ORCHESTRATOR/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"text": "find flowers"}')
  if echo "$resp" | grep -q '"summary"'; then
    echo "  ✓ Chat OK"
    echo "$resp" | head -c 200
    echo "..."
  else
    echo "  ✗ Chat failed"
    echo "$resp"
    return 1
  fi
  echo ""
fi

# --- Optional: Webhook push ---
if [ "$run_webhook" = true ]; then
  echo "--- Webhook push ---"
  resp=$(curl -s --max-time "$TIMEOUT" -w "\n%{http_code}" -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/test-123" \
    -H "Content-Type: application/json" \
    -d '{"narrative": "Test update"}')
  http_code=$(echo "$resp" | tail -n1)
  body=$(echo "$resp" | sed '$d')
  if echo "$body" | grep -q '"status"'; then
    echo "  ✓ Webhook OK"
  elif [ "$http_code" = "503" ] && echo "$body" | grep -q "not configured"; then
    echo "  ○ Webhook push skipped (CHATGPT_WEBHOOK_URL not set)"
  else
    echo "  ✗ Webhook failed (HTTP $http_code)"
    echo "$body"
    return 1
  fi
  echo ""
fi

}

if [ -n "$every_minutes" ] && [ "$every_minutes" -gt 0 ] 2>/dev/null; then
  echo ">>> Running every ${every_minutes} minute(s) until you press Ctrl+C."
  echo ""
  trap 'echo ""; echo "Stopped."; exit 0' INT TERM
  while true; do
    do_cycle || true
    echo "=== Done at $(date). Next run in ${every_minutes} minute(s). ==="
    echo ""
    sleep "$((every_minutes * 60))"
  done
fi

do_cycle
ret=$?
[ "$ret" -eq 0 ] && echo "=== Done ==="
exit "$ret"
