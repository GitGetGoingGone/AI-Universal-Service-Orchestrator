---
name: AI Universal Service Orchestrator Platform - Implementation
overview: Implementation Phases, Month 0, Critical Pillars
todos:
  - id: partner-earnings
    content: Partner Portal - Earnings: Payout dashboard, commission breakdown, invoice management
    status: pending
  - id: partner-analytics
    content: Partner Portal - Analytics: Sales, peak hours, popular items, CSV export
    status: pending
  - id: partner-ratings
    content: Partner Portal - Ratings: Review dashboard, respond to reviews
    status: pending
  - id: partner-team
    content: Partner Portal - Team: Team members, roles, assignments (partner_members)
    status: pending
  - id: partner-admins
    content: Partner Portal - Admins: Partner admins (owner promotes/revokes)
    status: pending
  - id: partner-integrations
    content: Partner Portal - Integrations: Webhook, API poll, OAuth availability
    status: pending
  - id: partner-settings-general
    content: Partner Portal - Settings General: Channel, pause orders, capacity, notifications
    status: pending
  # Schema & discovery (ACP/UCP) – see "Schema & Discovery Requirements" section
  - id: schema-partners-seller-fields
    content: Schema - Partners: Add seller_name, seller_url, return_policy, privacy_policy, terms_url, store_country (for ACP feed attribution)
    status: pending
  - id: schema-products-acp-fields
    content: Schema - Products: Add ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries) or metadata mapping
    status: pending
  - id: discovery-acp-feed-export
    content: Discovery - ACP feed export: Pipeline DB → ACP jsonl.gz/csv.gz with partner join for seller_* per product
    status: pending
  - id: discovery-acp-feed-url
    content: Discovery - ACP feed URL: Public feed endpoint or per-partner feed (e.g. ?partner_id=) and OpenAI registration
    status: pending
  - id: discovery-ucp-well-known
    content: Discovery - UCP: Implement /.well-known/ucp and catalog API (UCP Item shape) for AI platform discovery
    status: pending
  - id: discovery-merchant-attribution
    content: Discovery - Merchant attribution: Feed and catalog responses use partner as seller (not platform); bundling unchanged
    status: pending
---

# Implementation

**Single view of all planned tasks and latest status:** see [08-task-register.md](./08-task-register.md). Update status there; details remain in this file and [03-modules-all.md](./03-modules-all.md).

## Month 0: The Integration Hub (Pre-Implementation Foundation)

Before building any modules, we must establish the core integration components that enable all orchestration features. The **AI Agents Chat Entry Point** is the first priority—it enables ChatGPT and Gemini to use the platform. Then come the "brain," "ears," and "voice" of the system.

### 0. AI Agents Chat Entry Point (Orchestrator Service)

> **Note**: Now part of **Agentic AI** (Section 2). Kept here for reference.

**Purpose**: Single endpoint for AI chat agents (ChatGPT, Gemini) to resolve intent and discover products. Enables Chat-First usage from day one.

**Implementation**:

- Create `orchestrator-service/` (FastAPI on Container Apps)
- Implement `POST /api/v1/chat`:
  - Accepts `{"text": "I want to send flowers to my mom"}`
  - Calls Intent Service (Module 4) to resolve intent
  - When intent indicates discovery: calls Discovery Service (Module 1)
  - Returns unified response: intent + products (JSON-LD + Adaptive Card)
- Health/ready endpoints (with dependency checks on Intent + Discovery)
- Config: `DISCOVERY_SERVICE_URL`, `INTENT_SERVICE_URL`

**Deliverables**:

- `orchestrator-service/` with chat endpoint
- OpenAPI spec: `docs/api/orchestrator-service.openapi.yaml`
- End-to-end test: Chat request → Intent → Discovery → Response

**Timeline**: Week 1 of Month 0

**Status**: ✅ Implemented (MVP)

### 1. Durable Orchestrator (The Brain)

**Purpose**: Build the shell that can "sleep" and "wake up" to handle long-running workflows.

**Implementation**:

- Set up Azure Durable Functions (Python v2) infrastructure
- Create base orchestrator template that can:
  - Checkpoint state
  - Sleep for extended periods (days/weeks)
  - Wake up on external events
  - Resume from checkpoint
- Implement basic wait-for-event pattern
- Test cost efficiency (should be near $0 when sleeping)

**Deliverables**:

- Working Durable Functions environment
- Base orchestrator template
- Wait-for-event pattern implementation
- Cost monitoring dashboard

**Timeline**: Week 1-2 of Month 0

### 2. Agentic AI (includes AI Agents Chat Entry Point)

**Purpose**: Build the AI reasoning layer and single entry point for ChatGPT/Gemini. Enables autonomous planning, decision-making, and agentic handoff.

**Implementation**:

- **AI Agents Chat Entry Point** (orchestrator-service):
  - `POST /api/v1/chat` – single endpoint for AI chat agents
  - Accepts `{"text": "..."}` from ChatGPT/Gemini
  - Returns unified response: intent + products (JSON-LD + Adaptive Card)
  - Config: `DISCOVERY_SERVICE_URL`, `INTENT_SERVICE_URL`
- Integrate LLM-based reasoning (Azure OpenAI / Google AI) for:
  - Intent resolution and Graph of Needs construction
  - Autonomous planning and tool selection
  - Proactive suggestions and conflict resolution
- Implement agentic handoff support (SSO 2.0) for seamless ChatGPT/Gemini → custom UI flow
- Create agentic decision loop:
  - Observe state (orchestrator, discovery, intent)
  - Reason and plan next actions
  - Execute via orchestrator activities
  - Reflect and adapt
- Define agentic consent and agency boundaries (per Pillar 2)
- Test end-to-end: User request → Agent reasons → Plans → Orchestrator executes

**Deliverables**:

- AI Agents Chat Entry Point (orchestrator-service with `POST /api/v1/chat`)
- Agentic AI service (FastAPI on Container Apps)
- LLM integration for intent, planning, and reasoning
- Agentic handoff integration (Clerk or equivalent)
- Decision loop implementation
- Test suite for agentic flows

**Timeline**: Week 2-3 of Month 0

**Status**: ✅ Complete (MVP + location extraction, agent reasoning in cards, agentic consent, Gemini support)

