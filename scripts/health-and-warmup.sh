#!/usr/bin/env bash
#
# Health check and warmup script for Render-deployed USO services.
# Run before E2E chat to avoid cold-start timeouts on free tier.
#
# Usage:
#   ./scripts/health-and-warmup.sh              # health + warmup only
#   ./scripts/health-and-warmup.sh --e2e         # also run chat E2E
#   ./scripts/health-and-warmup.sh --e2e --webhook  # also test webhook push
#
# Override URLs via env:
#   DISCOVERY_URL=... INTENT_URL=... ./scripts/health-and-warmup.sh
#   PARTNER_PORTAL_URL=... OMNICHANNEL_URL=... RESOURCING_URL=... PAYMENT_URL=...
#

set -e

# Default Render URLs (override with env vars)
DISCOVERY="${DISCOVERY_URL:-https://uso-discovery.onrender.com}"
INTENT="${INTENT_URL:-https://uso-intent.onrender.com}"
DURABLE="${DURABLE_URL:-https://uso-durable.onrender.com}"
ORCHESTRATOR="${ORCHESTRATOR_URL:-https://uso-orchestrator.onrender.com}"
WEBHOOK="${WEBHOOK_URL:-https://uso-webhook.onrender.com}"
PARTNER_PORTAL="${PARTNER_PORTAL_URL:-https://uso-partner-portal.onrender.com}"
OMNICHANNEL="${OMNICHANNEL_URL:-https://uso-omnichannel-broker.onrender.com}"
RESOURCING="${RESOURCING_URL:-https://uso-resourcing.onrender.com}"
PAYMENT="${PAYMENT_URL:-https://uso-payment.onrender.com}"

# Timeout for curl (seconds); Render cold starts can take 30-60s
TIMEOUT=90

run_e2e=false
run_webhook=false
for arg in "$@"; do
  case "$arg" in
    --e2e) run_e2e=true ;;
    --webhook) run_webhook=true ;;
  esac
done

echo "=== USO Health Check & Warmup ==="
echo "Core:"
echo "  Discovery:    $DISCOVERY"
echo "  Intent:       $INTENT"
echo "  Orchestrator: $ORCHESTRATOR"
echo "  Webhook:      $WEBHOOK"
echo "  Durable:      $DURABLE"
echo "Full implementation:"
echo "  Partner Portal:      $PARTNER_PORTAL"
echo "  Omnichannel Broker:  $OMNICHANNEL"
echo "  Re-Sourcing:         $RESOURCING"
echo "  Payment:             $PAYMENT"
echo ""

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
echo "  Warming Partner Portal..."
curl -sf --max-time "$TIMEOUT" "$PARTNER_PORTAL/health" > /dev/null || true
echo "  Warming Omnichannel Broker..."
curl -sf --max-time "$TIMEOUT" "$OMNICHANNEL/health" > /dev/null || true
echo "  Warming Re-Sourcing..."
curl -sf --max-time "$TIMEOUT" "$RESOURCING/health" > /dev/null || true
echo "  Warming Payment..."
curl -sf --max-time "$TIMEOUT" "$PAYMENT/health" > /dev/null || true
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
check_optional "Partner Portal"      "$PARTNER_PORTAL/health"
check_optional "Omnichannel Broker" "$OMNICHANNEL/health"
check_optional "Re-Sourcing"        "$RESOURCING/health"
check_optional "Payment"            "$PAYMENT/health"

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
    exit 1
  fi
  echo ""
fi

# --- Optional: Webhook push ---
if [ "$run_webhook" = true ]; then
  echo "--- Webhook push ---"
  resp=$(curl -sf --max-time "$TIMEOUT" -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/test-123" \
    -H "Content-Type: application/json" \
    -d '{"narrative": "Test update"}')
  if echo "$resp" | grep -q '"status"'; then
    echo "  ✓ Webhook OK"
  else
    echo "  ✗ Webhook failed"
    echo "$resp"
    exit 1
  fi
  echo ""
fi

echo "=== Done ==="
