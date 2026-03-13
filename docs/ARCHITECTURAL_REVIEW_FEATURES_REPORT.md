# Architectural Review: Implemented Features Report

**Document version:** 1.0  
**Purpose:** Full report of implemented features for architectural review, with an end-to-end use case covering bundle, customization, partner change, payment, re-sourcing, and task queue.

---

## 1. Executive Summary

The AI Universal Service Orchestrator (USO) platform implements a **chat-first, multi-vendor commerce** flow. All core services are **implemented with real logic** (no placeholders): intent resolution (LLM + heuristic fallback), discovery (Scout, composite bundles, experience tags), bundle lifecycle, commitment precheck (Shopify/local), atomic checkout (Stripe), partner change requests (Omnichannel Broker), autonomous re-sourcing on rejection, task queue, webhook push (ChatGPT/Gemini/WhatsApp), and Hub Negotiator (RFP/bidding). Admin config, platform config, and partner portal are implemented. This report maps the 19-module core to services and describes one full lifecycle use case.

---

## 2. Architecture Layers & Services

| Layer | Components |
|-------|------------|
| **Frontend** | Next.js (portal, uso-unified-chat, assistant-ui-chat), embed chat |
| **API / Gateway** | Orchestrator (single chat endpoint + product/checkout proxies), direct service APIs |
| **Microservices** | intent-service, discovery-service, orchestrator-service, payment-service, webhook-service, omnichannel-broker-service, re-sourcing-service, task-queue-service, hub-negotiator-service, hybrid-response-service, proofing-service, reverse-logistics-service |
| **Durable / Async** | Durable Orchestrator (Azure Functions): standing intent, wait-for-event, status narrator → webhook push |
| **Data** | Supabase (PostgreSQL + pgvector), Stripe |
| **External** | UCP/ACP, Stripe, Azure OpenAI / LLM providers, Twilio WhatsApp (optional) |

---

## 3. Core Module Map (19 Modules) vs Implementation

| # | Module | Service(s) | Status |
|---|--------|------------|--------|
| 1 | Scout Engine | discovery-service (scout_engine, UCP/ACP, semantic search, manifest cache) | Implemented |
| 2 | Legacy Adapter | discovery-service (adapters, protocols) | Implemented |
| 3 | AI Discoverability | discovery-service, intent-service (LLM + heuristic) | Implemented |
| 4 | Intent Resolver | intent-service (LLM + configurable heuristic fallback) | Implemented |
| 5 | Time-Chain Resolver | orchestrator (experience_session, commitment flow, order_legs) | Implemented |
| 6 | Autonomous Re-Sourcing | re-sourcing-service (recovery trigger, SLA execute, Discovery + commitment cancel) | Implemented |
| 7 | Premium Registry | discovery-service, internal_agent_registry (Supabase) | Implemented |
| 8 | Virtual Proofing | proofing-service | Implemented |
| 9 | Partner Portal | apps/portal (partner + platform admin) | Implemented |
| 10 | Hub Negotiator | hub-negotiator-service (RFP, bids, capacity) | Implemented |
| 11 | Multi-Vendor Task Queue | task-queue-service (tasks from order_legs, start/complete) | Implemented |
| 12 | Multi-Party Support | omnichannel-broker, experience_session_legs | Implemented |
| 13 | Hybrid Response | hybrid-response-service (classify + respond) | Implemented |
| 14 | Status Narrator | durable-orchestrator (status updates), webhook-service (push to chat) | Implemented |
| 15 | Atomic Multi-Checkout | payment-service (commitment precheck, PaymentIntent, Stripe webhook) | Implemented |
| 16 | Transaction & Escrow | payment-service (Stripe), orders/order_legs | Implemented |
| 17 | Reverse Logistics | reverse-logistics-service (returns) | Implemented |
| 18 | Admin Command Center | apps/portal platform config, kill switch, platform config API | Implemented |
| 19 | Curation & Promotion | discovery (experience tags, product mix, composite bundles), portal config | Implemented |

Additional capabilities: **Standing Intents** (orchestrator + durable), **Omnichannel Message Broker** (partner change requests, accept/reject, trigger re-sourcing), **Link Account** (Clerk ↔ platform_user_id, WhatsApp).

---

## 4. Implemented Features by Area

### 4.1 Intent & Discovery

