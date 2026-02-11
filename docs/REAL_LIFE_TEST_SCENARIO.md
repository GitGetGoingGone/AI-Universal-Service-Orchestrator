# Real-Life Test Scenario: Multi-Vendor Task Queue, HubNegotiator & Hybrid Response

End-to-end test of Phase 2 modules using a realistic use case: **Customer orders a gift bundle (flowers + chocolates) from two vendors, needs assembly and delivery from a hub, and contacts support.**

---

## Staging / Deployed Services

Use these base URLs when testing on Render staging:

| Service | Staging URL |
|---------|-------------|
| Discovery | `https://uso-discovery.onrender.com` |
| Task Queue | `https://uso-task-queue.onrender.com` |
| Hub Negotiator | `https://uso-hub-negotiator.onrender.com` |
| Hybrid Response | `https://uso-hybrid-response.onrender.com` |
| Reverse Logistics | `https://uso-reverse-logistics.onrender.com` (deploy if needed) |
| Virtual Proofing | `https://uso-proofing.onrender.com` (deploy if needed) |
| Portal | Your Vercel deployment URL |

**How to test on staging**:

1. **Manifest (Module 3)**: `curl -s https://uso-discovery.onrender.com/api/v1/manifest | jq`
2. **Task Queue, HubNegotiator, Hybrid Response**: Use the seed IDs from Step 1.1 and run the curl commands in Step 2–4.
3. **Portal**:
   - Partner: Sign in with partner email → Tasks, Hub RFPs.
   - Platform: Sign in as platform admin → Dashboard, Escalations, RFPs.
4. **Order → Task Queue**: Set `TASK_QUEUE_SERVICE_URL` on discovery service; create order via checkout → tasks auto-created.

For local testing, use `http://localhost:8xxx` (port per service).

---

## Scenario: "Gift bundle for Saturday delivery"

1. **Customer** orders flowers from Flower Shop + chocolates from Chocolate Co. (multi-vendor bundle).
2. **Platform** creates an order with order_legs (one per vendor).
3. **Task Queue** assigns tasks to each vendor in sequence (flowers first, then chocolates).
4. **HubNegotiator** creates an RFP for assembly/delivery; hubs bid; platform selects winner.
5. **Customer** sends messages—routine ("Where is my order?") vs escalatable ("Item arrived damaged").
6. **Hybrid Response** classifies and routes: routine → AI, dispute/damage → human escalation.

---

## Prerequisites

- Supabase project with migrations applied (including `20240128100003_task_queue_hub_negotiator_hybrid.sql`)
- Deployed services: Task Queue, Hub Negotiator, Hybrid Response (see [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md))
- Seed data: Run `supabase/seed.sql` then `supabase/seed_phase2_scenario.sql` for pre-defined IDs (see Step 1.1)

---

## Step 1: Set up test data

### 1.1 Get IDs (quick path with seed)

If you ran `supabase/seed.sql` and `supabase/seed_phase2_scenario.sql`, use these fixed IDs:

| Variable | UUID |
|----------|------|
| `ORDER_UUID` | `e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a50` |
| `BUNDLE_UUID` | `d1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40` |
| `FLOWER_PARTNER_UUID` | `b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22` |
| `CHOCOLATE_PARTNER_UUID` | `b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23` |
| `HUB_PARTNER_UUID` | `b3eebc99-9c0b-4ef8-bb6d-6bb9bd380a24` |
| `USER_UUID` | `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11` |

**Otherwise**, create data manually in Supabase SQL Editor (see original Step 1.1 in git history or create partners, bundle, bundle_legs, order, order_legs).

---

## Step 1.5: AI-First Discoverability (Module 3)

*Run this anytime to verify manifest and action models for AI agents.*

```bash
export DISCOVERY="${DISCOVERY:-https://uso-discovery.onrender.com}"

# Manifest (ACP-style platform manifest for AI agents)
curl -s "$DISCOVERY/api/v1/manifest" | jq .

# Well-known agent manifest (same content, discoverable by convention)
curl -s "$DISCOVERY/.well-known/agent-manifest" | jq .

# Expected: manifest_version, platform_id, platform_name, discovery_endpoint, capabilities, action_models, offline_discovery
# action_models should include: discover_products, create_order, modify_order, cancel_order, track_order
```

