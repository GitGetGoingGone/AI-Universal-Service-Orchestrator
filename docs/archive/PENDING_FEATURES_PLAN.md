# Pending Features Plan

Plan for all remaining features to complete pre-Phase 1 (Month 0) and unlock production readiness. Status source: [08-task-register.md](../.cursor/plans/08-task-register.md).

---

## 1. Implementation Order (Priority)

| # | Feature | Type | Depends On | Est. Effort | Status |
|---|---------|------|------------|-------------|--------|
| 1 | Month 0 Integration Hub | Technical | None | High | Done |
| 2 | Pillar 1: Capability mapping & schema | Technical | None | Medium | Done |
| 3 | Pillar 4: SLA & resilience | Technical | None | Medium | Done |
| 4 | Pillar 5: Proof & approval workflows | Technical | Module 8 (exists) | Medium | Done |
| 5 | Pillar 2: Legal framework | Legal/docs | None | Low (no code) | Pending |
| 6 | OpenAI merchant onboarding | Operational | Done build | Low | Pending |
| 7 | Google UCP registration | Operational | Done build | Low | Pending |

---

## 2. Month 0 Integration Hub

**Purpose:** Durable Orchestrator shell, Agentic AI configuration, Adaptive Card Generator, integration testing. Unlocks standing intents and long-running workflows.

### 2.1 Durable Orchestrator shell

- **Status:** `functions/durable-orchestrator/` exists (Docker, Azure Functions)
- **Gaps:**
  - Standing Intent API (`POST /api/v1/standing-intents`, `wait_for_external_event`)
  - Time-Chain pause/resume on proof states
  - Integration with Intent Service (immediate vs standing intent detection)
- **Deliverables:**
  - `POST /api/v1/standing-intents` – create standing intent
  - `POST /api/v1/standing-intents/{id}/approve` – user approval
  - `context.wait_for_external_event("UserApproval", timeout)` pattern
  - Webhook Bridge integration for status push

### 2.2 Agentic AI configuration

- **Status:** Orchestrator has `run_agentic_loop`, Intent + Discovery wired
- **Gaps:**
  - Agentic consent / agency boundaries (endpoint exists: `/api/v1/agentic-consent`)
  - Standing intent handoff from agentic flow
- **Deliverables:**
  - Document agentic consent flow
  - Wire standing intent creation from agentic planner when condition-based intent detected

### 2.3 Adaptive Card Generator templates

- **Status:** Product cards, proof cards exist in proofing-service
- **Gaps:**
  - Centralized template library
  - Proof card with approval buttons in Support Hub
- **Deliverables:**
  - `packages/shared/adaptive_cards/` or equivalent template bundle
  - Proof card with Approve/Reject actions for chat

### 2.4 Integration testing

- **Deliverables:**
  - E2E test: Intent → Discovery → Standing Intent creation
  - E2E test: Proof → Approve → Time-Chain resume
  - Health-and-warmup script coverage for all services

### References

- [05-implementation.md § Pillar 5](./05-implementation.md) – Proof states, Time-Chain pause
- [03-modules-all.md § Module 23](./03-modules-all.md) – Standing Intent Engine
- [06-user-flows.md § 1.2](./06-user-flows.md) – Immediate vs standing intent

---

## 3. Pillar 1: Data model & capability mapping

**Purpose:** Finalize schema, capability mapping, inventory sync architecture, affiliate link tracking.

### 3.1 Data model schema

- **Status:** Core tables exist (`products`, `partners`, `order_*`, `proof_states`, etc.)
- **Gaps:**
  - Capability taxonomy (Module 7) – `capability_tags` exists; mapping to products needs formalization
  - Inventory sync: `product_inventory`; sync architecture (webhook vs poll) not defined
- **Deliverables:**
  - Document capability mapping: `capability_tags` → product capabilities, search filters
  - Schema migration if needed for capability hierarchy

### 3.2 Inventory sync architecture

- **Status:** `inventory_webhook` in Discovery service
- **Gaps:**
  - Design: push (webhook) vs pull (poll) per partner
  - `product_inventory` sync from partner systems
- **Deliverables:**
  - Architecture doc: `docs/INVENTORY_SYNC_ARCHITECTURE.md`
  - Webhook schema for partner inventory updates

### 3.3 Affiliate link tracking schema

- **Status:** Module 21 (Affiliate) not implemented
- **Deliverables:**
  - `affiliate_links` or `product_affiliate_metadata` schema
  - Affiliate Link Wrapper (Module 21) design for Scout Engine

### References

- [03-modules-all.md § Module 7](./03-modules-all.md) – Premium Registry & Capability Mapping
- [03-modules-all.md § Module 21](./03-modules-all.md) – Affiliate Onboarding

---

## 4. Pillar 4: SLA & resilience

**Purpose:** SLA thresholds, buffer calculations, kill switch protocol, affiliate partner SLAs.

### 4.1 SLA thresholds

- **Deliverables:**
  - Define SLA thresholds (e.g. response time, availability)
  - `platform_config` or env vars for SLA thresholds
  - `requires_human_approval_over` (e.g. $200) – already in action models

### 4.2 Buffer calculations

- **Status:** Time-Chain Resolver (Module 5) not implemented
- **Deliverables:**
  - Buffer logic for delivery windows (e.g. +15 min buffer)
  - Document in architecture

### 4.3 Kill switch protocol