- **Intent resolution:** LLM (configurable provider) or heuristic fallback; configurable keywords/patterns via Platform Config → Intent heuristics (no hardcoded domain terms in code).
- **Composite intents:** Date night, picnic, birthday party, baby shower (pattern → search_queries, experience_name, proposed_plan) from config.
- **Discovery:** Semantic + filters (experience tags, partner, price); composite bundle discovery (products per category, product mix, experience_flow_rules).
- **Adaptive Cards:** Product cards, bundle cards, checkout cards; “Add to bundle”, “Checkout”, “View bundle”, “Request change” actions.
- **Experience sessions & legs:** Thread-scoped session; legs per partner/product for commitment and SLA.

### 4.2 Bundle Lifecycle

- **Create bundle:** First “Add to bundle” creates draft bundle (Supabase `bundles` + `bundle_legs`).
- **Add to bundle:** Single product (`POST /api/v1/bundle/add`) or bulk (`POST /api/v1/bundle/add-bulk`) with optional fulfillment fields.
- **View bundle:** Get bundle by ID with legs and total.
- **Remove / replace:** Remove item by `bundle_leg` id; replace leg with another product (refinement).
- **Customization / fulfillment:** Required fulfillment fields per bundle; modal in chat for delivery/pickup details; stored with bulk add and used in commitment/order.

### 4.3 Checkout & Payment (Atomic Multi-Checkout)

- **Commitment precheck:** `POST /api/v1/commitment/precheck` (bundle_id + StandardizedShipping). Per-partner commitment provider (Shopify draft order, local); returns TCO (total, tax, shipping) and reservation_id per partner.
- **Create PaymentIntent:** With or without commitment_breakdown; Stripe metadata can carry thread_id and commitment_breakdown for webhook handshake.
- **Stripe webhook:** On payment_intent.succeeded, complete Shopify drafts (or local), create order and order_legs, update experience_session_legs.
- **Checkout Session:** Redirect-based Stripe Checkout; checkout-session-from-order for existing order.
- **Sponsorship:** Create sponsorship PaymentIntent; product sponsorship flows in portal.

### 4.4 Order & Post-Payment

- **Order creation:** From bundle (discovery-service) or via payment webhook (payment-service + orchestrator/discovery for order_legs).
- **Order legs:** One per bundle_leg; external_order_id (e.g. Shopify draft/order), vendor_type, partner_id.
- **Task queue:** `POST /api/v1/orders/{order_id}/tasks` creates vendor_tasks from order_legs (sequence from bundle_legs). Partners list/start/complete tasks.

### 4.5 Partner Change Request & Re-Sourcing

- **Change request:** Orchestrator or client calls `POST /change-request` → Omnichannel Broker `POST /api/v1/change-request`. Creates negotiation; **notifies partner only when channel is API** (POST to partner webhook URL). When channel is `whatsapp` or demo, negotiation is created but no outbound WhatsApp or in-portal notification is sent.
- **Partner response:** Partner calls `POST /webhooks/partner` (accept/reject). On **reject**, Omnichannel Broker calls Re-Sourcing `POST /api/v1/recovery/trigger`.
- **Re-sourcing:** Cancel external order (e.g. Shopify) and our order_leg; discover alternatives (exclude rejecting partner); create autonomous_recovery record; present alternatives to user (e.g. via chat).
- **SLA execute:** User confirms alternative → `POST /api/v1/recovery/sla-execute` (cancel old leg, add alternative to bundle/order, update order_legs).

### 4.6 Webhook Push & Status

- **Webhook service:** Push narrative + adaptive card to a chat thread (ChatGPT, Gemini, or WhatsApp). Thread mapping: `POST /api/v1/webhooks/mappings`. Delivery logging to Supabase.
- **Durable orchestrator:** Standing intent orchestration; wait-for-event; on wake, can call webhook service to push status to thread.
- **Status narrator:** Implemented via durable flow + webhook push to platform-specific thread_id.

### 4.7 Hub Negotiator & Task Queue

- **RFP:** Create RFP (order_id/bundle_id, deadline, compensation); list RFPs (open/closed); get RFP; list/submit bids; select winner; capacity-match (hubs with capacity in window); add hub capacity.
- **Task queue:** Create tasks from order; list tasks by partner (pending/in_progress/completed); get task; start task; complete task (updates order_leg status).

### 4.8 Admin & Config