### 3. Adaptive Card Generator (The Voice)

**Purpose**: Create the templates that allow the system to "speak" complex choices back to the user.

**Implementation**:

- Set up Adaptive Cards library structure:
  - `shared/adaptive-cards/` - Card templates
  - Card generator utilities
  - Platform-specific renderers (Gemini, ChatGPT)
- Create base card templates:
  - Product Card
  - Bundle Card
  - Proof Card
  - Time-Chain Card
  - Progress Ledger Card (with If/Then logic visualization)
  - Checkout Card
  - Conflict Suggestion Card
- Implement card generation utilities:
  - Dynamic data binding
  - Conditional rendering
  - Action button generation
- Test card rendering in:
  - Gemini (Dynamic View)
  - ChatGPT (native rendering)
  - WhatsApp (interactive buttons fallback)

**Deliverables**:

- Adaptive Cards library
- All base card templates
- Card generator utilities
- Platform-specific renderers
- Test suite for card rendering

**Timeline**: Week 3-4 of Month 0

### Integration Hub Testing

**End-to-End Test Scenario**:

1. **Durable Orchestrator**: Start orchestration, checkpoint, sleep
2. **Agentic AI**: User request triggers agent reasoning and planning
3. **Agentic Loop**: Agent observes state, plans actions, invokes orchestrator activities
4. **Adaptive Card**: Generate card with agent's response, push to user's chat
5. **User Interaction**: User clicks button in card (or provides follow-up)
6. **Agentic AI**: Processes user input, updates plan, continues orchestration
7. **Orchestrator**: Resumes, processes, completes workflow

**Success Criteria**:

- Orchestrator can sleep and wake up correctly
- Agentic AI reasons and plans correctly
- Events route to correct orchestration instances
- Adaptive Cards render correctly in all platforms
- End-to-end flow works without errors

**Timeline**: Week 4 of Month 0

### Month 0 Deliverables Summary

- ✅ Durable Orchestrator shell (can sleep/wake)
- ✅ Agentic AI (AI Agents Chat Entry Point + autonomous reasoning and agentic handoff)
- ✅ Adaptive Card Generator (can speak complex choices)
- ✅ Integration testing complete
- ✅ Documentation for all components

**Why This Order Matters**:

- **Orchestrator First**: Without the "brain," nothing can coordinate
- **Agentic AI Second**: Without autonomous reasoning, the system can't plan or adapt
- **Cards Third**: Without the "voice," system can't communicate complex states

Once Month 0 is complete, all subsequent modules can build on this foundation.

## Critical Pillars (Pre-Implementation Requirements)

These foundational pillars must be solidified and documented before implementation begins. They are prerequisites for all development work.

### Pillar 1: Data Model - From "Descriptions" to "Actionable Metadata"

**Problem**: AI agents don't "read" websites; they consume structured data models. Product descriptions must be machine-readable and action-oriented.

#### 1.1 "Blank" vs. "Capability" Mapping

**Requirement**: Every product must be defined not just by what it is, but by what can be done to it.

**Bad Example**: "Blue Cotton Onesie" (descriptive only)

**Good Example**:

```json
{
  "product_id": "onesie-001",
  "name": "Blue Cotton Onesie",
  "material": "cotton",
  "base_product": "onesie",
  "capabilities": [
    {
      "capability_type": "embroidery",
      "max_char_limit": 12,
      "supported_locations": ["chest", "back", "sleeve"],
      "pricing": {
        "base": 5.00,
        "per_character": 0.50
      }
    },
    {
      "capability_type": "screen-print",
      "max_colors": 3,
      "supported_locations": ["front", "back"],
      "pricing": {
        "base": 8.00,
        "per_color": 2.00
      }
    }
  ],
  "compatible_services": ["gift_wrapping", "rush_delivery"],
  "customization_metadata": {
    "color_options": ["blue", "white", "gray"],
    "size_options": ["0-3m", "3-6m", "6-12m"],
    "lead_time_hours": 24
  }
}
```

**Database Schema**:

```sql
-- Products with capability mapping
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  base_product_type VARCHAR(100), -- "onesie", "cap", "blanket"
  material VARCHAR(100),
  metadata JSONB NOT NULL, -- Full capability and customization data
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Capability definitions
CREATE TABLE product_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id),
  capability_type VARCHAR(100) NOT NULL, -- "embroidery", "screen-print", "engraving"
  capability_config JSONB NOT NULL, -- Type-specific configuration
  pricing_config JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast capability lookup
CREATE INDEX idx_product_capabilities_type ON product_capabilities(capability_type);
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);
```

**Implementation Requirements**:

- All products in Premium Registry (Module 7) must include capability metadata
- Scout Engine (Module 1) must index capabilities for semantic search
- Intent Resolver (Module 4) must map user intent to capabilities
- Virtual Proofing Engine (Module 8) must use capability metadata for preview generation

#### 1.2 SKU-Level Latency Requirements

**Requirement**: Database must sync inventory across 50+ local vendors in <2 seconds.

**Problem**: If an AI agent confirms a purchase for an out-of-stock item, the Time-Chain collapses.

**Solution Architecture**:

1. **Real-time Inventory Sync**:

  - Use Supabase Realtime subscriptions for inventory updates
  - Upstash Redis for inventory cache (sub-second reads)
  - Event-driven updates via Azure Service Bus

2. **Inventory Schema**:
```sql
-- Real-time inventory tracking
CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id),
  vendor_id UUID REFERENCES partners(id),
  sku VARCHAR(100) NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0,
  reserved_quantity INTEGER DEFAULT 0, -- For pending orders
  available_quantity INTEGER GENERATED ALWAYS AS (quantity - reserved_quantity) STORED,
  last_synced_at TIMESTAMPTZ DEFAULT NOW(),
  sync_status VARCHAR(50) DEFAULT 'synced', -- 'synced', 'syncing', 'error'
  UNIQUE(vendor_id, sku)
);

-- Real-time inventory updates log
CREATE TABLE inventory_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inventory_id UUID REFERENCES inventory(id),
  old_quantity INTEGER,
  new_quantity INTEGER,
  update_source VARCHAR(100), -- 'vendor_api', 'manual', 'system'
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable realtime for inventory
ALTER PUBLICATION supabase_realtime ADD TABLE inventory;
```