---

## Step 1.6: Reverse Logistics (Module 17)

*Requires deployed reverse-logistics-service. Use ORDER_UUID, FLOWER_PARTNER_UUID from Step 1.1.*

```bash
export REVERSE_LOGISTICS="${REVERSE_LOGISTICS:-https://uso-reverse-logistics.onrender.com}"

# Create return request
curl -s -X POST "$REVERSE_LOGISTICS/api/v1/returns" -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER_UUID",
    "partner_id": "FLOWER_PARTNER_UUID",
    "reason": "damaged",
    "reason_detail": "Flowers arrived wilted",
    "refund_amount_cents": 2500
  }' | jq .
# Note: RETURN_UUID

# List returns
curl -s "$REVERSE_LOGISTICS/api/v1/returns?order_id=ORDER_UUID" | jq .

# Approve return
curl -s -X POST "$REVERSE_LOGISTICS/api/v1/returns/RETURN_UUID/approve" | jq .

# Process refund
curl -s -X POST "$REVERSE_LOGISTICS/api/v1/returns/RETURN_UUID/refund" | jq .

# Restock (requires product_id from order)
curl -s -X POST "$REVERSE_LOGISTICS/api/v1/returns/RETURN_UUID/restock" -H "Content-Type: application/json" \
  -d '{"product_id": "PRODUCT_UUID", "quantity": 1}' | jq .
```

---

## Step 2: Multi-Vendor Task Queue (Module 11)

Replace `ORDER_UUID` and `PARTNER_UUID` with real ids from Step 1.

```bash
export TASK_QUEUE="https://uso-task-queue.onrender.com"   # or your URL

# 2.1 Create tasks for the order (idempotent; call again returns same tasks)
curl -s -X POST "$TASK_QUEUE/api/v1/orders/ORDER_UUID/tasks" | jq .

# Expected: Array of tasks, one per order_leg, ordered by task_sequence (1, 2)
# Each task has: id, order_id, order_leg_id, partner_id, task_sequence, status: "pending"

# 2.2 Flower vendor sees their task (first in sequence)
curl -s "$TASK_QUEUE/api/v1/tasks?partner_id=FLOWER_PARTNER_UUID&status=pending" | jq .

# Chocolate vendor sees nothing yet (earlier task must complete first)
curl -s "$TASK_QUEUE/api/v1/tasks?partner_id=CHOCOLATE_PARTNER_UUID&status=pending" | jq .

# 2.3 Flower vendor starts and completes task
TASK_1_UUID="<first-task-id-from-step-2.1>"
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/$TASK_1_UUID/start?partner_id=FLOWER_PARTNER_UUID" | jq .
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/$TASK_1_UUID/complete?partner_id=FLOWER_PARTNER_UUID" \
  -H "Content-Type: application/json" -d '{"metadata":{"notes":"Flowers delivered to hub"}}' | jq .

# 2.4 Now Chocolate vendor sees their task
curl -s "$TASK_QUEUE/api/v1/tasks?partner_id=CHOCOLATE_PARTNER_UUID&status=pending" | jq .

# 2.5 Chocolate vendor completes their task
TASK_2_UUID="<second-task-id>"
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/$TASK_2_UUID/start?partner_id=CHOCOLATE_PARTNER_UUID" | jq .
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/$TASK_2_UUID/complete?partner_id=CHOCOLATE_PARTNER_UUID" | jq .
```

---

## Step 3: HubNegotiator & Bidding (Module 10)

Replace `ORDER_UUID`, `BUNDLE_UUID`, `HUB_PARTNER_UUID` with real ids.

