---
name: Task Register - Single View of All Planned Tasks
overview: One place for all planned tasks and latest status. Update status here; details live in linked plan sections.
---

# Task Register — Single View of All Planned Tasks

**Use this file as the single place to see what’s planned and current status.** Details (acceptance criteria, APIs, schema) stay in [05-implementation.md](./05-implementation.md) and [03-modules-all.md](./03-modules-all.md); this register is the **status dashboard**.

**How to use**
- **See what’s pending**: Scan for `Pending` or `In progress`.
- **Update status**: Change the status cell when work is done (or started), and optionally add a short note.
- **Find details**: Use the **Source** link to open the section that defines the task.
- **Plan for pending**: [docs/PENDING_FEATURES_PLAN.md](../../docs/PENDING_FEATURES_PLAN.md) – detailed plan for all pending features.

**Status key**: `Pending` | `In progress` | `Done`

---

## 1. Partner Portal (05-implementation)

| ID | Task | Status | Source |
|----|------|--------|--------|
| partner-earnings | Earnings: Payout dashboard, commission breakdown, invoice management | Done | [05 § Phase 1](./05-implementation.md) |
| partner-analytics | Analytics: Sales, peak hours, popular items, CSV export | Done | [05 § Phase 1](./05-implementation.md) |
| partner-ratings | Ratings: Review dashboard, respond to reviews | Done | [05 § Phase 1](./05-implementation.md) |
| partner-team | Team: Team members, roles, assignments (partner_members) | Done | [05 § Phase 1](./05-implementation.md) |
| partner-admins | Admins: Partner admins (owner promotes/revokes) | Done | [05 § Phase 1](./05-implementation.md) |
| partner-integrations | Integrations: Webhook, API poll, OAuth availability | Done | [05 § Phase 1](./05-implementation.md) |
| partner-settings-general | Settings General: Channel, pause orders, capacity, notifications | Done | [05 § Phase 1](./05-implementation.md) |
| partner-conversations | Chat: ChatGPT-style UX (left nav + center chat), team assignment | Done | [09-chat-conversations](./09-chat-conversations.md) |

---

## 2. Schema & Discovery (ACP / UCP) (05-implementation)

| ID | Task | Status | Source |
|----|------|--------|--------|
| schema-partners-seller-fields | Partners: Add seller_name, seller_url, return_policy, privacy_policy, terms_url, store_country | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| schema-products-acp-fields | Products: Add ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries) or metadata | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-acp-feed-export | ACP feed export: DB → jsonl.gz/csv.gz with partner join for seller_* per product | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-acp-feed-url | ACP feed URL: Public endpoint or per-partner (?partner_id=) and OpenAI registration | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-ucp-well-known | UCP: /.well-known/ucp and catalog API (UCP Item shape) | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-merchant-attribution | Merchant attribution: Feed/catalog use partner as seller; bundling unchanged | Done | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |

---

## 2b. Profile discoverable – push, rate limit, portal (profile-discoverable-chatgpt-gemini)

*User-controlled push (single item or all; target ChatGPT and/or Gemini), ChatGPT 15-min rate limit, partner portal ACP/UCP UI. Full plan: [profile-discoverable-chatgpt-gemini.md](./profile-discoverable-chatgpt-gemini.md).*

| ID | Task | Status | Source |
|----|------|--------|--------|
| discovery-push-api | Push API: POST .../feeds/push with scope (single \| all \| selected), targets (chatgpt \| gemini \| both) | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |
| discovery-acp-rate-limit | ChatGPT 15-min rate limit: persist last_acp_push_at, reject push if &lt; 15 min, UI countdown / next-allowed time | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |
| portal-acp-ucp-partner-fields | Partner portal: Commerce profile form for ACP/UCP seller fields + validate for discovery | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |
| portal-acp-ucp-product-fields | Partner portal: Product edit ACP/UCP fields (url, brand, eligibility, availability, target_countries) + validation | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |
| discovery-validate-api | Validation API: product + partner ACP/UCP validation (GET .../validate-discovery) | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |
| portal-push-controls | Partner portal: Push controls (single vs all vs selected), ChatGPT/Gemini/both, 15-min throttle messaging | Done | [profile-discoverable](./profile-discoverable-chatgpt-gemini.md) |

---

## 3. Pillars (Pre–Phase 1) (05-implementation)