3. **Caching Strategy**:

  - Upstash Redis: Cache inventory for all active products
  - TTL: 1 second (refresh every second)
  - Pattern: `inventory:{vendor_id}:{sku}` → `{quantity, reserved, available}`
  - On update: Invalidate cache immediately

4. **Sync Performance Targets**:

  - Inventory update propagation: <500ms
  - Cache invalidation: <100ms
  - Total sync time: <2 seconds across all vendors
  - API response time: <200ms for inventory checks

5. **Reservation System**:

  - When order created: Reserve inventory immediately (atomic operation)
  - Reservation TTL: 15 minutes (if not confirmed, release)
  - On confirmation: Convert reservation to actual deduction
  - On cancellation: Release reservation immediately

**Implementation Requirements**:

- Module 1 (Scout Engine) must check inventory before returning results
- Module 5 (Time-Chain Resolver) must verify inventory availability before calculating feasibility
- Module 15 (Payment) must confirm inventory before processing payment
- Module 6 (Autonomous Re-Sourcing) must check inventory when finding alternatives
- Module 21 (Affiliate) must track inventory for affiliate partners
- Module 22 (Curation Picker) must validate inventory when creating bundles

---

### Pillar 2: Legal & Liability - The "Agentic Agency" Problem

**Problem**: When an AI agent makes a $500 purchase on behalf of a user and the local artisan ruins the product, who is liable?

#### 2.1 Merchant of Record (MoR) Decision

**Requirement**: Decide if platform is the merchant or simply the Orchestrator.

**Recommendation**: Use Delegated Payment Token model (via Stripe ACP integration)

**Architecture**:

- User's AI agent holds payment token (AP2 - Agent Payments Protocol)
- Platform orchestrates but does not hold funds
- Vendors receive payment directly from user's token
- Platform collects orchestration fee separately

**Payment Flow**:

1. User authorizes AP2 token to AI agent
2. AI agent uses token to authorize payments
3. Platform orchestrates split payments:

  - Vendor A: $200 (direct from token)
  - Vendor B: $150 (direct from token)
  - Platform fee: $50 (separate transaction)

4. Platform never touches customer funds for vendors
5. Platform liability limited to orchestration services

**Legal Structure**:

- Platform Terms of Service: "Orchestration Service Provider"
- Vendor Agreements: Direct relationship with customer
- Platform Agreement: Limited to coordination, not product quality

#### 2.2 Autonomous Error Indemnity

**Requirement**: Terms of Service must include "Hallucination Clauses"

**Problem**: If AI "Intent Resolver" misinterprets "Blue" as "Red," who covers return cost?

**Policy Framework**:

1. **AI Error Categories**:

  - **Category 1 - Minor Misinterpretation** (e.g., color shade difference):
  - Platform covers return shipping
  - Vendor covers replacement cost
  - Customer receives credit for inconvenience

  - **Category 2 - Major Misinterpretation** (e.g., wrong product type):
  - Platform covers full return + replacement
  - Customer receives full refund option
  - AI model training updated to prevent recurrence

  - **Category 3 - System Failure** (e.g., inventory sync error):
  - Platform covers all costs
  - Automatic re-sourcing triggered
  - Customer receives apology credit

2. **Terms of Service Clauses**:
```
Section 8: AI Agent Liability

8.1 Agentic Purchases: When an AI agent makes purchases on your behalf,
    you authorize the agent to act as your agent for payment purposes.

8.2 Interpretation Errors: The platform uses AI to interpret your intent.
    While we strive for accuracy, interpretation errors may occur.

8.3 Error Resolution:
    a) Minor errors (<$50 impact): Return shipping covered by platform
    b) Major errors (>$50 impact): Full refund or replacement at platform cost
    c) System errors: Full coverage including inconvenience compensation

8.4 Human Review Threshold: Orders over $200 require human approval
    before final confirmation, unless explicitly authorized.

8.5 Dispute Resolution: All disputes resolved through platform support
    with 48-hour response SLA.
```

3. **Implementation Requirements**:

  - Module 4 (Intent Resolver) must log confidence scores
  - Low confidence (<80%) triggers human review flag
  - Module 13 (Hybrid Response Logic) must escalate high-value errors
  - All AI decisions must be logged for audit trail

4. **Insurance Considerations**:

  - Errors & Omissions (E&O) insurance for AI decisions
  - Product liability remains with vendors
  - Platform liability limited to orchestration errors

---

### Pillar 3: The "Agent Directory" & Manifest Strategy

**Requirement**: Finalized Manifest Template for Module 3 (AI Discoverability)

#### 3.1 Manifest Template Structure

**Purpose**: Allow AI agents to "see" and interact with platform services even when server scales to zero.

**ACP (Agentic Commerce Protocol) Manifest Template**:

```json
{
  "manifest_version": "1.0",
  "platform_id": "uso-orchestrator",
  "platform_name": "AI Universal Service Orchestrator",
  "discovery_endpoint": "https://api.usoorchestrator.com/v1/discovery",
  "capabilities": {
    "can_initiate_checkout": true,
    "can_modify_order": false,
    "can_cancel_order": true,
    "requires_human_approval_over": 200.00,
    "currency": "USD",
    "supported_regions": ["US", "CA"],
    "max_order_value": 10000.00
  },
  "action_models": [
    {
      "action": "discover_products",
      "method": "POST",
      "endpoint": "/v1/discover",
      "requires_auth": false,
      "rate_limit": "100/hour",
      "parameters": {
        "intent": "string (required)",
        "location": "geo_point (optional)",
        "budget_range": "price_range (optional)",
        "deadline": "datetime (optional)"
      }
    },
    {
      "action": "create_order",
      "method": "POST",
      "endpoint": "/v1/orders",
      "requires_auth": true,
      "requires_approval_if_over": 200.00,
      "parameters": {
        "bundle_id": "uuid (required)",
        "customization": "object (optional)",
        "delivery_address": "address (required)",
        "payment_token": "ap2_token (required)"
      }
    },
    {
      "action": "modify_order",
      "method": "PATCH",
      "endpoint": "/v1/orders/{id}",
      "requires_auth": true,
      "allowed_modifications": ["delivery_address", "delivery_time"],
      "restricted_modifications": ["products", "customization"]
    },
    {
      "action": "cancel_order",
      "method": "DELETE",
      "endpoint": "/v1/orders/{id}",
      "requires_auth": true,
      "allowed_before_delivery": true,
      "cancellation_fee": "calculated"
    },
    {
      "action": "track_order",
      "method": "GET",
      "endpoint": "/v1/orders/{id}/status",
      "requires_auth": true,
      "rate_limit": "60/hour"
    }
  ],
  "product_schema": {
    "required_fields": ["product_id", "name", "capabilities", "pricing"],
    "capability_format": {
      "type": "string",
      "config": "object",
      "pricing": "object"
    }
  },
  "offline_discovery": {
    "enabled": true,
    "cache_ttl": 3600,
    "static_manifest_url": "https://cdn.usoorchestrator.com/manifests/latest.json",
    "update_frequency": "hourly"
  },
  "webhook_endpoints": {
    "order_status": "https://api.usoorchestrator.com/v1/webhooks/order-status",
    "inventory_update": "https://api.usoorchestrator.com/v1/webhooks/inventory"
  }
}
```