- **Platform config (Supabase):** Commission, discovery threshold, feature flags, LLM/image provider IDs, ranking, composite_discovery_config, retry_phrases, **intent_heuristic_config** (all heuristic patterns), upsell_surge_rules, thinking_ui, kill_switch, etc.
- **Portal (Platform):** General, LLM & AI, Discovery & Ranking, **Prompts** tab (model interactions), Integrations, Embeddings. Intent heuristics (fallback) vs Intent LLM (force model, prompt in Prompts tab) clearly separated.
- **Admin API:** Kill switch, platform config, test interaction, standing intents, experience flow rules.

### 4.9 Chat Clients & Auth

- **uso-unified-chat:** Next.js chat UI; threads; add to bundle, checkout, fulfillment modal; link to Discovery/orchestrator APIs; themes; Connect WhatsApp; Sign in (Clerk).
- **assistant-ui-chat:** assistant-ui runtime; bundle/checkout/payment inline; Gateway actions (add_to_bundle, view_bundle, checkout, explore_product); fixed sidebar + “Atreyai” outside when collapsed; Settings (Login, Connect WhatsApp, Themes); link-account API.
- **Embed:** Embeddable chat.
- **Clerk:** Auth; link_account (Clerk user ↔ platform_user_id for WhatsApp/omnichannel).

### 4.10 Partner Portal Conversations & WhatsApp

**Partner conversations (portal):**

- **Implemented:** Partner portal has a full **Conversations** experience: list conversations (filter: all / mine / unassigned), create conversation, open conversation detail, send/receive messages, assign conversation to team member. Data: `conversations` and `messages` tables (Supabase), scoped by `partner_id`.
- **Inbound (customer → partner):** A webhook `POST /api/webhooks/conversations/customer-message` (auth: partner API key) allows an external system to inject a customer message into an existing portal conversation. Optional: Hybrid Response (AI auto-respond) when `partners.ai_auto_respond_enabled` is true. There is **no** built-in Twilio (or other) webhook in the portal that receives WhatsApp from a customer and creates or routes to a conversation; that would require a separate ingress (e.g. Twilio webhook → backend that resolves partner/conversation and calls this API).
- **Outbound (partner → customer):** When the partner replies in the portal, the message is stored only. **Sending that reply to the customer via WhatsApp (or any channel) is not implemented.**

**Change requests / negotiations and WhatsApp:**

- **Partner channel config:** In Partner Portal → Omnichannel, partners can connect **WhatsApp** (store phone in `communication_preferences`) or use **API** (webhook URL in Integrations). The UI states that "Orders and negotiation updates will be sent to your WhatsApp number via Twilio."
- **Actual behavior:** When a change request is created, the Omnichannel Broker notifies the partner **only if channel is API**: it POSTs to the partner's webhook URL. When channel is `whatsapp`, the broker **only creates the negotiation**; it does **not** call Twilio (or any provider) to send an SMS/WhatsApp to the partner's phone. So **partner-facing WhatsApp for change requests is not implemented**.
- **Negotiations in portal:** Negotiations live in the omnichannel-broker DB. There is **no** UI in the partner portal to list or respond to negotiations (e.g. change requests), and **no** automatic creation of or link from a negotiation to a portal conversation. Partners respond today by calling `POST /webhooks/partner` (e.g. from their own system or a demo script).

**Summary:** Partner conversations in the portal are implemented; they are **not** fully connected to WhatsApp (no customer→partner or partner→customer WhatsApp in portal, no outbound WhatsApp to partner for change requests, no negotiations list in portal).

---

## 5. End-to-End Use Case: Full Lifecycle (Bundle, Customization, Partner Change, Re-Sourcing)

This use case walks through one path that touches **bundle, customization, commitment, payment, order, partner change, rejection, re-sourcing, task queue, and webhook**.

### 5.1 Discovery & Intent

1. **User** (in chat): “Plan a date night” or “Best birthday gifts under $50.”
2. **Orchestrator** receives message; calls **Intent Service** (LLM or heuristic).
3. **Intent** returns e.g. `discover_composite` (date night: flowers, dinner, limo) or `discover` (search_query “birthday gifts”).
4. **Orchestrator** calls **Discovery** with intent (composite categories or search query).
5. **Discovery** (Scout, product mix, experience_flow_rules) returns products and **Adaptive Cards** with “Add to bundle”.
6. **Webhook / chat client** shows cards; user may say “Add the first option” or “Add roses and dinner for two”.