| Task | Status | Source |
|------|--------|--------|
| Pillar 1: Data model schema finalized, capability mapping, inventory sync architecture, affiliate link tracking schema | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 2: Legal framework, ToS drafted, MoR decision, insurance, affiliate commission agreements | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 3: Manifest template finalized, action models, offline discovery strategy, affiliate manifest integration | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 4: SLA thresholds, buffer calculations, kill switch protocol, affiliate partner SLAs | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 5: Proof state machine, Vision AI integration, approval workflows | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Chat-First Foundation: API response standard, JSON-LD schemas, Adaptive Cards library, Link Account flow | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Month 0 Integration Hub: Durable Orchestrator shell, Agentic AI configured, Adaptive Card Generator, integration testing | Done | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |

---

## 4. Schema & Discovery — Checklist detail (05-implementation)

*Same scope as section 2; these are the checkbox items.*

| Task | Status |
|------|--------|
| Partners table: seller attribution fields (seller_name, seller_url, return_policy_url, privacy_policy_url, terms_url, store_country) | Done |
| Products table: ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries, availability enum) | Done |
| Products: UCP price in minor units (cents) for UCP Item | Done |
| Feed export pipeline: products JOIN partners → ACP ndjson/jsonl.gz/csv/csv.gz (?format=), ACP validation; single + full catalog | Done |
| Feed URL or delivery: public URL or per-partner (?partner_id=), OpenAI registration (manual) | Done |
| OpenAI merchant/feed onboarding completed | Pending |
| /.well-known/ucp endpoint with UCP profile | Done |
| UCP REST Schema (rest.openapi.json) with searchGifts, custom endpoint | Done |
| Catalog API: UCP Item shape (id, title, price cents, image_url), optional seller per item | Done |
| Checkout/order APIs (optional) for full UCP checkout | Done |
| Merchant on record: partner as seller in feed and catalog; product URL shows "Sold by {partner}" | Done |
| Bundling: document feed = discovery-only; bundling remains in orchestrator | Done |
| **Profile discoverable (see section 2b)** Push API (scope + targets); ChatGPT 15-min throttle; portal ACP/UCP forms + validation API + push controls | Done |

---

## 5. Modules — Phase 2 & Phase 3 (03-modules-all)

*Implementation not started; details in 03-modules-all.*

| Module | Name | Phase | Status |
|--------|------|-------|--------|
| 2 | Legacy Adapter Layer | Phase 2 | Done |
| 3 | AI-First Discoverability | Phase 2 | Done |
| 8 | Virtual Proofing Engine | Phase 2 | Done |
| 10 | HubNegotiator & Bidding | Phase 2 | Done |
| 11 | Multi-Vendor Task Queue | Phase 2 | Done |
| 13 | Hybrid Response Logic | Phase 2 | Done |
| 17 | Reverse Logistics | Phase 3 | Done |
| 18 | Admin Command Center | Phase 3 | Done |

---

## 5b. Implementation Order (Next Up)

**Full implementation, no mocks.** Details in [03-modules-all.md](./03-modules-all.md) and [05-implementation.md](./05-implementation.md).

| # | Task | Scope |
|---|------|-------|
| 1 | **AI-First Discoverability** (Module 3) | Done – Manifest template, action models, offline discovery strategy |
| 2 | **Admin Command Center** (Module 18) | Done – Dashboard metrics, period filter, escalations, export |
| 3 | **Reverse Logistics** (Module 17) | Done – return_requests, refunds, restock_events, API |
| 4 | **Virtual Proofing Engine** (Module 8) | Done – proof_states, DALL-E generate, approve/reject workflow |
| 5 | **Portal – Task Queue** | Done – Partner Tasks page, proxy to Task Queue |
| 6 | **Portal – HubNegotiator** | Done – Partner RFPs/bids; Platform create/select winner |
| 7 | **Portal – Hybrid Response** | Done – Support page with classify-and-route |
| 8 | **Portal – Omnichannel connect** | Done – Connect options (WhatsApp) in portal |
| 9 | **Order → Task Queue** | Done – Discovery checkout calls Task Queue |
| 10 | **Checkout and payments** | Done – Payment page with Stripe Elements, Pay link in orders |
| 11 | **Legacy Adapter (Module 2)** | Done – POST /api/v1/admin/legacy/ingest, portal Import → Legacy |

---

## 5c. ChatGPT App Directory, Gemini UCP, Unified Web App (05-implementation)

*UCP discovery + checkout for Gemini; ChatGPT App via MCP; unified web app for end users. Full plan: [05-implementation § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app).*

