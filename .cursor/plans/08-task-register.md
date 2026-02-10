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

**Status key**: `Pending` | `In progress` | `Done`

---

## 1. Partner Portal (05-implementation)

| ID | Task | Status | Source |
|----|------|--------|--------|
| partner-earnings | Earnings: Payout dashboard, commission breakdown, invoice management | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-analytics | Analytics: Sales, peak hours, popular items, CSV export | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-ratings | Ratings: Review dashboard, respond to reviews | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-team | Team: Team members, roles, assignments (partner_members) | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-admins | Admins: Partner admins (owner promotes/revokes) | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-integrations | Integrations: Webhook, API poll, OAuth availability | Pending | [05 § Phase 1](./05-implementation.md) |
| partner-settings-general | Settings General: Channel, pause orders, capacity, notifications | Pending | [05 § Phase 1](./05-implementation.md) |

---

## 2. Schema & Discovery (ACP / UCP) (05-implementation)

| ID | Task | Status | Source |
|----|------|--------|--------|
| schema-partners-seller-fields | Partners: Add seller_name, seller_url, return_policy, privacy_policy, terms_url, store_country | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| schema-products-acp-fields | Products: Add ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries) or metadata | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-acp-feed-export | ACP feed export: DB → jsonl.gz/csv.gz with partner join for seller_* per product | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-acp-feed-url | ACP feed URL: Public endpoint or per-partner (?partner_id=) and OpenAI registration | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-ucp-well-known | UCP: /.well-known/ucp and catalog API (UCP Item shape) | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |
| discovery-merchant-attribution | Merchant attribution: Feed/catalog use partner as seller; bundling unchanged | Pending | [05 § Schema & Discovery](./05-implementation.md#schema--discovery-requirements-acp--ucp) |

---

## 3. Pillars (Pre–Phase 1) (05-implementation)

| Task | Status | Source |
|------|--------|--------|
| Pillar 1: Data model schema finalized, capability mapping, inventory sync architecture, affiliate link tracking schema | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 2: Legal framework, ToS drafted, MoR decision, insurance, affiliate commission agreements | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 3: Manifest template finalized, action models, offline discovery strategy, affiliate manifest integration | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 4: SLA thresholds, buffer calculations, kill switch protocol, affiliate partner SLAs | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Pillar 5: Proof state machine, Vision AI integration, approval workflows | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Chat-First Foundation: API response standard, JSON-LD schemas, Adaptive Cards library, Link Account flow | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |
| Month 0 Integration Hub: Durable Orchestrator shell, Agentic AI configured, Adaptive Card Generator, integration testing | Pending | [05 § Pillar Checklist](./05-implementation.md#pillar-implementation-checklist) |

---

## 4. Schema & Discovery — Checklist detail (05-implementation)

*Same scope as section 2; these are the checkbox items.*

| Task | Status |
|------|--------|
| Partners table: seller attribution fields (seller_name, seller_url, return_policy_url, privacy_policy_url, terms_url, store_country) | Pending |
| Products table: ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries, availability enum) | Pending |
| Products: UCP price in minor units (cents) for UCP Item | Pending |
| Feed export pipeline: products JOIN partners → ACP jsonl.gz/csv.gz, ACP validation before export | Pending |
| Feed URL or delivery: public URL or per-partner, OpenAI registration | Pending |
| OpenAI merchant/feed onboarding completed | Pending |
| /.well-known/ucp endpoint with UCP profile | Pending |
| Catalog API: UCP Item shape (id, title, price cents, image_url), optional seller per item | Pending |
| Checkout/order APIs (optional) for full UCP checkout | Pending |
| Merchant on record: partner as seller in feed and catalog; product URL shows "Sold by {partner}" | Pending |
| Bundling: document feed = discovery-only; bundling remains in orchestrator | Pending |

---

## 5. Modules — Phase 2 & Phase 3 (03-modules-all)

*Implementation not started; details in 03-modules-all.*

| Module | Name | Phase | Status |
|--------|------|-------|--------|
| 2 | Legacy Adapter Layer | Phase 2 | Pending |
| 3 | AI-First Discoverability | Phase 2 | Pending |
| 8 | Virtual Proofing Engine | Phase 2 | Pending |
| 10 | HubNegotiator & Bidding | Phase 2 | Pending |
| 11 | Multi-Vendor Task Queue | Phase 2 | Pending |
| 13 | Hybrid Response Logic | Phase 2 | Pending |
| 17 | Reverse Logistics | Phase 3 | Pending |
| 18 | Admin Command Center | Phase 3 | Pending |

---

## 6. Implemented (reference)

| Item | Status |
|------|--------|
| AI Agents Integration (Orchestrator chat: Intent → Discovery) | Done |
| Module 1: Multi-Protocol Scout Engine (semantic search, UCP/ACP adapters, manifest cache, inventory webhook) | Done |
| Partner Portal: Dashboard with real data; stub nav items removed | Done |
| Webhook infrastructure (05 Pillar 6) | Done |

---

## Keeping this file in sync

1. **When you start a task**: Set status to `In progress` and optionally add a one-line note.
2. **When you finish a task**: Set status to `Done`; move to section 6 if it’s a major deliverable.
3. **When you add a new planned task**: Add a row in the right section (or a new section) and set status `Pending`.
4. **05-implementation.md** frontmatter todos: You can keep them for tooling; update **this register** as the source of truth for status so one place stays current.