#### 3.2 Offline Discovery Strategy

**Requirement**: Agents must be able to discover services even when server scales to zero.

**Implementation**:

1. **Static Manifest Hosting**:

  - Host manifest on CDN (Vercel Edge or Azure Blob Storage)
  - Update hourly via scheduled job
  - Include: Product catalog, capabilities, pricing (cached)
  - Exclude: Real-time inventory, order status

2. **Cache Strategy**:

  - Agents cache manifest locally
  - TTL: 1 hour
  - On cache miss: Fallback to CDN static manifest
  - Real-time data requires active API connection

3. **Manifest Versioning**:

  - Versioned manifests: `manifests/v1.0.json`, `manifests/v1.1.json`
  - Agents check version on startup
  - Backward compatibility maintained for 3 versions

#### 3.3 Action Models Definition

**Requirement**: Clearly define what agents are allowed to do.

**Action Model Schema**:

```sql
CREATE TABLE agent_action_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_name VARCHAR(100) UNIQUE NOT NULL,
  method VARCHAR(10) NOT NULL, -- GET, POST, PATCH, DELETE
  endpoint VARCHAR(255) NOT NULL,
  requires_auth BOOLEAN DEFAULT TRUE,
  requires_approval_if_over DECIMAL(10,2),
  rate_limit_per_hour INTEGER,
  allowed_parameters JSONB,
  restricted_parameters JSONB,
  allowed_modifications JSONB, -- For PATCH actions
  restricted_modifications JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Default Action Models**:

- `discover_products`: No auth, 100/hour
- `create_order`: Auth required, approval if >$200
- `modify_order`: Auth required, limited modifications
- `cancel_order`: Auth required, fee applies
- `track_order`: Auth required, 60/hour

**Implementation Requirements**:

- Module 3 (AI-First Discoverability) must serve manifest
- All API endpoints must validate against action models
- Rate limiting must be enforced
- Approval workflows must trigger based on action models

---

### Pillar 4: Real-time Service Level Agreements (SLAs)

**Problem**: In a multi-vendor "Time-Chain," a 10-minute delay by a gig worker cascades into a missed dinner reservation.

#### 4.1 Dynamic Buffers

**Requirement**: Algorithm must include "Buffer Legs" to account for "Agentic Friction"

**Implementation**:

- If vendor says job takes 2 hours, system logs as 2.5 hours (25% buffer)
- Buffer percentage varies by:
  - Service type (customization: 25%, delivery: 15%, pickup: 10%)
  - Vendor reliability score (high: 10%, medium: 25%, low: 50%)
  - Time of day (rush hour: +20%, off-peak: standard)
  - Weather conditions (if applicable: +15%)

**Buffer Calculation**:

```python
def calculate_buffer_time(base_time, service_type, vendor_reliability, time_of_day, conditions):
    base_buffer = {
        'customization': 0.25,
        'delivery': 0.15,
        'pickup': 0.10,
        'assembly': 0.20
    }[service_type]

    reliability_multiplier = {
        'high': 0.10,
        'medium': 0.25,
        'low': 0.50
    }[vendor_reliability]

    time_multiplier = 1.20 if is_rush_hour(time_of_day) else 1.0
    conditions_multiplier = 1.15 if has_adverse_conditions(conditions) else 1.0

    total_buffer = base_buffer + reliability_multiplier
    buffer_time = base_time * total_buffer * time_multiplier * conditions_multiplier

    return buffer_time
```

**Database Schema**:

```sql
CREATE TABLE sla_configurations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_type VARCHAR(100) NOT NULL,
  base_buffer_percentage DECIMAL(5,2) NOT NULL,
  reliability_multipliers JSONB, -- {"high": 0.10, "medium": 0.25, "low": 0.50}
  time_of_day_multipliers JSONB, -- {"rush_hour": 1.20, "off_peak": 1.0}
  condition_multipliers JSONB, -- {"adverse_weather": 1.15, "normal": 1.0}
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4.2 The "Kill Switch" Protocol

**Requirement**: Define exact threshold for Module 6 (Autonomous Re-Sourcing)

**Protocol Definition**:

1. **Delay Thresholds**:

  - **Warning Threshold**: 15 minutes behind schedule
  - System sends alert to vendor
  - Customer notified: "Slight delay, still on track"
  - No action taken

  - **Critical Threshold**: 30 minutes behind schedule
  - System triggers re-sourcing evaluation
  - Checks for alternative vendors
  - Prepares backup plan
  - Customer notified: "We're finding a backup option"

  - **Kill Switch Threshold**: 45 minutes behind schedule OR delivery deadline at risk
  - System automatically cancels current vendor
  - Activates "Hot-Shot" replacement
  - Customer notified: "We've upgraded your delivery to ensure on-time arrival"
  - Original vendor marked for review

2. **Kill Switch Logic**:
```python
def evaluate_kill_switch(order_id, current_delay, time_to_deadline):
    # Critical threshold reached
    if current_delay >= 45 or time_to_deadline < current_delay + 30:
        # Find replacement
        replacement = find_hot_shot_replacement(order_id)

        if replacement:
# Cancel current vendor
cancel_vendor_task(order_id, reason="delay_threshold")

# Assign replacement
assign_replacement_vendor(order_id, replacement)

# Notify all parties
notify_customer(order_id, "upgraded_delivery")
notify_admin(order_id, "kill_switch_activated")

# Log for analysis
log_kill_switch_event(order_id, current_delay, replacement)

return True

    return False
```