### 5.2 Bundle Building & Customization

7. **Client** calls Discovery `POST /api/v1/bundle/add` (single) or `POST /api/v1/bundle/add-bulk` (multiple products, optional fulfillment_fields).
8. **Discovery** creates or updates **bundle** and **bundle_legs** in Supabase; optionally creates/updates **experience_session** and **experience_session_legs** for thread.
9. User adds more items (e.g. movie tickets). Bundle now has multiple legs (multi-partner).
10. **Customization:** For bulk add with `requires_fulfillment`, client shows fulfillment modal (delivery address, pickup time, etc.); same add-bulk API with fulfillment details.
11. **View bundle:** Client calls bundle by ID; Discovery returns bundle + legs; client shows bundle card with “Checkout” and “Request change” actions.

### 5.3 Commitment Precheck & Checkout

12. **Checkout** (from chat or portal): Client calls Orchestrator or Payment **commitment precheck** with `bundle_id` and **StandardizedShipping** (address, email, phone).
13. **Payment service** loads bundle and groups legs by partner; for each partner, resolves **commitment provider** (Shopify or local); creates draft/reservation (e.g. Shopify draft order); returns **TCO** (total_amount, breakdown with reservation_id per partner).
14. **Client** shows total; user confirms. Client calls **create PaymentIntent** (with commitment_breakdown and thread_id in metadata if commitment flow).
15. **Payment service** creates Stripe PaymentIntent; client completes payment with Stripe.js (or redirect Checkout Session).
16. **Stripe webhook** (payment_intent.succeeded): Payment service completes Shopify drafts (or local), creates **order** and **order_legs** (one per bundle_leg), updates experience_session_legs; may call Orchestrator/Discovery for order creation depending on wiring.
17. **Task queue:** Back-end or orchestrator calls `POST /api/v1/orders/{order_id}/tasks`; **task-queue-service** creates **vendor_tasks** from order_legs. Partners later list/start/complete tasks.

### 5.4 Partner Change Request & Rejection

18. **Change request:** User or system requests a change (e.g. “Replace the flowers with tulips” or “Partner can’t fulfill—need alternative”). Client or Orchestrator calls **Omnichannel Broker** `POST /api/v1/change-request` (order_id, order_leg_id, partner_id, original_item, requested_change).
19. **Broker** creates **negotiation** in DB; fetches partner channel (API vs demo_chat/whatsapp). For **API**, POSTs to partner webhook URL with negotiation_id and payload.
20. **Partner** (external system) responds: `POST /webhooks/partner` with negotiation_id and **response: "reject"** (optional rejection_reason, counter_offer).
21. **Broker** updates negotiation status to rejected; calls **Re-Sourcing** `POST /api/v1/recovery/trigger` with negotiation_id and rejection payload.

### 5.5 Autonomous Re-Sourcing

22. **Re-Sourcing service** loads negotiation, order, order_leg; **cancels** external order (e.g. Shopify) via commitment_cancel and **cancels** our order_leg.
23. **Discovery** call to find **alternatives** (same category/query, exclude rejecting partner).
24. If alternatives found: creates **autonomous_recovery** record; can return narrative + adaptive card with options to user (e.g. “Partner couldn’t fulfill. Here are alternatives: A, B, C”).
25. **User** selects alternative. Client or backend calls **Re-Sourcing** `POST /api/v1/recovery/sla-execute` (experience_session_leg_id, alternative_partner_id, alternative_product_id, alternative_price).
26. **Re-Sourcing** adds alternative as new order_leg (and bundle_leg if applicable), cancels or supersedes old leg; order and task queue reflect new leg. Optionally **webhook push** to chat: “We’ve replaced with [alternative]. Your order is updated.”

### 5.6 Status & Notifications

27. **Durable orchestrator** (e.g. standing intent or post-order workflow) may **wait for event** (e.g. “partner_responded” or “payment_received”).
28. On **wake**, orchestrator or Status Narrator logic calls **Webhook service** `POST /api/v1/webhooks/chat/{platform}/{thread_id}` with narrative and optional adaptive card.
29. **Webhook service** delivers to **ChatGPT**, **Gemini**, or **WhatsApp** (thread_id or phone); logs delivery in **webhook_deliveries**.
30. User sees status update in the same chat thread.

### 5.7 Hub Negotiator (Optional Path)