- **Deliverables:**
  - `POST /api/v1/admin/kill-switch` or equivalent
  - Pause platform operations (e.g. block new orders)
  - Admin dashboard event log for kill switch

### 4.4 Affiliate partner SLAs

- **Deliverables:**
  - SLA definitions for affiliate partners
  - Breach handling (e.g. de-list, throttle)

### References

- [05-implementation.md § Pillar 4](./05-implementation.md) – Kill switch, SLA

---

## 5. Pillar 5: Proof & approval workflows

**Purpose:** Formalize proof state machine, Vision AI integration, approval workflows. Module 8 (Virtual Proofing Engine) is implemented; this pillar completes the design and integrations.

### 5.1 Proof state machine

- **Status:** `proof_states` table, approve/reject in proofing-service
- **Gaps:**
  - Formal state machine diagram
  - Time-Chain pause/resume integration
  - `proof_state_transitions` table (if not exists)
- **Deliverables:**
  - State machine doc: `Pending → In_Progress → Proof_Ready → [Approved|Rejected] → [Proceed|Revise]`
  - Migration for `proof_state_transitions` if needed
  - Time-Chain integration: pause leg on `proof_ready`, resume on `approved`

### 5.2 Vision AI integration

- **Status:** Not implemented
- **Deliverables:**
  - Azure Computer Vision or OpenAI Vision for proof image comparison
  - `auto_approve_with_vision_ai(proof_image_url, source_of_truth_url)` – similarity score
  - Thresholds: ≥0.95 auto-approve, ≥0.85 human review, &lt;0.85 reject

### 5.3 Approval workflows

- **Deliverables:**
  - Approval timeout (24h default) → escalate or auto-approve with Vision AI
  - Support Hub / chat: Proof card with Approve/Reject actions
  - Admin dashboard: proof review queue, escalation

### References

- [05-implementation.md § Pillar 5](./05-implementation.md) – Proof states, Vision AI
- [03-modules-all.md § Module 8](./03-modules-all.md) – Virtual Proofing Engine

---

## 6. Pillar 2: Legal framework

**Purpose:** Legal documentation; no code changes.

### 6.1 Deliverables

- Terms of Service drafted (incl. AI agent clause, §8.4 human approval over $200)
- Merchant of Record (MoR) decision documented
- Insurance (E&O for AI) considerations
- Affiliate commission agreements drafted

### References

- [05-implementation.md § Pillar 2](./05-implementation.md) – ToS, MoR, insurance

---

## 7. Operational items

### 7.1 OpenAI merchant/feed onboarding

- **Status:** ACP feed URL exists; manual registration required
- **Deliverables:**
  - Complete OpenAI merchant onboarding
  - Point feed URL to `GET /api/v1/feeds/acp?format=jsonl.gz` (or per-partner)
  - Document in `docs/CHATGPT_APP_DIRECTORY_SUBMISSION.md` or equivalent

### 7.2 ChatGPT App Directory submission

- **Status:** MCP server built; deploy and submit
- **Deliverables:**
  - Deploy MCP server (e.g. Render)
  - Submit to OpenAI App Directory per `docs/CHATGPT_APP_DIRECTORY_SUBMISSION.md`

### 7.3 Google UCP registration

- **Status:** `/.well-known/ucp` live; discovery requires Google UCP waitlist
- **Deliverables:**
  - Join [Google UCP waitlist](https://support.google.com/merchants/contact/ucp_integration_interest)
  - Document registration steps

---

## 8. Future modules (not in scope for Month 0)

| Module | Name | Phase | Notes |
|--------|------|-------|-------|
| 5 | Time-Chain Resolver | Patent | Route optimization, conflict simulation |
| 6 | Autonomous Re-Sourcing | MVP Critical | Live demo of autonomous recovery |
| 7 | Premium Registry & Capability Mapping | Phase 2 | Part of Pillar 1 |
| 9 | Generic Capability Portal | Phase 2 | Partner capability registration |
| 12 | Multi-Party Support Hub | Phase 2 | Unified chat, WhatsApp bridge |
| 14 | Status Narrator | Phase 2 | Empathetic status updates |
| 15 | Atomic Multi-Checkout | Phase 2 | Stripe Connect, split payments |
| 16 | Transaction & Escrow Manager | Phase 2 | Escrow, payment release |
| 19–25 | Storefront, Curation, Affiliate, etc. | Phase 3+ | Later roadmap |

---

## 9. Quick reference

| Pending | Action |
|---------|--------|
| Month 0 Integration Hub | Durable Orchestrator, standing intents, adaptive cards, integration tests |
| Pillar 1 | Capability mapping doc, inventory sync design, affiliate schema |
| Pillar 4 | SLA config, buffer logic, kill switch API, admin events |
| Pillar 5 | Proof state machine doc, Vision AI, approval timeout, Support Hub proof approval |
| Pillar 2 | ToS, MoR, insurance (legal only) |
| OpenAI onboarding | Manual: register merchant, point to feed URL |
| ChatGPT App | Deploy MCP, submit to App Directory |
| Google UCP | Join waitlist |

---

## 10. References

- [08-task-register.md](../.cursor/plans/08-task-register.md) – Status dashboard
- [05-implementation.md](../.cursor/plans/05-implementation.md) – Pillar details, schema
- [03-modules-all.md](../.cursor/plans/03-modules-all.md) – Module specs
- [06-user-flows.md](../.cursor/plans/06-user-flows.md) – User flows
- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) – Deployment