3. **Database Schema**:
```sql
CREATE TABLE kill_switch_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  original_vendor_id UUID REFERENCES partners(id),
  replacement_vendor_id UUID REFERENCES partners(id),
  delay_minutes INTEGER,
  time_to_deadline_minutes INTEGER,
  reason VARCHAR(255),
  activated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sla_thresholds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  threshold_type VARCHAR(50), -- 'warning', 'critical', 'kill_switch'
  delay_minutes INTEGER NOT NULL,
  action_required VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```


**Implementation Requirements**:

- Module 5 (Time-Chain Resolver) must calculate buffers
- Module 6 (Autonomous Re-Sourcing) must implement kill switch
- Module 14 (Status Narrator) must notify at each threshold
- Admin dashboard must show kill switch events

---

### Pillar 5: Trust & Verification - The "Proof" Leg

**Requirement**: Database must support Asynchronous Approval for "White Glove" perfection

#### 5.1 Mandatory "Proof" States

**Problem**: Virtual Proofing Engine must be able to pause Time-Chain until approval.

**Implementation**:

1. **Proof State Machine**:
```
Pending → In_Progress → Proof_Ready → [Approved | Rejected] → [Proceed | Revise]
```

2. **Database Schema**:
```sql
CREATE TABLE proof_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  order_leg_id UUID, -- Reference to specific leg requiring proof
  proof_type VARCHAR(50), -- 'virtual_preview', 'artisan_photo', 'quality_check'
  current_state VARCHAR(50) NOT NULL, -- 'pending', 'in_progress', 'proof_ready', 'approved', 'rejected'
  proof_image_url TEXT,
  proof_metadata JSONB, -- Additional proof data
  submitted_by UUID REFERENCES users(id), -- Artisan or system
  approved_by UUID REFERENCES users(id), -- Customer or Vision AI
  approval_method VARCHAR(50), -- 'human', 'vision_ai', 'auto'
  approval_confidence DECIMAL(5,2), -- For AI approvals
  rejection_reason TEXT,
  submitted_at TIMESTAMPTZ,
  approved_at TIMESTAMPTZ,
  time_chain_paused BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Proof state transitions log
CREATE TABLE proof_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proof_state_id UUID REFERENCES proof_states(id),
  from_state VARCHAR(50),
  to_state VARCHAR(50),
  transitioned_by UUID REFERENCES users(id),
  transition_reason TEXT,
  transitioned_at TIMESTAMPTZ DEFAULT NOW()
);
```

3. **Time-Chain Pause Logic**:
```python
def handle_proof_submission(order_id, leg_id, proof_image_url):
    # Create proof state
    proof_state = create_proof_state(
        order_id=order_id,
        leg_id=leg_id,
        proof_type='artisan_photo',
        current_state='proof_ready',
        proof_image_url=proof_image_url
    )

    # Pause time-chain for this leg
    pause_time_chain_leg(order_id, leg_id, reason='awaiting_proof_approval')

    # Notify customer
    notify_customer(order_id, 'proof_ready_for_approval', proof_image_url)

    # Start approval timer (24 hours max)
    start_approval_timer(proof_state.id, timeout_hours=24)

    return proof_state

def handle_proof_approval(proof_state_id, approved, approved_by, method='human'):
    proof_state = get_proof_state(proof_state_id)

    if approved:
        update_proof_state(proof_state_id, 'approved', approved_by, method)
        resume_time_chain_leg(proof_state.order_id, proof_state.leg_id)
        notify_vendor(proof_state.order_id, 'proof_approved')
    else:
        update_proof_state(proof_state_id, 'rejected', approved_by, method)
        request_revision(proof_state.order_id, proof_state.leg_id)
        notify_vendor(proof_state.order_id, 'proof_rejected')
```

4. **Vision AI Integration**:
```python
def auto_approve_with_vision_ai(proof_image_url, source_of_truth_image_url):
    # Compare proof image with source of truth
    similarity_score = vision_ai_compare(proof_image_url, source_of_truth_image_url)

    if similarity_score >= 0.95:
        return {
'approved': True,
'confidence': similarity_score,
'method': 'vision_ai'
        }
    elif similarity_score >= 0.85:
        return {
'approved': False,
'requires_human_review': True,
'confidence': similarity_score,
'method': 'vision_ai_review_needed'
        }
    else:
        return {
'approved': False,
'requires_human_review': True,
'confidence': similarity_score,
'method': 'vision_ai_rejected'
        }
```

5. **Approval Timeout Handling**:
```python
def handle_approval_timeout(proof_state_id):
    proof_state = get_proof_state(proof_state_id)

    # If no response after 24 hours, auto-approve with low confidence
    if proof_state.current_state == 'proof_ready':
        auto_approve_with_vision_ai(proof_state.proof_image_url, proof_state.source_of_truth_url)

        # If AI can't approve, escalate to human
        if not auto_approved:
escalate_to_human_review(proof_state_id)
notify_admin(proof_state.order_id, 'proof_timeout_escalation')
```


**Implementation Requirements**:

- Module 8 (Virtual Proofing Engine) must create proof states
- Module 5 (Time-Chain Resolver) must pause on proof states
- Module 12 (Support Hub) must allow proof approval in chat
- Vision AI integration for auto-approval (Azure Computer Vision or similar)
- Admin dashboard for proof review and escalation

---

### Pillar Implementation Checklist

Before Phase 1 begins, ensure:

- [ ] **Pillar 1**: Data model schema finalized, capability mapping defined, inventory sync architecture designed, affiliate link tracking schema defined
- [ ] **Pillar 2**: Legal framework documented, Terms of Service drafted, MoR decision made, insurance secured, affiliate commission agreements drafted
- [ ] **Pillar 3**: Manifest template finalized, action models defined, offline discovery strategy implemented, affiliate manifest integration planned
- [ ] **Pillar 4**: SLA thresholds defined, buffer calculations implemented, kill switch protocol documented, affiliate partner SLAs defined
- [ ] **Pillar 5**: Proof state machine designed, Vision AI integration planned, approval workflows defined
- [ ] **Chat-First Foundation**: API response standard defined, JSON-LD schemas created, Adaptive Cards library built, ~~webhook infrastructure set up~~ ✅, Link Account flow implemented
- [ ] **Month 0 Integration Hub**: Durable Orchestrator shell built, Agentic AI configured, Adaptive Card Generator templates created, integration testing complete