31. For assembly or delivery that requires **hub bidding**, platform or partner creates **RFP** via hub-negotiator `POST /api/v1/rfps` (order_id/bundle_id, deadline, compensation).
32. **Hubs** with capacity (registered via `POST /api/v1/hub-capacity`) are matched via `GET /api/v1/rfps/{id}/capacity-match`.
33. Hubs submit **bids** `POST /api/v1/rfps/{id}/bids`; platform **selects winner** `POST /api/v1/rfps/{id}/select-winner`. Order/fulfillment can then reference winning hub.

---

## 6. Key APIs (Summary)

| Service | Key endpoints |
|---------|----------------|
| **Orchestrator** | `POST /api/v1/chat`, `POST /api/v1/bundle/add`, `POST /checkout`, `POST /change-request`, `GET /api/v1/threads`, platform-config, standing intents |
| **Intent** | `POST /api/v1/resolve` (intent from text) |
| **Discovery** | `GET /api/v1/discover`, `POST /api/v1/bundle/add`, `POST /api/v1/bundle/add-bulk`, `GET /api/v1/bundles/{id}`, `POST /checkout`, remove/replace in bundle, experience-categories |
| **Payment** | `POST /api/v1/commitment/precheck`, `POST /api/v1/payment/create`, `POST /api/v1/payment/checkout-session`, `POST /webhooks/stripe`, sponsorship |
| **Omnichannel Broker** | `POST /api/v1/change-request`, `POST /webhooks/partner` |
| **Re-Sourcing** | `POST /api/v1/recovery/trigger`, `POST /api/v1/recovery/sla-execute` |
| **Task Queue** | `POST /api/v1/orders/{order_id}/tasks`, `GET /api/v1/tasks`, `POST /api/v1/tasks/{id}/start`, `POST /api/v1/tasks/{id}/complete` |
| **Webhook** | `POST /api/v1/webhooks/chat/{platform}/{thread_id}`, `POST /api/v1/webhooks/push`, `POST /api/v1/webhooks/mappings` |
| **Hub Negotiator** | `POST /api/v1/rfps`, `GET /api/v1/rfps`, `POST /api/v1/rfps/{id}/bids`, `POST /api/v1/rfps/{id}/select-winner`, `GET /api/v1/rfps/{id}/capacity-match`, `POST /api/v1/hub-capacity` |

---

## 7. Data Model (Critical Entities)

- **bundles** / **bundle_legs** – Draft basket; leg = product + partner + price.
- **orders** / **order_legs** – Post-payment; order_leg has external_order_id, vendor_type, partner_id.
- **experience_sessions** / **experience_session_legs** – Thread-scoped; link to commitment (reservation_id) and SLA.
- **negotiations** – Partner change requests; status (awaiting_partner_reply, accepted, rejected, escalated).
- **vendor_tasks** – One per order_leg; partner task list (pending → in_progress → completed).
- **rfps** / **bids** / **hub_capacity** – Hub Negotiator.
- **webhook_deliveries** / **chat_thread_mappings** – Webhook push and thread mapping.

---

## 8. Deployment & Configuration Notes

- **Env vars:** Per-service URLs (DISCOVERY_SERVICE_URL, INTENT_SERVICE_URL, PAYMENT_SERVICE_URL, OMNICHANNEL_BROKER_URL, RE_SOURCING_SERVICE_URL, TASK_QUEUE_SERVICE_URL, HUB_NEGOTIATOR_SERVICE_URL, WEBHOOK_SERVICE_URL); Stripe keys and webhook secret; Supabase; Clerk; optional Twilio for WhatsApp.
- **Portal:** Platform Config (including Intent heuristics and Prompts) stored in Supabase `platform_config`; Partner Portal for partners and omnichannel/webhook config.
- **No placeholders:** All listed features use real DB, Stripe, and service-to-service calls; heuristic patterns and prompts are configurable via admin UI.

---

## 9. Document References

- Architecture: `.cursor/plans/02-architecture.md`
- Modules detail: `.cursor/plans/03-modules-all.md`
- Commitment flow: `.cursor/plans/commitment-first_orchestration_uso_c9129fd9.plan.md`
- Deployment: `docs/RENDER_DEPLOYMENT.md`, `docs/TESTING_RENDER_AND_PORTAL.md`
- Model interactions: `docs/MODEL_INTERACTIONS_ARCHITECTURE.md`