| ID | Task | Status | Source |
|----|------|--------|--------|
| ucp-checkout-api | UCP Checkout: Discovery service REST API (Create, Get, Update, Complete, Cancel) per UCP spec | Done | [05 § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app) |
| chatgpt-app-mcp | ChatGPT App: MCP server with 12 tools, deploy, submit to App Directory | Done | [05 § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app) |
| unified-web-app | Unified Web App: Next.js chat app with ChatGPT or Gemini provider switch | Done | [05 § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app) |
| orchestrator-auxiliary | Orchestrator: auxiliary endpoints (manifest, order status, classify-support, returns) | Done | [05 § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app) |
| chatgpt-gemini-test-scenarios | Docs: CHATGPT_GEMINI_TEST_SCENARIOS.md with test prompts for UCP, ChatGPT app, web app | Done | [05 § ChatGPT App Directory](./05-implementation.md#chatgpt-app-directory-gemini-ucp-and-unified-web-app) |

---

## 5d. Composite Bundle (Date Night, Bundles) (composite-bundle-unified-plan)

*Probing → discover → multiple bundle options → bulk add. Configurable prompts, product mix, enable/disable. Full plan: [composite-bundle-unified-plan.md](./composite-bundle-unified-plan.md).*

| ID | Task | Status | Source |
|----|------|--------|--------|
| composite-bulk-add-api | Bulk Add API: Discovery add_products_to_bundle_bulk, POST /bundle/add-bulk; Orchestrator client + proxy | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-chat-handler | Chat UI: Handle add_bundle_bulk action, POST /api/bundle/add-bulk | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-bundle-options | suggest_composite_bundle_options: 2–4 options per experience; experience card "Add [Label]" per option | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-db-prompt | suggest_composite_bundle: Fetch prompt from model_interaction_prompts when available | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-enable-flag | enable_composite_bundle_suggestion: platform_config flag; loop checks before calling suggest | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-products-per-cat | products_per_category: Configurable in composite_discovery_config; loop uses for per_limit | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-config-ui | Config UI: Composite Discovery section (products per category, sponsorship checkbox, enable bundle suggestion) | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-product-mix | Product mix: Discovery slices (price_desc, price_asc, rating, popularity, sponsored, recent); compose by pct, dedupe | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-sold-count | products.sold_count: Migration for popularity slice; search_products + semantic_search include it | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |
| composite-product-mix-ui | Product Mix editor: Add/remove slices, sort/limit/pct per slice, validate pct sums to 100 | Done | [composite-bundle-unified-plan](./composite-bundle-unified-plan.md) |

---

## 6. Implemented (reference)

| Item | Status |
|------|--------|
| AI Agents Integration (Orchestrator chat: Intent → Discovery) | Done |
| Module 1: Multi-Protocol Scout Engine (semantic search, UCP/ACP adapters, manifest cache, inventory webhook) | Done |
| Partner Portal: Dashboard with real data; stub nav items removed | Done |
| Webhook infrastructure (05 Pillar 6) | Done |
| Schema & Discovery: Partner/product ACP fields, ACP feed (ndjson, jsonl.gz, csv, csv.gz), UCP well-known + catalog, merchant attribution | Done |
| Profile discoverable: Push API (single/all/selected), 15-min rate limit, Commerce profile + product ACP/UCP forms, validation API, push controls | Done |
| Module 11: Multi-Vendor Task Queue (vendor_tasks, order-leg sequence, partner task list, start/complete) | Done |
| Module 10: HubNegotiator & Bidding (RFPs, bids, select winner, hub capacity matching) | Done |
| Module 13: Hybrid Response Logic (classify-and-route, support_escalations, assign/resolve) | Done |
| Module 3: AI-First Discoverability (manifest, action models, /.well-known/agent-manifest, /api/v1/manifest) | Done |
| Module 18: Admin Command Center (dashboard metrics, escalations, export reports) | Done |
| Module 17: Reverse Logistics (return requests, refunds, restock events) | Done |
| Module 8: Virtual Proofing Engine (proof_states, DALL-E generate, approve/reject) | Done |
| Portal – Omnichannel connect (WhatsApp) | Done |
| Chat-First Foundation (Link Account, Adaptive Cards, JSON-LD) | Done |
| Module 2: Legacy Adapter Layer | Done – CSV/Excel/JSON ingest, column mapping, Scout Engine integration, portal import |
| UCP REST Schema (rest.openapi.json) | Done – searchGifts operationId, gift params, well-known points to custom schema |
| ChatGPT App (MCP), Unified Web App, Orchestrator auxiliary | Done – see 5c |
| Composite Bundle (Date Night, Bundles) | Done – probing, discover, 2–4 options, bulk add, product mix, config UI – see 5d |

---

## Keeping this file in sync

1. **When you start a task**: Set status to `In progress` and optionally add a one-line note.
2. **When you finish a task**: Set status to `Done`; move to section 6 if it’s a major deliverable.
3. **When you add a new planned task**: Add a row in the right section (or a new section) and set status `Pending`.
4. **05-implementation.md** frontmatter todos: You can keep them for tooling; update **this register** as the source of truth for status so one place stays current.