**Timeline**: All pillars must be completed in **Month 0** (pre-implementation phase)

### Schema & Discovery Requirements (ACP / UCP)

Trackable requirements for commerce feed schema and AI platform discovery. Reference: `docs/COMMERCE_FEED_SCHEMA_REQUIREMENTS.md`, `docs/ACP_COMPLIANCE.md`, `docs/AI_PLATFORM_PRODUCT_DISCOVERY.md`.

#### Schema requirements

- [ ] **Partners table (seller attribution)**  
  Add or expose partner-level fields for ACP feed and UCP catalog: `seller_name` (e.g. `business_name`), `seller_url`, `return_policy_url`, `privacy_policy_url`, `terms_url`, `store_country`, optional `target_countries`. Used so "merchant on record" is the actual partner, not the platform.
- [ ] **Products table (ACP)**  
  Add or map ACP-required fields: `url`, `brand`, `is_eligible_search`, `is_eligible_checkout`, `target_countries`, `store_country` (or equivalent in `metadata` / partner). Map `is_available` → availability enum. Ensure validation uses `acp_compliance` before export.
- [ ] **Products (UCP)**  
  Ensure price can be expressed in **minor units (cents)** when returning UCP Item shape; no new columns required beyond existing id, name, price, image_url.

#### Discovery – ACP (push feed for ChatGPT)

- [ ] **Feed export pipeline**  
  Build export: `products` JOIN `partners` → ACP-shaped rows (jsonl.gz or csv.gz). Populate every row with partner’s `seller_name`, `seller_url`, `return_policy`, and when checkout-eligible `seller_privacy_policy`, `seller_tos`. Run ACP validation before export.
- [ ] **Feed URL or delivery**  
  Expose feed at a stable public URL (e.g. `GET /api/v1/feeds/acp` or per-partner `?partner_id=...`) or implement OpenAI’s SFTP/upload delivery. Document for OpenAI merchant/feed registration.
- [ ] **Registration**  
  Complete OpenAI merchant/feed onboarding and point to our feed URL or use their upload flow.

#### Discovery – UCP (expose API for Google AI Mode / Gemini)

- [ ] **`/.well-known/ucp`**  
  Implement well-known endpoint (or static file) with UCP profile: version, capabilities, REST/MCP schema URLs, base URL. Make discoverable (crawlable, optional directory registration).
- [ ] **Catalog API**  
  Implement catalog/search endpoint that returns UCP Item shape: `id`, `title`, `price` (integer cents), optional `image_url`. Can wrap existing discovery service and map responses. Include seller/merchant per item where schema allows.
- [ ] **Checkout/order APIs (optional)**  
  If full UCP checkout desired: create/update/complete checkout, order confirmation, webhooks. Not required for discovery-only.

#### Merchant attribution & bundling

- [ ] **Merchant on record**  
  In ACP feed and UCP catalog/checkout responses: never use platform as seller for partner products; always source seller_* and policy URLs from the partner record. Product URL should point to partner page or our detail page showing "Sold by {partner}".
- [ ] **Bundling**  
  No change: feed lists individual products with correct seller; cross-partner bundling and checkout remain in our orchestrator (bundle add/remove, order with multiple order_items/order_legs per partner). Document that feed is discovery-only; bundling is runtime.

**Timeline**: Schema and discovery work can run in parallel with Phase 1; ACP feed export and UCP endpoints unlock native ChatGPT/Google discovery when ready.

### Pillar 6: Chat-First / Headless Foundation

**Requirement**: All features must be accessible via standardized REST API with machine-readable responses for AI agent consumption.

#### 6.1 API Response Standard

**Requirement**: Every API response must include machine-readable JSON-LD block.

**Standard Response Format**:

```json
{
  "data": {
    // Response data
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "EntityType",
    // JSON-LD structured data
  },
  "adaptive_card": {
    // Optional: Adaptive Card JSON
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "ISO8601",
    "request_id": "uuid"
  }
}
```

**Implementation**:

- Create shared response wrapper in `shared/utils/api_response.py`
- All endpoints use wrapper
- JSON-LD schemas defined in `shared/json-ld/`

#### 6.2 Adaptive Cards Library

**Requirement**: All complex states must have Adaptive Card representations.

**Card Types Required**:

- Product Card
- Bundle Card
- Proof Card
- Time-Chain Card
- Progress Ledger Card
- Checkout Card

**Implementation**:

- Card templates in `shared/adaptive-cards/`
- Card generators in each service
- Platform-specific rendering (Gemini Dynamic View, ChatGPT Instant Checkout)

#### 6.3 Webhook Push Notification Bridge

**Requirement**: Durable Functions must send updates to specific Chat Thread IDs.

**Implementation**:

- Webhook service (FastAPI on Container Apps)
- Platform-specific handlers (ChatGPT, Gemini, WhatsApp)
- Database: `chat_thread_mappings`, `webhook_deliveries`
- Integration with Durable Functions Status Narrator Activity

#### 6.4 Zero-Friction Auth

**Requirement**: One-tap account linking for Google/OpenAI identity.

**Implementation**:

- Link Account API endpoint
- OAuth token verification
- Account link database table
- Agentic Consent Manager API
- Integration with Clerk for session management

**Timeline**: Chat-First foundation must be completed in **Month 0** alongside other pillars

**Note**: The Adaptive Cards library component overlaps with Month 0: The Integration Hub. The Adaptive Card Generator (The Voice) built in Month 0 will serve as the foundation for the Chat-First Adaptive Cards implementation.

## Implementation Phases

### Phase 1: MVP Foundation (Months 1-3)

1. Set up hybrid infrastructure:

  - Azure Container Apps environment
  - Supabase project (PostgreSQL with pgvector and PostGIS extensions)
  - Upstash Redis instance
  - Vercel project for frontend
  - Clerk application for IAM
  - React Native project setup (shared codebase)
  - PWA configuration for Next.js