```bash
export HUB_NEGOTIATOR="https://uso-hub-negotiator.onrender.com"

# 3.1 Create RFP for assembly and delivery
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps" -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER_UUID",
    "bundle_id": "BUNDLE_UUID",
    "request_type": "assembly",
    "title": "Assemble and deliver gift bundle",
    "description": "Bundle flowers + chocolates, wrap, deliver to customer",
    "deadline": "2026-02-08T18:00:00Z",
    "compensation_cents": 2500
  }' | jq .
# Note: RFP_UUID

# 3.2 List open RFPs
curl -s "$HUB_NEGOTIATOR/api/v1/rfps?status=open" | jq .

# 3.3 Hub submits bid
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/RFP_UUID/bids" -H "Content-Type: application/json" \
  -d '{
    "hub_partner_id": "HUB_PARTNER_UUID",
    "amount_cents": 2200,
    "proposed_completion_at": "2026-02-08T14:00:00Z"
  }' | jq .
# Note: BID_UUID

# 3.4 (Optional) Add second hub bid for competition
# Another hub partner could submit a different bid.

# 3.5 Select winning bid
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/RFP_UUID/select-winner" -H "Content-Type: application/json" \
  -d '{"bid_id": "BID_UUID"}' | jq .

# 3.6 Add hub capacity (for capacity matching)
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/hub-capacity" -H "Content-Type: application/json" \
  -d '{
    "partner_id": "HUB_PARTNER_UUID",
    "available_from": "2026-02-01T00:00:00Z",
    "available_until": "2026-02-28T23:59:59Z",
    "capacity_slots": 10
  }' | jq .
```

---

## Step 4: Hybrid Response Logic (Module 13)

```bash
export HYBRID_RESPONSE="https://uso-hybrid-response.onrender.com"

# 4.1 Routine message (route → AI)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{
    "conversation_ref": "conv-gift-001",
    "message_content": "Where is my order? I need it by Saturday."
  }' | jq .
# Expected: {"classification": "routine", "route": "ai", "support_escalation_id": null}

# 4.2 Routine: tracking query
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{
    "conversation_ref": "conv-gift-001",
    "message_content": "What is the delivery status and ETA?"
  }' | jq .
# Expected: route: "ai"

# 4.3 Escalatable: damage complaint (route → human)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{
    "conversation_ref": "conv-gift-001",
    "message_content": "My order arrived damaged. The box was crushed and chocolates are broken. I want a refund."
  }' | jq .
# Expected: {"classification": "physical_damage" or "dispute", "route": "human", "support_escalation_id": "<uuid>"}

# 4.4 List pending escalations
curl -s "$HYBRID_RESPONSE/api/v1/escalations?status=pending" | jq .

# 4.5 Assign escalation to support agent (replace ESCALATION_UUID, USER_UUID)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/escalations/ESCALATION_UUID/assign" -H "Content-Type: application/json" \
  -d '{"assigned_to": "USER_UUID"}' | jq .

# 4.6 Resolve escalation
curl -s -X POST "$HYBRID_RESPONSE/api/v1/escalations/ESCALATION_UUID/resolve" -H "Content-Type: application/json" \
  -d '{"resolution_notes": "Refund processed. Replacement sent."}' | jq .
```

---

## Step 5: One-shot script (copy-paste)

After you have `ORDER_UUID`, `FLOWER_PARTNER_UUID`, `CHOCOLATE_PARTNER_UUID`, `HUB_PARTNER_UUID` from your DB:

```bash
TASK_QUEUE="${TASK_QUEUE:-https://uso-task-queue.onrender.com}"
HUB_NEGOTIATOR="${HUB_NEGOTIATOR:-https://uso-hub-negotiator.onrender.com}"
HYBRID_RESPONSE="${HYBRID_RESPONSE:-https://uso-hybrid-response.onrender.com}"

ORDER_UUID="your-order-uuid"
FLOWER_PARTNER_UUID="your-flower-partner-uuid"
CHOCOLATE_PARTNER_UUID="your-chocolate-partner-uuid"
HUB_PARTNER_UUID="your-hub-partner-uuid"

echo "=== Task Queue ==="
curl -s -X POST "$TASK_QUEUE/api/v1/orders/$ORDER_UUID/tasks" | jq '. | length' 
echo "Tasks per partner:"
curl -s "$TASK_QUEUE/api/v1/tasks?partner_id=$FLOWER_PARTNER_UUID&status=pending" | jq '. | length'

echo "=== HubNegotiator ==="
RFP=$(curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps" -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_UUID\",\"request_type\":\"assembly\",\"title\":\"Test RFP\",\"deadline\":\"2026-03-01T18:00:00Z\",\"compensation_cents\":2000}")
echo "$RFP" | jq '{id, status}'
RFP_ID=$(echo "$RFP" | jq -r '.id')
BID=$(curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/$RFP_ID/bids" -H "Content-Type: application/json" \
  -d "{\"hub_partner_id\":\"$HUB_PARTNER_UUID\",\"amount_cents\":1800}")
echo "$BID" | jq '{id, status}'
BID_ID=$(echo "$BID" | jq -r '.id')
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/$RFP_ID/select-winner" -H "Content-Type: application/json" \
  -d "{\"bid_id\":\"$BID_ID\"}" | jq '{status, winning_bid_id}'

echo "=== Hybrid Response ==="
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{"conversation_ref":"t","message_content":"Where is my order?"}' | jq .
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{"conversation_ref":"t","message_content":"It arrived damaged, I want a refund"}' | jq .
```

---

## Step 5.5: Admin Command Center (Module 18)

*Requires platform admin access. Test on staging portal.*

1. Log in as platform admin at `/platform`.
2. Dashboard: Verify metrics (Partners, Pending Approvals, Active Bundles, Orders, Revenue, Pending Escalations, Vendor Tasks Pending, Open RFPs).
3. Period filter: Change to "Last 7 days", "Last 30 days", "All time" and confirm counts update.
4. Escalations: Go to `/platform/escalations`. Filter by pending/assigned/resolved. For a pending escalation, click "Assign to me", then add resolution notes and "Resolve".
5. Export: Click "Export Partners", "Export Orders", "Export Escalations" and confirm CSV downloads.

*API (if needed):*
```bash
# Platform stats (requires platform admin auth)
curl -s -H "Cookie: ..." "$PORTAL_URL/api/platform/stats?period=7d" | jq .

# Export (requires platform admin auth)
curl -s -H "Cookie: ..." "$PORTAL_URL/api/platform/reports/export?type=partners" -o partners.csv
```

---

## Checklist summary

| Module | Flow | Pass condition |
|--------|------|----------------|
| AI-First Discoverability (3) | GET manifest → action_models, offline_discovery | 200, manifest_version, action_models with discover_products, create_order, etc. |
| Admin Command Center (18) | Dashboard, period filter, escalations assign/resolve, export | Metrics visible; period filter works; assign/resolve succeeds; CSV downloads |
| Reverse Logistics (17) | Create return → Approve → Refund → Restock | Return created; approve; refund processed; restock event created |
| Virtual Proofing (8) | Create proof → Generate (DALL-E) → Approve/Reject | Proof created; generate sets proof_ready; approve/reject |
| Task Queue | Create tasks → Vendor 1 sees task → Start/Complete → Vendor 2 sees task | Tasks created in leg order; partner sees only next task when prior complete |
| HubNegotiator | Create RFP → Bids → Select winner → Add capacity | RFP closed, winning_bid_id set; capacity record created |
| Hybrid Response | Routine message → AI; Damage/dispute → Human + escalation | `route: "ai"` for routine; `route: "human"` with `support_escalation_id` for dispute/damage |

---

## Integration with other flows

- **Order → Task Queue**: When checkout creates an order (`POST /api/v1/checkout`), the discovery service auto-calls the Task Queue to create vendor tasks. Set `TASK_QUEUE_SERVICE_URL` in discovery service env.
- **Omnichannel Broker**: Partner responses (accept/reject) could trigger Re-Sourcing; HubNegotiator RFPs could be created when a hub is needed.
- **Webhook**: Classify-and-route could be called before sending an AI response; if `route: "human"`, pause AI and notify support.

See [TESTING_RENDER_AND_PORTAL.md § 8b](./TESTING_RENDER_AND_PORTAL.md#8b-phase-2-modules-task-queue-hubnegotiator-hybrid-response) for API-level tests.