2. **Build Design System Foundation** (Critical - must be done first):

  - Set up design system package structure
  - Define design tokens (colors, typography, spacing) - **Mobile-responsive from start**
  - Build base component library (Button, Card, Input, etc.) - **React Native compatible components**
  - Create default theme - **Mobile and web themes**
  - Set up theme injection system - **Works for web, mobile, and PWA**
  - Document component API and usage - **Include mobile usage examples**

3. **Implement Chat-First Foundation** (Critical - must be done first):

  - **API Response Standard**: All endpoints return standardized format with JSON-LD
  - **Adaptive Cards Library**: Build card generators for all complex states
  - **Webhook Infrastructure**: Set up webhook push notification bridge
  - **Link Account Flow**: Implement zero-friction account linking
  - **JSON-LD Schemas**: Define Schema.org schemas for all entity types

4. Implement basic IAM with Clerk (user/partner login with RBAC):

  - **Web**: Next.js integration
  - **Mobile**: React Native Clerk SDK integration
  - **PWA**: Service worker for offline auth

5. Build discovery service (Module 1) - FastAPI on Container Apps, UCP only initially:

  - **Web**: Discovery UI in Next.js
  - **Mobile**: React Native discovery screen
  - **PWA**: Offline caching of recent discoveries

6. Build intent resolver (Module 4) - FastAPI with Azure OpenAI GPT-4o:

  - **Web**: Intent input UI
  - **Mobile**: Voice input support (React Native)
  - **PWA**: Offline intent queue

7. Build time-chain resolver (Module 5) - basic version with PostGIS:

  - **Web**: Timeline visualization
  - **Mobile**: Map view with route visualization
  - **PWA**: Push notifications for timeline updates

8. Build partner portal (Module 9) - Next.js on Vercel with Supabase Realtime (using design system):

  - **Web**: Full portal experience
  - **Mobile**: Partner mobile app (React Native)
  - **PWA**: Partner PWA for quick access

9. Build payment service (Module 15) - FastAPI with Stripe Connect:

  - **Web**: Checkout flow
  - **Mobile**: React Native Stripe SDK integration
  - **PWA**: Payment request API support

10. Build escrow service (Module 16) - basic hold/release with Supabase transactions:

  - **Web**: Escrow status dashboard
  - **Mobile**: Payment status notifications
  - **PWA**: Real-time escrow updates

### Phase 2: Core Features (Months 4-6)

1. Complete registry service (Module 7):

  - **Web**: Registry browsing and search
  - **Mobile**: React Native registry screen with filters
  - **PWA**: Offline registry cache

2. Build support hub (Module 12) - Basic real-time chat (using design system components):

  - **Web**: Full chat interface
  - **Mobile**: React Native chat screen with push notifications
  - **PWA**: Service worker for background message sync

3. **Build Autonomous Re-Sourcing (Module 6) - MVP Critical: Live Demo**:

  - **Web**: Autonomous recovery dashboard
  - **Mobile**: Push notifications for recovery events
  - **PWA**: Background sync for recovery status
  - **All platforms**: Live demo capability - user requests change, partner says "No", AI automatically finds alternative and updates timeline
  - Integration with Module 24 (Omnichannel Broker) for partner communication
  - Integration with Module 1 (Scout Engine) for finding alternatives
  - Integration with Module 5 (Time-Chain Resolver) for timeline recalculation
  - Integration with Module 14 (Status Narrator) for user notifications with reasoning

4. **Build Partner Simulator (Module 25) - MVP Critical: For Live Demo**:

  - **Web**: Partner simulator dashboard for creating/managing test partners
  - **Web**: Product catalog manager for simulated partners
  - **Web**: Scenario builder for configuring automated/manual responses
  - **Web**: Manual response queue interface
  - **Web**: Live Demo quick setup interface
  - **Backend**: Simulator engine with automated/manual response handling
  - **Backend**: Integration with Module 1 (Scout Engine) - simulated partners appear in search
  - **Backend**: Integration with Module 24 (Omnichannel Broker) - receives and responds to negotiations
  - **Backend**: Integration with Module 6 (Autonomous Re-Sourcing) - triggers recovery scenarios
  - **All platforms**: Create partners with different products and response scenarios

4. Add legacy adapter layer (Module 2):

  - **Web**: Legacy vendor integration UI
  - **Mobile**: Legacy vendor product display
  - **PWA**: Legacy product caching

5. Implement AI-first discoverability (Module 3):

  - **Web**: AI agent integration UI
  - **Mobile**: Deep-link handling for AI agent handoffs
  - **PWA**: AI agent manifest caching

6. Add advanced IAM features (passkeys, agentic handoff):

  - **Web**: Passkey registration/login
  - **Mobile**: Biometric passkey (FaceID/TouchID)
  - **PWA**: Passkey API support

7. **Enhance Support Hub (Module 12)** - Full chat features:

  - Typing indicators (**Web + Mobile + PWA**)
  - Read receipts (**Web + Mobile + PWA**)
  - File attachments (**Web + Mobile**: Camera integration, **PWA**: File API)
  - Message search (**Web + Mobile + PWA**)
  - Multi-party presence (**Web + Mobile + PWA**)

8. **WhatsApp Integration** - Phase 1:

  - Twilio WhatsApp API setup
  - Status update notifications (template messages) - **All platforms**
  - Webhook integration
  - Basic two-way messaging - **Mobile**: Deep-link to WhatsApp, **Web**: WhatsApp Web integration

9. **Storefront Customization Platform (Module 19)** - Phase 1:

  - Theme engine implementation - **Mobile-responsive themes**
  - Basic visual theme editor - **Web only (admin)**
  - Theme preset system - **Mobile preview support**
  - Partner storefront creation API
  - Custom domain support (CNAME) - **Mobile**: Subdomain routing

10. **Curation, Merchandising & Promotion Engine (Module 20)** - Phase 1:

  - Basic curated bundle creation - **Web + Mobile**: Bundle display
  - Simple ranking boost system
  - Featured partner functionality - **Mobile**: Featured section
  - Transparent/Concierge mode toggle - **Mobile**: Mode-aware UI

11. **Affiliate Onboarding & Link Orchestration (Module 21)** - Phase 1:

  - Self-service registration portal - **Web**: Registration UI, **Mobile**: Partner app
  - Basic affiliate link wrapper - **All platforms**: Tracking ID injection
  - KYC verification system - **Web**: Admin dashboard
  - Trust scoring foundation - **Web**: Trust score display

12. **The Curation Picker (Module 22)** - Phase 1:

  - Visual bundle canvas - **Web only (admin)**: Drag-and-drop interface
  - Product picker with semantic search - **Web**: Product search UI
  - Basic margin calculator - **Web**: Real-time margin display
  - Partner locking (hard/soft) - **Web**: Lock controls

13. **Standing Intent Engine (Module 23)** - Phase 1:

  - Durable Functions setup - **Azure**: Orchestrator infrastructure
  - Basic orchestrator function - **Python v2**: Core orchestration logic
  - Intent watcher activity - **Timer-triggered**: Condition checking
  - Progress ledger - **Web + Mobile**: Real-time progress display
  - Basic HITL support - **Web + Mobile**: User approval flows

14. **Omnichannel Message Broker & HITL Escalation (Module 24)** - Phase 1:

  - Multi-channel router - **All platforms**: WhatsApp, SMS, Email, API
  - Basic negotiation state machine - **Durable Functions**: State tracking
  - Two-way webhooks - **Twilio**: WhatsApp and SMS webhook handlers
  - NLP re-processing - **Module 4 integration**: Counter-offer extraction
  - Basic escalation triggers - **All platforms**: Timeout, sentiment, deadlock
  - Admin dashboard foundation - **Web only**: Negotiation monitoring

### Phase 3: Advanced Features (Months 7-12)

1. Virtual proofing engine (Module 8):

  - **Web**: High-fidelity preview
  - **Mobile**: React Native image viewer with zoom/pan
  - **PWA**: Image caching for offline preview

2. Hub negotiator & bidding (Module 10):

  - **Web**: Hub dashboard for bidding
  - **Mobile**: Hub mobile app for real-time bid notifications
  - **PWA**: Background bid updates

3. Multi-vendor task queue (Module 11):

  - **Web**: Task queue management
  - **Mobile**: Task notifications and quick actions
  - **PWA**: Background task sync

4. Hybrid response logic (Module 13):

  - **Web**: AI/Human response indicators
  - **Mobile**: Push notifications for human responses
  - **PWA**: Background response sync

5. Status narrator (Module 14) - Integrated with WhatsApp and Agent Reasoning:

  - **Web**: Status updates dashboard with reasoning explanations
  - **Mobile**: Push notifications with status messages and "Why" context
  - **PWA**: Background status sync
  - **All platforms**: Enhanced Progress Ledger cards with Agent Reasoning section

6. **WhatsApp Integration** - Phase 2:

  - Full channel synchronization (WhatsApp ↔ Web Chat) - **All platforms**
  - Interactive messages (quick replies, lists) - **Mobile**: Native WhatsApp integration
  - Rich media support (images, documents, location) - **Mobile**: Camera/GPS integration
  - Conversation bridging with AI orchestrator - **All platforms**
  - Opt-in/opt-out management - **Mobile**: In-app settings

7. **Storefront Customization Platform (Module 19)** - Phase 2:

  - Advanced visual editor (drag-and-drop) - **Web only (admin)**
  - Component-level customization - **Mobile preview**
  - Layout builder - **Mobile-responsive layouts**
  - Branded email templates
  - Theme export/import
  - Storefront analytics dashboard - **Mobile**: Analytics app
  - A/B testing for themes - **Mobile**: Theme variant testing

8. **Curation, Merchandising & Promotion Engine (Module 20)** - Phase 2:

  - Advanced boost engine with dynamic weighting
  - Meta-partner manifest system - **Mobile**: Manifest display
  - Bundle builder UI - **Web only (admin)**
  - Promotion dashboard - **Mobile**: Promotion viewer
  - Ranking algorithm A/B testing
  - Hybrid visibility modes - **Mobile**: Mode-aware UI
  - Bundle analytics - **Mobile**: Analytics dashboard

9. **Affiliate Onboarding & Link Orchestration (Module 21)** - Phase 2:

  - Advanced KYC automation - **Web**: Automated verification workflows
  - Trust score optimization - **Web**: Score analytics
  - Shared Payment Token (SPT) integration - **All platforms**: SPT support
  - Commission analytics dashboard - **Web + Mobile**: Partner dashboard
  - Affiliate performance tracking - **Web**: Performance metrics

10. **The Curation Picker (Module 22)** - Phase 2:

  - Advanced margin optimization - **Web**: AI-powered suggestions
  - Bundle validation with Time-Chain - **Web**: Real-time validation
  - Canvas collaboration - **Web**: Multi-user editing
  - Template library - **Web**: Pre-built bundle templates
  - Export/import functionality - **Web**: Bundle sharing

11. **Standing Intent Engine (Module 23)** - Phase 2:

  - Advanced condition types - **All platforms**: Weather, calendar, inventory, price
  - Multi-condition logic - **Orchestrator**: AND/OR condition combinations
  - Trust level automation - **All platforms**: Auto-proceed based on trust
  - Intent templates - **Web**: Pre-built intent patterns
  - Intent analytics - **Web + Mobile**: Performance tracking
  - Recurring intents - **Orchestrator**: Repeat on schedule

12. **Omnichannel Message Broker & HITL Escalation (Module 24)** - Phase 2:

  - Dynamic suggestion engine - **All platforms**: Enrich counter-offers with metadata
  - Vision AI integration - **OpenAI Vision**: Photo analysis for quality check
  - Silent monitoring - **Web**: Admin can watch without interrupting
  - Intervention queue - **Web**: High-urgency task prioritization
  - Preference persistence - **All platforms**: Channel preference management
  - Advanced escalation logic - **All platforms**: Time-Chain urgency detection
  - Multi-day negotiations - **Durable Functions**: Long-running negotiations

9. Reverse logistics (Module 17):

  - **Web**: Return request interface
  - **Mobile**: Return request with photo upload
  - **PWA**: Offline return request queue

10. Admin command center (Module 18):

  - **Web**: Full admin dashboard
  - **Mobile**: Admin mobile app for on-the-go monitoring
  - **PWA**: Admin PWA for quick access
