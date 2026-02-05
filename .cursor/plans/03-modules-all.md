---
name: AI Universal Service Orchestrator Platform - All Modules
overview: Complete module implementation details for all 25 modules
todos: []
---

# Module Implementation Details

> **Note**: This file contains all module definitions from the original plan. Due to its size (~4,300 lines), it has been extracted from the main plan file. All modules are included here with their complete implementation details, database schemas, API endpoints, and code examples.

## AI Agents Integration (Core Platform)

**Purpose**: Entry point for AI chat agents (ChatGPT, Gemini). Orchestrating multi-vendor orders via a single chat-first API.

**Service**: `orchestrator-service`  
**Endpoint**: `POST /api/v1/chat` – Resolves intent (Module 4) + discovers products (Module 1) in one call.

**Integration points**:
- Intent Service (Module 4) – Azure OpenAI for natural language → structured intent
- Discovery Service (Module 1) – Product discovery with JSON-LD and Adaptive Cards

**Environment variables**:
- `AZURE_OPENAI_*` (via Intent Service)
- `DISCOVERY_SERVICE_URL`, `INTENT_SERVICE_URL` (orchestrator config)
- Future: `GOOGLE_AI_*` for Gemini direct integration

**Status**: MVP implemented. Orchestrator chat flow (Intent → Discovery) in place.

**Plan reference**: See [02-architecture.md](./02-architecture.md) for Chat-First standards; [07-project-operations.md](./07-project-operations.md) for project structure.

---

## Module List

1. **Module 1**: Multi-Protocol Scout Engine
2. **Module 2**: Legacy Adapter Layer (Phase 2)
3. **Module 3**: AI-First Discoverability (Phase 2)
4. **Module 4**: Intent Resolver
5. **Module 5**: Time-Chain Resolver (Patent Candidate)
6. **Module 6**: Autonomous Re-Sourcing (MVP Critical: Live Demo of Autonomous Recovery)
7. **Module 7**: Premium Registry & Capability Mapping
8. **Module 8**: Virtual Proofing Engine (Phase 2)
9. **Module 9**: Generic Capability Portal
10. **Module 10**: HubNegotiator & Bidding (Phase 2)
11. **Module 11**: Multi-Vendor Task Queue (Phase 2)
12. **Module 12**: Multi-Party Support Hub
13. **Module 13**: Hybrid Response Logic (Phase 2)
14. **Module 14**: Status Narrator
15. **Module 15**: Atomic Multi-Checkout
16. **Module 16**: Transaction & Escrow Manager
17. **Module 17**: Reverse Logistics (Phase 3)
18. **Module 18**: Admin Command Center (Phase 3)
19. **Module 19**: Storefront Customization & White-Label Platform
20. **Module 20**: Curation, Merchandising & Promotion Engine
21. **Module 21**: Affiliate Onboarding & Link Orchestration
22. **Module 22**: The Curation Picker (Admin & Partner View)
23. **Module 23**: Standing Intent Engine (Durable Intent Engine)
24. **Module 24**: Omnichannel Message Broker & HITL Escalation
25. **Module 25**: The Partner Simulator (MVP Critical)

---

## Module Implementation Details

### Module 1: Multi-Protocol Scout Engine

**Technology**: Azure Container Apps (FastAPI) + Supabase pgvector

**Implementation**:

- `discovery-service/` - Main service (FastAPI on Container Apps)
  - `protocols/ucp-adapter.py` - Google UCP parser
  - `protocols/acp-adapter.py` - OpenAI ACP parser
  - `scout-engine.py` - Unified discovery interface
  - `manifest-cache.py` - Cache manifest files in Supabase
  - `semantic-search.py` - pgvector-based product matching
  - `api/chat-first.py` - Chat-First API endpoints with JSON-LD
  - `adaptive-cards/product-card.py` - Product Adaptive Card generator
  - `webhooks/inventory-webhook.py` - Inventory update webhooks
- **Why Container Apps**: Handles high-concurrency "Scout" bursts better than Functions. Supports long-running WebSocket connections for real-time product feeds. Scales to zero when idle (cost-effective).
- Cache product feeds in Supabase PostgreSQL with TTL
- **Why pgvector**: Native PostgreSQL extension for semantic search. More cost-effective than Azure Cognitive Search. Easier to manage for small teams.

**Chat-First Requirements**:

1. **API Response Format**:
```python
@router.get("/api/v1/discover")
async def discover_products(intent: str, location: Optional[str] = None):
    products = await scout_engine.search(intent, location)

    return {
        "data": {
"products": products,
"count": len(products)
        },
        "machine_readable": {
"@context": "https://schema.org",
"@type": "ItemList",
"itemListElement": [
{
"@type": "Product",
"name": product.name,
"description": product.description,
"offers": {
"@type": "Offer",
"price": product.price,
"priceCurrency": "USD"
},
"capabilities": product.capabilities
} for product in products
]
        },
        "adaptive_card": generate_product_card(products),
        "metadata": {
"api_version": "v1",
"timestamp": datetime.utcnow().isoformat(),
"request_id": str(uuid.uuid4())
        }
    }
```

2. **Adaptive Card Generation**:

  - Product Card with image, price, capabilities
  - "Add to Bundle" action button
  - "View Details" action button
  - Supports Gemini Dynamic View and ChatGPT Instant Checkout

3. **Webhook Support**:

  - Inventory updates trigger webhooks to chat threads
  - Real-time product availability notifications
  - Price change notifications

### Module 4: Intent Resolver

**Technology**: Azure OpenAI Service (GPT-4o) + Azure Container Apps (FastAPI)

**Implementation**:

- `intent-service/` (FastAPI on Container Apps)
  - `intent-parser.py` - LLM-based intent extraction using GPT-4o
  - `graph-builder.py` - Convert intent to Graph of Needs
  - `entity-extractor.py` - Extract products, dates, preferences
  - `api/chat-first.py` - Chat-First API with JSON-LD Intent schema
  - `adaptive-cards/intent-card.py` - Intent confirmation Adaptive Card
  - `standing-intent-creator.py` - Creates standing intents via API
- Use GPT-4o with function calling to structure intents
- Store intent graphs in Supabase PostgreSQL
- **Why Container Apps**: Better for streaming LLM responses to frontend via Vercel

**Chat-First Requirements**:

1. **API Response with JSON-LD Intent Schema**:
```json
{
  "data": {
    "intent_id": "uuid",
    "graph_of_needs": {...},
    "is_standing_intent": false
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "Intent",
    "description": "User intent description",
    "target": {
      "@type": "Product",
      "name": "Product name"
    },
    "temporal": {
      "@type": "TemporalEntity",
      "deadline": "2024-01-15T18:00:00Z"
    }
  },
  "adaptive_card": generate_intent_confirmation_card(intent_data)
}
```

2. **Standing Intent API**:

  - Detects condition-based intents
  - Creates standing intent via Module 23 API
  - Returns orchestration instance ID

### Module 5: Time-Chain Resolver (Patent Candidate)

**Technology**: Azure Container Apps (FastAPI) + Supabase PostgreSQL (PostGIS)

**Implementation**:

- `timechain-service/` (FastAPI on Container Apps)
  - `timechain-calculator.py` - Deterministic feasibility engine
  - `route-optimizer.py` - Multi-leg journey optimization
  - `synchronization-engine.py` - Hub arrival coordination
  - `conflict-simulator.py` - Real-time conflict detection and simulation
  - `proactive-suggestions.py` - Proactive alternative suggestions
- Use Azure Container Apps for long-running calculation workflows
- Store time-chains in Supabase PostgreSQL with PostGIS extension for geospatial indexing
- **Why Container Apps**: Better for CPU-intensive route optimization calculations

**Key Features**:

1. **Conflict Simulation**:

  - **Real-time Route Simulation**: When user adds item (e.g., "custom chocolates") to existing order, system immediately simulates driver's route
  - **Detour Impact Analysis**: Calculates time impact of detour
  - **Proactive Suggestions**: If conflict detected (e.g., makes user 15 minutes late for dinner), AI proactively suggests alternatives:
  - "Adding chocolates will make you 15 minutes late for dinner. Should I proceed, or would you like me to courier the chocolates separately to the restaurant?"
  - **No "Checking..." States**: System doesn't just say "checking..."; it immediately shows impact and alternatives

2. **Implementation**:
```python
# conflict-simulator.py
async def simulate_conflict(
    existing_order: Order,
    new_item: Item,
    pickup_location: Location,
    delivery_location: Location
) -> ConflictAnalysis:
    """
    Simulates adding new item to existing order and detects conflicts
    """
    # Get current route
    current_route = await route_optimizer.get_route(
        order_id=existing_order.id
    )

    # Calculate detour for new item
    detour_route = await route_optimizer.add_detour(
        base_route=current_route,
        detour_location=pickup_location,
        delivery_location=delivery_location
    )

    # Calculate time impact
    time_impact = detour_route.total_time - current_route.total_time

    # Check for conflicts with other legs
    conflicts = []
    for leg in existing_order.legs:
        if leg.deadline:
new_arrival_time = detour_route.arrival_time + time_impact
if new_arrival_time > leg.deadline:
conflicts.append({
'leg_id': leg.id,
'leg_name': leg.name,
'deadline': leg.deadline,
'new_arrival_time': new_arrival_time,
'delay_minutes': (new_arrival_time - leg.deadline).total_seconds() / 60
})

    # Generate proactive suggestions
    suggestions = []
    if conflicts:
        for conflict in conflicts:
if conflict['delay_minutes'] > 10:  # Significant delay
suggestions.append({
'type': 'separate_delivery',
'message': f"Adding {new_item.name} will make you {conflict['delay_minutes']:.0f} minutes late for {conflict['leg_name']}. Should I proceed, or would you like me to courier it separately?",
'alternative': {
'type': 'courier',
'item': new_item.name,
'delivery_location': conflict['leg_name'],
'estimated_cost': calculate_courier_cost(new_item, conflict['leg_name'])
}
})

    return ConflictAnalysis(
        has_conflict=len(conflicts) > 0,
        time_impact_minutes=time_impact.total_seconds() / 60,
        conflicts=conflicts,
        suggestions=suggestions,
        detour_route=detour_route
    )
```

3. **API Response**:
```json
{
  "data": {
    "conflict_detected": true,
    "time_impact_minutes": 15,
    "conflicts": [
      {
        "leg_id": "uuid",
        "leg_name": "Dinner Reservation",
        "deadline": "2024-01-15T19:00:00Z",
        "new_arrival_time": "2024-01-15T19:15:00Z",
        "delay_minutes": 15
      }
    ],
    "suggestions": [
      {
        "type": "separate_delivery",
        "message": "Adding chocolates will make you 15 minutes late for dinner. Should I proceed, or would you like me to courier the chocolates separately to the restaurant?",
        "alternative": {
          "type": "courier",
          "item": "Custom Chocolates",
          "delivery_location": "Restaurant",
          "estimated_cost": 12.99
        }
      }
    ]
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "ConflictAnalysis",
    "hasConflict": true,
    "timeImpact": "PT15M",
    "suggestions": [...]
  },
  "adaptive_card": {
    "type": "AdaptiveCard",
    "body": [
      {
        "type": "TextBlock",
        "text": "⚠️ Conflict Detected",
        "weight": "Bolder",
        "color": "Attention"
      },
      {
        "type": "TextBlock",
        "text": "Adding chocolates will make you 15 minutes late for dinner."
      },
      {
        "type": "FactSet",
        "facts": [
          {"title": "Delay", "value": "15 minutes"},
          {"title": "Dinner Reservation", "value": "7:00 PM"}
        ]
      }
    ],
    "actions": [
      {
        "type": "Action.Submit",
        "title": "Proceed Anyway",
        "data": {"action": "proceed"}
      },
      {
        "type": "Action.Submit",
        "title": "Courier Separately ($12.99)",
        "data": {"action": "separate_delivery"}
      }
    ]
  }
}
```


### Module 6: Autonomous Re-Sourcing (MVP Critical: Live Demo of Autonomous Recovery)

**Technology**: Azure Container Apps (FastAPI) + Supabase PostgreSQL + Azure OpenAI Service (GPT-4o) + Module 1 (Scout Engine) + Module 5 (Time-Chain Resolver) + Module 24 (Omnichannel Broker)

**Implementation**:

- `re-sourcing-service/` (FastAPI on Container Apps)
  - `autonomous-recovery.py` - Main autonomous recovery orchestrator
  - `partner-rejection-handler.py` - Handles partner "No" responses
  - `alternative-finder.py` - Finds alternatives using Scout Engine
  - `order-cancellation.py` - Cancels original orders
  - `bundle-updater.py` - Updates bundle with new items
  - `timeline-recalculator.py` - Recalculates Time-Chain with new timelines
  - `recovery-notifier.py` - Notifies user of recovery actions
- Integration with Module 1 (Scout Engine) for finding alternatives
- Integration with Module 5 (Time-Chain Resolver) for timeline recalculation
- Integration with Module 24 (Omnichannel Broker) for partner communication
- Integration with Module 14 (Status Narrator) for user updates

**Key Features**:

1. **Live Demo of Autonomous Recovery** (MVP Critical):

  - **Scenario**: User requests change (e.g., "pink flowers" instead of "red")
  - **Partner Rejection**: Partner says "No" via WhatsApp/SMS/API
  - **Automatic Recovery**: AI automatically:
  - Cancels original order
  - Finds alternative (pink flowers from another vendor)
  - Updates bundle
  - Recalculates timeline
  - Updates user with new timeline
  - **No Human Intervention**: Fully autonomous recovery

2. **Autonomous Recovery Workflow**:
```python
# autonomous-recovery.py
async def handle_autonomous_recovery(
    order_id: str,
    change_request: dict,
    partner_rejection: dict
) -> RecoveryResult:
    """
    Handles autonomous recovery when partner rejects change request
    """
    # Step 1: Parse change request
    original_item = change_request['original_item']  # e.g., "red flowers"
    requested_item = change_request['requested_item']  # e.g., "pink flowers"
    order_leg_id = change_request['order_leg_id']

    # Step 2: Cancel original order leg
    cancellation_result = await cancel_order_leg(
        order_id=order_id,
        leg_id=order_leg_id,
        reason="Partner unable to fulfill change request"
    )

    # Step 3: Find alternative using Scout Engine (Module 1)
    alternative = await find_alternative_item(
        original_item=original_item,
        requested_item=requested_item,
        location=change_request.get('location'),
        deadline=change_request.get('deadline')
    )

    if not alternative:
        # No alternative found - escalate to human
        return await escalate_to_human(
order_id=order_id,
reason="No alternative found for requested change"
        )

    # Step 4: Update bundle with new item
    updated_bundle = await update_bundle(
        order_id=order_id,
        removed_leg_id=order_leg_id,
        new_item=alternative,
        new_vendor=alternative['vendor']
    )

    # Step 5: Recalculate Time-Chain (Module 5)
    new_timeline = await recalculate_time_chain(
        order_id=order_id,
        updated_bundle=updated_bundle
    )

    # Step 6: Check if timeline changed
    timeline_changed = new_timeline['total_time'] != change_request['original_timeline']['total_time']
    delay_minutes = None
    if timeline_changed:
        delay_minutes = (new_timeline['total_time'] - change_request['original_timeline']['total_time']).total_seconds() / 60

    # Step 7: Notify user (Module 14)
    await notify_user_of_recovery(
        user_id=change_request['user_id'],
        order_id=order_id,
        original_item=original_item,
        new_item=alternative,
        timeline_changed=timeline_changed,
        delay_minutes=delay_minutes,
        new_timeline=new_timeline
    )

    return RecoveryResult(
        success=True,
        original_item=original_item,
        new_item=alternative,
        timeline_changed=timeline_changed,
        delay_minutes=delay_minutes,
        new_timeline=new_timeline
    )

# alternative-finder.py
async def find_alternative_item(
    original_item: dict,
    requested_item: str,
    location: dict,
    deadline: datetime
) -> dict:
    """
    Finds alternative item using Scout Engine (Module 1)
    """
    # Use Scout Engine to search for requested item
    search_results = await scout_engine.search(
        intent=requested_item,  # e.g., "pink flowers"
        location=location,
        filters={
'exclude_vendor_id': original_item['vendor_id'],  # Exclude original vendor
'price_range': {
'min': original_item['price'] * 0.8,  # Within 20% of original
'max': original_item['price'] * 1.2
},
'capabilities': original_item.get('capabilities', [])  # Match capabilities
        }
    )

    if not search_results:
        return None

    # Rank alternatives by:
    # 1. Availability (must be available before deadline)
    # 2. Price similarity
    # 3. Location proximity
    # 4. Vendor trust score

    ranked_alternatives = await rank_alternatives(
        alternatives=search_results,
        original_item=original_item,
        deadline=deadline,
        location=location
    )

    # Return best alternative
    return ranked_alternatives[0] if ranked_alternatives else None

# recovery-notifier.py
async def notify_user_of_recovery(
    user_id: str,
    order_id: str,
    original_item: dict,
    new_item: dict,
    timeline_changed: bool,
    delay_minutes: float,
    new_timeline: dict
) -> None:
    """
    Notifies user of autonomous recovery with Status Narrator (Module 14)
    """
    # Generate status message
    if timeline_changed and delay_minutes > 0:
        narrative = f"I've found {new_item['name']} from a different vendor to replace {original_item['name']}. The new timeline shows a {delay_minutes:.0f}-minute delay. Should I proceed?"
        agent_reasoning = f"because the original vendor couldn't fulfill your request, I automatically found an alternative and recalculated the timeline"
    elif timeline_changed and delay_minutes < 0:
        narrative = f"Great news! I found {new_item['name']} from a different vendor, and it actually improves your timeline by {abs(delay_minutes):.0f} minutes!"
        agent_reasoning = f"because the original vendor couldn't fulfill your request, I found a better alternative that actually speeds things up"
    else:
        narrative = f"I've found {new_item['name']} from a different vendor to replace {original_item['name']}. Your timeline remains unchanged."
        agent_reasoning = f"because the original vendor couldn't fulfill your request, I automatically found an alternative with the same timeline"

    # Generate Adaptive Card with timeline comparison
    adaptive_card = generate_recovery_card(
        original_item=original_item,
        new_item=new_item,
        timeline_changed=timeline_changed,
        delay_minutes=delay_minutes,
        new_timeline=new_timeline
    )

    # Send via Status Narrator (Module 14)
    await status_narrator.send_update(
        user_id=user_id,
        narrative=narrative,
        agent_reasoning=agent_reasoning,
        adaptive_card=adaptive_card,
        context={
'recovery_type': 'autonomous',
'original_item': original_item,
'new_item': new_item
        }
    )
```

3. **Database Schema**:
```sql
-- Autonomous recovery records
CREATE TABLE autonomous_recoveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  original_leg_id UUID REFERENCES order_legs(id),
  change_request JSONB NOT NULL, -- Original change request
  partner_rejection JSONB NOT NULL, -- Partner rejection details
  recovery_action VARCHAR(50) NOT NULL, -- 'cancelled', 'found_alternative', 'escalated'
  alternative_item_id UUID REFERENCES products(id),
  alternative_vendor_id UUID REFERENCES partners(id),
  timeline_changed BOOLEAN DEFAULT FALSE,
  delay_minutes DECIMAL(10,2), -- Positive = delay, Negative = improvement
  new_timeline JSONB,
  recovery_status VARCHAR(50) DEFAULT 'in_progress', -- 'in_progress', 'completed', 'failed', 'escalated'
  user_notified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Recovery attempts log
CREATE TABLE recovery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recovery_id UUID REFERENCES autonomous_recoveries(id),
  attempt_number INTEGER NOT NULL,
  alternative_found BOOLEAN DEFAULT FALSE,
  alternative_item_id UUID REFERENCES products(id),
  rejection_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

4. **Integration with Omnichannel Broker (Module 24)**:
```python
# Partner rejection handler
async def handle_partner_rejection(
    negotiation_id: str,
    rejection_data: dict
) -> None:
    """
    Handles partner rejection and triggers autonomous recovery
    """
    # Check if this is a change request rejection
    negotiation = await get_negotiation(negotiation_id)

    if negotiation['negotiation_type'] == 'product_change':
        # Trigger autonomous recovery
        recovery_result = await handle_autonomous_recovery(
order_id=negotiation['order_id'],
change_request=negotiation['original_request'],
partner_rejection=rejection_data
        )

        # Update negotiation status
        await update_negotiation(
negotiation_id=negotiation_id,
status='recovered_autonomously',
recovery_result=recovery_result
        )
```

5. **User Flow Example**:
```
1. User: "I want pink flowers instead of red"
2. System: Sends request to partner via WhatsApp
3. Partner: "No, we don't have pink flowers"
4. System (Autonomous Recovery):
   - Cancels red flowers order
   - Searches for pink flowers from other vendors
   - Finds pink flowers from Vendor B
   - Recalculates timeline
   - Updates user: "I've found pink flowers from a different vendor. Your timeline shows a 5-minute delay. Should I proceed?"
5. User: "Yes, proceed"
6. System: Confirms new order, updates bundle
```


**Integration Points**:

- **Module 1 (Scout Engine)**: Finds alternative items
- **Module 5 (Time-Chain Resolver)**: Recalculates timeline after change
- **Module 24 (Omnichannel Broker)**: Receives partner rejections
- **Module 14 (Status Narrator)**: Notifies user with reasoning
- **Module 15 (Payment)**: Handles refunds/cancellations
- **Module 16 (Escrow)**: Releases/cancels escrow for original order

**API Endpoints**:

```python
# Autonomous recovery
POST   /api/v1/recovery/trigger              # Trigger autonomous recovery
GET    /api/v1/recovery/{id}                 # Get recovery status
POST   /api/v1/recovery/{id}/approve         # User approves recovery
POST   /api/v1/recovery/{id}/reject          # User rejects recovery
```

**Why This Approach**:

- **Fully Autonomous**: No human intervention required
- **Seamless Experience**: User sees recovery happen automatically
- **Transparent**: User is notified with reasoning and timeline changes
- **Trust Building**: Shows system can self-heal
- **MVP Critical**: Demonstrates core value proposition

### Module 7: Premium Registry & Capability Mapping

**Technology**: Supabase PostgreSQL (single database for both)

**Implementation**:

- `registry-service/` (FastAPI on Container Apps)
  - `capability-mapper.py` - Tag-based capability system
  - `product-registry.py` - Premium blanks database
  - `service-matcher.py` - Match products to capabilities using pgvector
- Supabase PostgreSQL for both structured relationships and flexible JSON metadata (PostgreSQL JSONB)
- **Why Supabase**: Single database reduces complexity. JSONB columns provide flexibility of NoSQL with ACID guarantees of SQL.

### Module 8: Virtual Proofing Engine

**Technology**: Azure OpenAI DALL-E 3 + Azure Container Apps (FastAPI) + Supabase PostgreSQL + Clerk IAM

**Implementation**:

- `proofing-service/` (FastAPI on Container Apps)
  - `proof-generator.py` - High-fidelity preview generation
  - `image-processor.py` - Image processing and optimization
  - `identity-persistence.py` - Identity persistence from Clerk profile
  - `approval-handler.py` - Approval workflow management
  - `adaptive-cards/proof-card.py` - Proof preview Adaptive Card generator
- Azure OpenAI DALL-E 3 for image generation
- Supabase PostgreSQL for proof state management
- Clerk IAM for identity retrieval

**Key Features**:

1. **Identity Persistence**:

  - **Automatic Name Retrieval**: When user says "send it with my name," system automatically pulls `legal_name` or `display_name` from Clerk IAM profile
  - **No Duplicate Entry**: User doesn't need to type their name twice
  - **Profile Integration**: Seamlessly integrates with Clerk user metadata
  - **Fallback Logic**: If `legal_name` not available, uses `display_name`; if neither, prompts user

2. **Implementation**:
```python
# identity-persistence.py
async def get_user_name_for_customization(
    user_id: str,
    customization_type: str  # 'embroidery', 'engraving', 'gift_wrapping'
) -> str:
    """
    Retrieves user's name from Clerk profile for customization
    """
    # Get user from Clerk
    clerk_user = await clerk_client.users.get(user_id)

    # Try legal_name first
    if clerk_user.legal_name:
        return clerk_user.legal_name

    # Fallback to display_name
    if clerk_user.display_name:
        return clerk_user.display_name

    # Fallback to first_name + last_name
    if clerk_user.first_name and clerk_user.last_name:
        return f"{clerk_user.first_name} {clerk_user.last_name}"

    # Last resort: prompt user
    return None  # Will trigger user prompt

# proof-generator.py
async def generate_proof_with_identity(
    order_id: str,
    customization_request: dict,
    user_id: str
) -> Proof:
    """
    Generates proof with automatic identity persistence
    """
    # Check if customization requires name
    if customization_request.get('requires_name'):
        # Automatically retrieve from Clerk
        user_name = await get_user_name_for_customization(
user_id=user_id,
customization_type=customization_request['type']
        )

        if user_name:
# Auto-populate name in customization
customization_request['name'] = user_name
customization_request['identity_source'] = 'clerk_profile'
        else:
# Prompt user for name
return {
'requires_user_input': True,
'prompt': 'What name would you like to use for this customization?'
}

    # Generate proof with identity
    proof = await generate_proof(
        order_id=order_id,
        customization=customization_request
    )

    return proof
```

3. **Database Schema Enhancement**:
```sql
-- Add identity persistence to proof metadata
ALTER TABLE proof_states ADD COLUMN identity_data JSONB;
-- Example: {"name": "John Doe", "source": "clerk_profile", "field": "legal_name"}

-- Customization requests with identity
CREATE TABLE customization_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  proof_state_id UUID REFERENCES proof_states(id),
  customization_type VARCHAR(50), -- 'embroidery', 'engraving', 'gift_wrapping'
  customization_data JSONB NOT NULL, -- Includes name, text, etc.
  identity_source VARCHAR(50), -- 'clerk_profile', 'user_input', 'manual'
  identity_field VARCHAR(50), -- 'legal_name', 'display_name', 'first_name'
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

4. **User Experience**:

  - User: "Send it with my name"
  - System: Automatically retrieves name from Clerk profile
  - System: Generates proof with name pre-filled
  - User: Reviews proof (name already included)
  - No need to type name again

### Module 9: Generic Capability Portal

**Technology**: Next.js on Vercel + Azure Container Apps (FastAPI) + Supabase

**Implementation**:

- `partner-portal/` - Next.js application (deployed on Vercel)
        - `capability-registration.tsx` - UI for skill registration
  - `capacity-tracker.tsx` - Real-time capacity updates (Supabase Realtime)
  - `api/capabilities.ts` - REST API endpoints (Next.js API routes or Container Apps)
- Azure Container Apps for API backend (if needed beyond Next.js API routes)
- Supabase for partner profiles and capabilities with real-time subscriptions
- **Why Vercel**: Better edge delivery for global partner access. Built-in real-time capabilities.

### Module 14: Status Narrator

**Technology**: Azure OpenAI Service (GPT-4o) + Azure Container Apps (FastAPI) + Supabase PostgreSQL + Twilio WhatsApp Business API

**Implementation**:

- `status-narrator-service/` (FastAPI on Container Apps)
  - `narrator-engine.py` - Main status narration logic
  - `agent-reasoning.py` - Agent reasoning extraction and contextualization
  - `empathy-translator.py` - Translates logistics data into empathetic updates
  - `adaptive-cards/status-card.py` - Status update Adaptive Card generator with reasoning
  - `whatsapp-integration.py` - WhatsApp status message formatting
- Azure OpenAI GPT-4o for natural language generation
- Supabase PostgreSQL for status history
- Twilio WhatsApp Business API for status notifications

**Key Features**:

1. **Agent Reasoning in Status Updates**:

  - **Contextual "Why" Explanations**: Status updates include reasoning behind actions
  - **Example**: "I'm still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."
  - **Transparency**: Users understand not just what's happening, but why
  - **Trust Building**: Shows the agent is actively monitoring and making decisions

2. **Enhanced Status Narrator Activity**:
```python
# narrator-engine.py
async def generate_status_update(
    status_data: dict,
    context: dict  # Full context of the situation
) -> dict:
    """
    Generates empathetic status update with agent reasoning
    """
    # Extract key information
    current_status = status_data['status']
    previous_status = status_data.get('previous_status')
    context_info = context.get('context')

    # Generate base narrative
    base_narrative = await generate_base_narrative(
        status=current_status,
        order_data=status_data.get('order_data')
    )

    # Extract agent reasoning
    agent_reasoning = await extract_agent_reasoning(
        status_data=status_data,
        context=context
    )

    # Combine into empathetic narrative
    narrative = f"{base_narrative} {agent_reasoning}"

    return {
        'narrative': narrative,
        'reasoning': agent_reasoning,
        'context': context_info
    }

# agent-reasoning.py
async def extract_agent_reasoning(
    status_data: dict,
    context: dict
) -> str:
    """
    Extracts and formats agent reasoning for status updates
    """
    reasoning_parts = []

    # Check for waiting states
    if status_data.get('status') == 'waiting':
        waiting_reason = context.get('waiting_reason')
        if waiting_reason:
if waiting_reason.get('type') == 'condition':
# Example: Weather condition
condition = waiting_reason.get('condition')
current_value = waiting_reason.get('current_value')
target_value = waiting_reason.get('target_value')

if condition == 'weather':
reasoning_parts.append(
f"because the forecast for {waiting_reason.get('day')} just changed to '{current_value}'—monitoring for a clear window"
)
elif condition == 'inventory':
reasoning_parts.append(
f"because {current_value} is currently out of stock—monitoring for availability"
)

elif waiting_reason.get('type') == 'approval':
reasoning_parts.append(
f"waiting for your approval on {waiting_reason.get('item')}"
)

elif waiting_reason.get('type') == 'partner':
reasoning_parts.append(
f"waiting for {waiting_reason.get('partner_name')} to confirm availability"
)

    # Check for action states
    elif status_data.get('status') == 'action_taken':
        action_reason = context.get('action_reason')
        if action_reason:
reasoning_parts.append(
f"because {action_reason.get('reason')}"
)

    # Combine reasoning parts
    if reasoning_parts:
        return "I'm " + " ".join(reasoning_parts) + "."

    return ""

# Example usage
status_update = await generate_status_update(
    status_data={
        'status': 'waiting',
        'order_id': 'order_123'
    },
    context={
        'waiting_reason': {
'type': 'condition',
'condition': 'weather',
'day': 'Thursday',
'current_value': 'Rainy',
'target_value': 'Sunny'
        },
        'intent': 'buy_flowers'
    }
)
# Result: "I'm still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."
```

3. **Enhanced Progress Ledger Card with Reasoning**:
```python
# Enhanced Progress Ledger Card Generator with Agent Reasoning
def generate_progress_ledger_card(
    narrative: str,
    thought: str = None,
    if_then_logic: dict = None,
    agent_reasoning: str = None,
    context: dict = None
) -> dict:
    """
    Generates Progress Ledger Adaptive Card with If/Then logic and Agent Reasoning
    """
    card_body = [
        {
"type": "TextBlock",
"text": narrative,
"weight": "Bolder",
"size": "Medium",
"wrap": True
        }
    ]

    # Add Agent Reasoning section
    if agent_reasoning:
        reasoning_section = {
"type": "Container",
"style": "default",
"items": [
{
"type": "TextBlock",
"text": "🤔 Agent Reasoning",
"weight": "Bolder",
"color": "Accent",
"size": "Small"
},
{
"type": "TextBlock",
"text": agent_reasoning,
"wrap": True,
"size": "Small",
"spacing": "Small"
}
],
"spacing": "Medium"
        }
        card_body.append(reasoning_section)

    # Add If/Then logic visualization if present
    if if_then_logic:
        logic_map = {
"type": "Container",
"style": "emphasis",
"items": [
{
"type": "TextBlock",
"text": "🔍 Active Monitoring",
"weight": "Bolder",
"color": "Accent"
},
{
"type": "FactSet",
"facts": [
{
"title": "IF",
"value": format_condition(if_then_logic.get('condition'))
},
{
"title": "THEN",
"value": format_action(if_then_logic.get('action'))
}
]
}
]
        }
        card_body.append(logic_map)

    # Add thought (internal logic) if provided
    if thought:
        card_body.append({
"type": "TextBlock",
"text": f"💭 {thought}",
"size": "Small",
"color": "Default",
"isSubtle": True,
"wrap": True
        })

    # Add context details if provided
    if context and context.get('details'):
        context_section = {
"type": "Container",
"items": [
{
"type": "TextBlock",
"text": "📋 Context",
"weight": "Bolder",
"size": "Small",
"color": "Default"
},
{
"type": "FactSet",
"facts": [
{"title": key.replace('_', ' ').title(), "value": str(value)}
for key, value in context['details'].items()
]
}
],
"spacing": "Small"
        }
        card_body.append(context_section)

    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": card_body
    }
```

4. **Database Schema Enhancement**:
```sql
-- Add reasoning to status updates
ALTER TABLE status_updates ADD COLUMN agent_reasoning TEXT;
ALTER TABLE status_updates ADD COLUMN reasoning_context JSONB;

-- Enhanced standing_intent_logs with reasoning
ALTER TABLE standing_intent_logs ADD COLUMN agent_reasoning TEXT;
ALTER TABLE standing_intent_logs ADD COLUMN reasoning_context JSONB;

-- Example reasoning_context structure:
-- {
--   "waiting_reason": {
--     "type": "condition",
--     "condition": "weather",
--     "day": "Thursday",
--     "current_value": "Rainy",
--     "target_value": "Sunny"
--   },
--   "monitoring": true,
--   "next_check": "2024-01-15T10:00:00Z"
-- }
```

5. **Integration with Standing Intent (Module 23)**:
```python
# Enhanced status_narrator_activity with reasoning
def status_narrator_activity(context: df.DurableActivityContext):
    """
    Updates Progress Ledger with thoughts, narratives, and agent reasoning
    """
    status_data = context.get_input()

    # Extract context for reasoning
    context_info = status_data.get('context', {})

    # Generate agent reasoning
    agent_reasoning = extract_agent_reasoning(
        status_data=status_data,
        context=context_info
    )

    # Combine narrative with reasoning
    full_narrative = f"{status_data['narrative']} {agent_reasoning}"

    # Extract If/Then logic from metadata
    if_then_logic = status_data.get('metadata', {}).get('if_then_logic')

    # Write to standing_intent_logs
    write_progress_log(
        instance_id=status_data['instance_id'],
        thought=status_data.get('thought'),
        narrative=full_narrative,
        agent_reasoning=agent_reasoning,
        reasoning_context=context_info,
        metadata={
  **status_data.get('metadata', {}),
'if_then_logic': if_then_logic
        }
    )

    # Generate enhanced Progress Ledger Adaptive Card
    adaptive_card = generate_progress_ledger_card(
        narrative=status_data['narrative'],
        thought=status_data.get('thought'),
        if_then_logic=if_then_logic,
        agent_reasoning=agent_reasoning,
        context=context_info
    )

    # Send real-time update to user
    send_status_update(
        user_id=status_data.get('user_id'),
        narrative=full_narrative,
        adaptive_card=adaptive_card
    )

    return {'logged': True}
```

6. **Example Status Updates with Reasoning**:

  - **Waiting for Condition**: "I'm still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."
  - **Waiting for Inventory**: "I'm holding off on purchasing because the custom chocolates are currently out of stock—monitoring for availability."
  - **Waiting for Approval**: "I'm waiting for your approval on the purple limo before proceeding with the booking."
  - **Action Taken**: "I've switched to a different vendor because your preferred option doesn't have availability for your requested time."

**Integration Points**:

- **Module 23 (Standing Intent)**: Enhanced status narrator activity with reasoning
- **Module 5 (Time-Chain)**: Context for timing decisions
- **Module 12 (Support Hub)**: Status updates in chat threads
- **Module 24 (Omnichannel Broker)**: Status updates during negotiations

**Why This Approach**:

- **Transparency**: Users understand the "why" behind actions
- **Trust Building**: Shows active monitoring and decision-making
- **Reduced Anxiety**: Explains waiting states instead of just saying "checking..."
- **Better UX**: Contextual explanations make status updates more meaningful

### Module 19: Storefront Customization & White-Label Platform

**Technology**: Next.js on Vercel + Supabase PostgreSQL + Azure Blob Storage

**Implementation**:

- `storefront-platform/` - Multi-tenant storefront system
  - `storefront-builder/` - Visual storefront customization interface
  - `theme-engine/` - Runtime theme switching and customization
  - `component-library/` - Reusable, customizable React components
  - `api/storefronts.ts` - Storefront management API

**Design System Architecture**:

- `packages/design-system/` - Core design system package
  - `tokens/` - Design tokens (colors, typography, spacing, shadows, borders)
  - `components/` - Base components built on shadcn/ui
  - `themes/` - Theme definitions and presets
  - `utils/` - Theme utilities and helpers

**Key Features**:

1. **Design System Foundation**:

  - Design tokens defined in TypeScript/JSON
  - CSS custom properties for runtime theming
  - Component variants and composition patterns
  - Accessibility-first (WCAG 2.1 AA compliant)
  - Responsive design utilities

2. **Storefront Customization**:

  - **Visual Theme Editor**: Drag-and-drop interface for partners to customize:
  - Colors (primary, secondary, accent, background, text)
  - Typography (fonts, sizes, weights)
  - Spacing and layout
  - Component styles (buttons, cards, inputs)
  - Logo and branding assets
  - **Component Customization**: Partners can customize:
  - Product card layouts
  - Checkout flow
  - Navigation structure
  - Footer and header content
  - **White-Label Options**:
  - Custom domain support (CNAME)
  - Branded email templates
  - Custom favicon and meta tags
  - Partner-specific terms and privacy policies

3. **Multi-Tenant Architecture**:

  - Each partner gets isolated storefront instance
  - Theme stored in Supabase PostgreSQL (JSONB)
  - Assets stored in Azure Blob Storage (partner-specific containers)
  - Runtime theme injection via CSS variables

4. **Component Library Structure**:
   ```
   packages/design-system/
   ├── tokens/
   │   ├── colors.ts          # Color palette definitions
   │   ├── typography.ts      # Font families, sizes, weights
   │   ├── spacing.ts        # Spacing scale
   │   ├── shadows.ts        # Elevation system
   │   └── breakpoints.ts    # Responsive breakpoints
   ├── components/
   │   ├── Button/           # Customizable button component
   │   ├── Card/             # Product card component
   │   ├── Input/            # Form input component
   │   ├── Navigation/      # Navigation components
   │   └── ...               # All other components
   ├── themes/
   │   ├── default.ts        # Default theme
   │   ├── presets/         # Pre-built theme presets
   │   └── generator.ts     # Theme generation utilities
   └── utils/
       ├── theme-injector.ts # Runtime theme injection
       └── class-names.ts   # Utility class generators
   ```

5. **Customization API**:

  - REST API for theme CRUD operations
  - Theme preview endpoint
  - Theme export/import (JSON format)
  - Theme validation and sanitization

**Database Schema**:

```sql
-- Partner storefronts
CREATE TABLE storefronts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id),
  subdomain VARCHAR(100) UNIQUE,
  custom_domain VARCHAR(255) UNIQUE,
  theme_config JSONB, -- Theme customization data
  branding_config JSONB, -- Logo, favicon, meta tags
  layout_config JSONB, -- Component layout preferences
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Theme presets (pre-built themes partners can choose from)
CREATE TABLE theme_presets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100),
  description TEXT,
  theme_config JSONB,
  preview_image_url TEXT,
  is_public BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Storefront assets (logos, favicons, etc.)
CREATE TABLE storefront_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  storefront_id UUID REFERENCES storefronts(id),
  asset_type VARCHAR(50), -- 'logo', 'favicon', 'hero_image', etc.
  asset_url TEXT, -- Azure Blob Storage URL
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Implementation Details**:

- **Theme Engine**: CSS custom properties injected at runtime
  ```css
  :root[data-theme="partner-123"] {
    --color-primary: #3b82f6;
    --color-secondary: #8b5cf6;
    --font-family: 'Inter', sans-serif;
    --spacing-unit: 0.25rem;
    /* ... more tokens */
  }
  ```

- **Component Customization**: Props-based customization with theme context
  ```tsx
  <Button variant="primary" size="lg" theme={partnerTheme}>
    Add to Cart
  </Button>
  ```

- **Visual Editor**: React-based drag-and-drop interface
  - Real-time preview
  - Theme token editor
  - Component style overrides
  - Asset upload interface

- **White-Label Features**:
  - Custom domain routing (Vercel rewrites)
  - Partner-specific subdomain (partner-name.usoorchestrator.com)
  - Branded email templates (using Resend or SendGrid)
  - Custom meta tags and SEO settings

**Why This Approach**:

- **Design System First**: Ensures consistency across all storefronts
- **Scalable**: Multi-tenant architecture supports unlimited partners
- **Flexible**: Partners can customize extensively while maintaining design quality
- **Maintainable**: Single component library, multiple themes
- **Performance**: CSS variables for instant theme switching, no re-renders

### Module 20: Curation, Merchandising & Promotion Engine

**Technology**: Azure Container Apps (FastAPI) + Supabase PostgreSQL + Upstash Redis

**Implementation**:

- `curation-service/` (FastAPI on Container Apps)
  - `bundle-abstraction.py` - Curated bundle logic and metadata
  - `ranking-engine.py` - Boost engine for sorting and promotion
  - `meta-manifest-processor.py` - Pre-packaged experience manifest handler
  - `visibility-controller.py` - Admin visibility toggle management
  - `merchandising-api.py` - Merchandising operations API

**Key Features**:

1. **Curated Bundle Abstraction**:

  - **Abstracted SKUs**: Multiple vendors hidden behind single experience title
  - Example: "The Birthday Bash" = [Florist + Bakery + Balloon Service + Delivery]
  - **Bundle Metadata**: Overrides individual partner branding in Chat UI
  - Custom bundle name, description, images
  - Unified pricing display
  - Single checkout experience
  - **Bundle Composition**:
  - Define bundle structure (which vendors, in what order)
  - Set bundle-level pricing (can be different from sum of parts)
  - Bundle-level availability rules
  - Bundle-level customization options

2. **Ranking & Promotion Service**:

  - **Boost Engine**: Adjusts Scout Engine sorting based on admin-defined weights
  - **Sponsored**: Paid promotion boost (highest priority)
  - **Verified**: Quality/trust boost (moderate priority)
  - **Margin-optimized**: Revenue optimization boost (calculated priority)
  - **Featured Partner Status**: Prioritizes vendor's Manifest over organic results
  - Featured partners appear in "Featured" section
  - Featured partners get priority in search results
  - Featured partners can have custom placement
  - **Ranking Algorithm**:
     ```
     Final Score = (
       Relevance Score * 0.4 +
       Boost Score * 0.3 +
       Quality Score * 0.2 +
       Margin Score * 0.1
     )
     ```

  - **Dynamic Weighting**: Admin can adjust weight percentages in real-time

3. **Meta-Partner Manifests**:

  - **Pre-Packaged Experience Manifests**: Partners submit complete experiences
  - Example: Limo + Dining as single unit
  - Example: Spa Day = [Massage + Facial + Lunch + Transportation]
  - **Single-Leg Task for Orchestrator**: System treats as one task
  - Simplified Time-Chain calculation
  - Single payment transaction
  - Unified delivery tracking
  - **Multi-Event Task for User**: User sees multiple components
  - "Your Spa Day includes: Massage at 2 PM, Facial at 3 PM, Lunch at 4 PM"
  - Individual component tracking
  - Component-level customization
  - **Manifest Structure**:
     ```json
     {
       "manifest_id": "spa-day-package",
       "partner_id": "luxury-spa-partner",
       "title": "Complete Spa Day Experience",
       "components": [
         {
"service_type": "massage",
"scheduled_time": "14:00",
"duration_minutes": 60,
"customization_options": {...}
         },
         {
"service_type": "facial",
"scheduled_time": "15:00",
"duration_minutes": 45
         },
         {
"service_type": "dining",
"scheduled_time": "16:00",
"duration_minutes": 90
         }
       ],
       "pricing": {
         "total": 299.99,
         "currency": "USD"
       },
       "availability_rules": {...}
     }
     ```


4. **Admin Visibility Toggles**:

  - **Transparent Marketplace Mode**: Shows all partners
  - User sees individual vendor names
  - User sees individual pricing
  - User can see bundle composition
  - User can customize individual components
  - **Concierge Mode**: Shows only bundle name and price
  - User sees curated bundle name only
  - User sees single total price
  - Vendor details hidden
  - Simplified experience
  - **Hybrid Mode**: Selective transparency
  - Show some vendors, hide others
  - Show bundle name but allow drill-down
  - Customizable per bundle

**Database Schema**:

```sql
-- Curated bundles
CREATE TABLE curated_bundles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_name VARCHAR(255) NOT NULL,
  bundle_slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  bundle_metadata JSONB, -- Custom branding, images, descriptions
  pricing_config JSONB, -- Bundle-level pricing rules
  composition JSONB, -- Array of vendor/service IDs in order
  visibility_mode VARCHAR(50) DEFAULT 'transparent', -- 'transparent', 'concierge', 'hybrid'
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bundle components (links vendors to bundles)
CREATE TABLE bundle_components (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES curated_bundles(id),
  vendor_id UUID REFERENCES partners(id),
  service_id UUID, -- Reference to vendor's service
  sequence_order INTEGER, -- Order in bundle execution
  is_required BOOLEAN DEFAULT TRUE,
  customization_allowed BOOLEAN DEFAULT FALSE,
  metadata JSONB, -- Component-specific overrides
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Promotion and ranking weights
CREATE TABLE promotion_weights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id),
  bundle_id UUID REFERENCES curated_bundles(id), -- NULL for partner-level
  promotion_type VARCHAR(50), -- 'sponsored', 'verified', 'margin_optimized', 'featured'
  weight_value DECIMAL(5,2) DEFAULT 1.0, -- Multiplier for ranking
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Featured partners
CREATE TABLE featured_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id),
  featured_until TIMESTAMPTZ,
  placement_priority INTEGER DEFAULT 0, -- Higher = more prominent
  featured_section VARCHAR(100), -- 'homepage', 'search_results', 'category'
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Meta-partner manifests (pre-packaged experiences)
CREATE TABLE meta_manifests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id),
  manifest_name VARCHAR(255) NOT NULL,
  manifest_slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  components JSONB NOT NULL, -- Array of service components
  pricing JSONB, -- Total pricing for manifest
  availability_rules JSONB,
  is_single_leg BOOLEAN DEFAULT TRUE, -- Treated as single task
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin visibility settings
CREATE TABLE visibility_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES curated_bundles(id),
  visibility_mode VARCHAR(50) NOT NULL, -- 'transparent', 'concierge', 'hybrid'
  show_vendors BOOLEAN DEFAULT TRUE,
  show_individual_pricing BOOLEAN DEFAULT TRUE,
  show_bundle_composition BOOLEAN DEFAULT TRUE,
  allow_component_customization BOOLEAN DEFAULT TRUE,
  custom_rules JSONB, -- Additional visibility rules
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ranking algorithm configuration
CREATE TABLE ranking_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_name VARCHAR(100) UNIQUE NOT NULL,
  relevance_weight DECIMAL(3,2) DEFAULT 0.4,
  boost_weight DECIMAL(3,2) DEFAULT 0.3,
  quality_weight DECIMAL(3,2) DEFAULT 0.2,
  margin_weight DECIMAL(3,2) DEFAULT 0.1,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Integration Points**:

1. **Module 1 (Discovery Service)**:

  - Ranking engine modifies Scout Engine results
  - Featured partners injected into search results
  - Curated bundles appear as single results

2. **Module 4 (Intent Resolver)**:

  - Intent resolver can suggest curated bundles
  - Bundle matching based on user intent

3. **Module 5 (Time-Chain Resolver)**:

  - Meta-manifests treated as single-leg tasks
  - Simplified time-chain calculation for bundles

4. **Module 12 (Support Hub)**:

  - Bundle metadata overrides partner branding in chat
  - Concierge mode affects chat UI display

5. **Module 15 (Payment)**:

  - Bundle-level pricing in checkout
  - Single transaction for curated bundles

**API Endpoints**:

```python
# Bundle management
POST   /api/v1/bundles                    # Create curated bundle
GET    /api/v1/bundles                    # List bundles
GET    /api/v1/bundles/{id}               # Get bundle details
PUT    /api/v1/bundles/{id}               # Update bundle
DELETE /api/v1/bundles/{id}               # Delete bundle

# Promotion management
POST   /api/v1/promotions                 # Create promotion
GET    /api/v1/promotions                  # List promotions
PUT    /api/v1/promotions/{id}            # Update promotion
POST   /api/v1/partners/{id}/feature      # Feature a partner

# Ranking configuration
GET    /api/v1/ranking/config              # Get ranking config
PUT    /api/v1/ranking/config             # Update ranking weights
POST   /api/v1/ranking/boost               # Apply boost to result

# Meta-manifests
POST   /api/v1/manifests                  # Submit meta-manifest
GET    /api/v1/manifests                  # List manifests
GET    /api/v1/manifests/{id}             # Get manifest details

# Visibility settings
GET    /api/v1/visibility/{bundle_id}     # Get visibility settings
PUT    /api/v1/visibility/{bundle_id}      # Update visibility mode
```

**Admin UI Components**:

1. **Bundle Builder**:

  - Drag-and-drop interface to compose bundles
  - Vendor selection and sequencing
  - Bundle metadata editor
  - Pricing configuration
  - Preview mode

2. **Promotion Dashboard**:

  - Partner promotion management
  - Featured partner controls
  - Boost weight sliders
  - Promotion calendar view

3. **Ranking Configuration**:

  - Algorithm weight adjustment
  - Real-time ranking preview
  - A/B testing setup

4. **Visibility Toggle**:

  - Mode switcher (Transparent/Concierge/Hybrid)
  - Per-bundle visibility rules
  - Preview for each mode

**Implementation Details**:

- **Boost Engine**: Uses Upstash Redis for fast ranking calculations
- **Bundle Abstraction**: Metadata stored in Supabase JSONB for flexibility
- **Ranking Cache**: Cache ranking results in Redis for performance
- **Real-time Updates**: WebSocket updates when admin changes visibility mode
- **Chat-First**: All ranking APIs include JSON-LD, Adaptive Cards for bundle results

**Why This Approach**:

- **Flexible Merchandising**: Supports both transparent and concierge experiences
- **Revenue Optimization**: Margin-based ranking maximizes platform revenue
- **Partner Empowerment**: Partners can create pre-packaged experiences
- **Admin Control**: Fine-grained control over marketplace visibility
- **Scalable**: Redis-based ranking handles high query volumes

### Module 21: Affiliate Onboarding & Link Orchestration

**Technology**: Azure Container Apps (FastAPI) + Supabase PostgreSQL + Clerk + Azure Blob Storage

**Implementation**:

- `affiliate-service/` (FastAPI on Container Apps)
  - `affiliate-onboarding.py` - Self-service registration portal
  - `link-wrapper.py` - Tracking ID injection service
  - `kyc-verification.py` - Automated business verification
  - `trust-scoring.py` - Trust score calculation
  - `commission-calculator.py` - CPA/CPE commission logic

**Key Features**:

1. **Self-Service Registration Portal**:

  - Local businesses (e.g., "Texas Limo Co") or individual creators can register
  - Must provide UCP/ACP Manifest URL
  - Set commission rates (CPA - Cost Per Acquisition, CPE - Cost Per Engagement)
  - Business information and contact details
  - Payment account setup (Stripe Connect)

2. **Affiliate Link Wrapper**:

  - **Tracking ID Injection**: Automatically injects platform Tracking IDs into Scout results
  - **Protocol-Native Retailers**: Uses Shared Payment Tokens (SPTs) for agent-native retailers
  - **Non-Protocol Retailers**: Uses deep-linking for traditional web stores
  - **Link Format**: `https://retailer.com/product?affiliate_id={tracking_id}&ref=uso`
  - **Token Format**: SPT contains tracking ID in metadata

3. **KYC & Trust Scoring**:

  - **Automated Verification**:
  - Business license verification (API integration with state databases)
  - Insurance verification (policy number validation)
  - Tax ID verification (EIN/SSN validation)
  - Identity verification (for individual creators)
  - **Trust Score Calculation**:
  - Business license: +20 points
  - Insurance: +15 points
  - Tax ID verified: +10 points
  - Positive reviews: +5 points per review
  - On-time delivery rate: +1 point per percentage
  - Trust score range: 0-100
  - **White Glove Threshold**: Minimum 70 trust score for "White Glove" status

4. **Delegated Commission Logic**:

  - Platform takes percentage of total Bundle price
  - Commission split:
  - Affiliate commission (to retailer)
  - Platform orchestration fee
  - Partner service fee (if applicable)
  - Real-time commission calculation

**Database Schema**:

```sql
-- Affiliate partners
CREATE TABLE affiliate_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id), -- Clerk user ID
  business_name VARCHAR(255) NOT NULL,
  business_type VARCHAR(100), -- 'business', 'individual_creator'
  manifest_url TEXT NOT NULL, -- UCP/ACP Manifest URL
  manifest_type VARCHAR(50), -- 'ucp', 'acp', 'legacy'
  commission_type VARCHAR(50), -- 'cpa', 'cpe', 'hybrid'
  commission_rate DECIMAL(5,2) NOT NULL, -- Percentage or fixed amount
  tracking_id VARCHAR(100) UNIQUE NOT NULL, -- Platform tracking ID
  trust_score INTEGER DEFAULT 0, -- 0-100
  is_white_glove BOOLEAN DEFAULT FALSE, -- Requires trust_score >= 70
  kyc_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'verified', 'rejected'
  is_active BOOLEAN DEFAULT FALSE, -- Only active after KYC verification
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- KYC verification records
CREATE TABLE kyc_verifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  affiliate_partner_id UUID REFERENCES affiliate_partners(id),
  verification_type VARCHAR(50), -- 'business_license', 'insurance', 'tax_id', 'identity'
  verification_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'verified', 'rejected'
  verification_data JSONB, -- Verification details
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES users(id), -- System or admin
  verification_method VARCHAR(50), -- 'automated', 'manual', 'api'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trust score history
CREATE TABLE trust_score_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  affiliate_partner_id UUID REFERENCES affiliate_partners(id),
  score INTEGER NOT NULL,
  score_components JSONB, -- Breakdown of score calculation
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Affiliate link tracking
CREATE TABLE affiliate_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  affiliate_partner_id UUID REFERENCES affiliate_partners(id),
  product_id UUID REFERENCES products(id),
  original_url TEXT NOT NULL,
  wrapped_url TEXT NOT NULL, -- With tracking ID
  spt_token TEXT, -- Shared Payment Token (if applicable)
  link_type VARCHAR(50), -- 'deep_link', 'spt', 'direct'
  click_count INTEGER DEFAULT 0,
  conversion_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Commission transactions
CREATE TABLE commission_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  affiliate_partner_id UUID REFERENCES affiliate_partners(id),
  commission_type VARCHAR(50), -- 'cpa', 'cpe'
  commission_amount DECIMAL(10,2) NOT NULL,
  total_order_value DECIMAL(10,2) NOT NULL,
  commission_rate DECIMAL(5,2) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'paid', 'cancelled'
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Integration Points**:

1. **Module 1 (Scout Engine)**:

  - Affiliate Link Wrapper injects tracking IDs into all Scout results
  - Filters results by affiliate partner trust score
  - Prioritizes White Glove affiliates

2. **Module 4 (Intent Resolver)**:

  - Can suggest affiliate bundles based on commission optimization
  - Considers trust scores when recommending partners

3. **Module 15 (Payment)**:

  - Commission Calculator calculates split payments
  - Delegated commission logic applied
  - Affiliate commissions paid separately

4. **Module 20 (Curation Engine)**:

  - Margin Optimizer uses affiliate commission rates
  - Affiliate partners can be locked into bundles

**API Endpoints**:

```python
# Affiliate onboarding
POST   /api/v1/affiliates/register              # Self-service registration
GET    /api/v1/affiliates/{id}                   # Get affiliate details
PUT    /api/v1/affiliates/{id}                   # Update affiliate info
POST   /api/v1/affiliates/{id}/verify            # Trigger KYC verification

# Link orchestration
POST   /api/v1/links/wrap                       # Wrap affiliate link
GET    /api/v1/links/{id}/stats                  # Link statistics
POST   /api/v1/links/track                        # Track link click

# Commission management
GET    /api/v1/commissions                        # List commissions
GET    /api/v1/commissions/{id}                   # Get commission details
POST   /api/v1/commissions/{id}/pay               # Pay commission
```

**Implementation Details**:

- **Link Wrapper Service**: Intercepts all Scout Engine results, injects tracking IDs
- **KYC Automation**: Integrates with state business license APIs, insurance verification APIs
- **Trust Score Updates**: Real-time updates based on performance metrics
- **Commission Tracking**: All affiliate clicks and conversions tracked in real-time
- **Chat-First**: Affiliate APIs include JSON-LD, Adaptive Cards for affiliate partner info

**Why This Approach**:

- **Scalable Onboarding**: Self-service reduces admin overhead
- **Automated Verification**: KYC automation ensures compliance
- **Revenue Optimization**: Commission tracking maximizes affiliate revenue
- **Trust-Based**: White Glove threshold ensures quality partners

### Module 22: The Curation Picker (Admin & Partner View)

**Technology**: Next.js on Vercel + Azure Container Apps (FastAPI) + Supabase PostgreSQL + pgvector

**Implementation**:

- `curation-picker/` (Next.js application on Vercel)
  - `visual-canvas.tsx` - Drag-and-drop bundle builder
  - `product-picker.tsx` - Product search and selection UI
  - `margin-calculator.tsx` - Real-time margin optimization
  - `bundle-lock.tsx` - Partner locking functionality

- `curation-picker-api/` (FastAPI on Container Apps)
  - `canvas-manager.py` - Canvas state management
  - `product-search.py` - Semantic product search
  - `margin-optimizer.py` - Real-time margin calculation
  - `bundle-validator.py` - Bundle feasibility validation

**Key Features**:

1. **Visual Bundle Canvas**:

  - **Drag-and-Drop Interface**: Admins or verified Partners browse global Scout database
  - **Product Picker**: Search and select items from Supabase/pgvector store
  - **Visual Composition**: Literally "drag and drop" items into a bundle plan
  - **Example Workflow**:
  - Pick "Designer Suit" from Retailer
  - Add "On-site Tailoring" from Local Artisan
  - Add "Priority Courier" for delivery
  - Arrange in sequence
  - Set timing and dependencies

2. **Margin Optimizer**:

  - **Real-time Calculator**: Shows total commission/margin for bundle
  - **Based on Affiliate Rates**: Uses Module 21 affiliate commission rates
  - **Breakdown Display**:
  - Individual item commissions
  - Platform orchestration fee
  - Total margin
  - Recommended pricing
  - **Optimization Suggestions**: Suggests alternative products for better margins

3. **Partner Locking**:

  - **Lock Partners**: Certain partners can be locked into a bundle
  - **Example**: "This bundle ONLY uses Texas Limo Co"
  - **Lock Types**:
  - **Hard Lock**: Partner cannot be swapped (even in re-sourcing)
  - **Soft Lock**: Partner preferred but can be swapped if needed
  - **Service Lock**: Lock specific service type to specific partner
  - **Lock Reasoning**: Admin can specify why partner is locked

4. **Bundle Validation**:

  - **Feasibility Check**: Validates bundle against Time-Chain Resolver
  - **Inventory Check**: Verifies all items are in stock
  - **Capability Matching**: Ensures products match required capabilities
  - **Pricing Validation**: Ensures pricing is within acceptable ranges

**Database Schema**:

```sql
-- Curation canvas sessions
CREATE TABLE curation_canvas_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_by UUID REFERENCES users(id), -- Admin or Partner
  session_name VARCHAR(255),
  bundle_id UUID REFERENCES curated_bundles(id), -- If saved as bundle
  canvas_state JSONB NOT NULL, -- Current canvas state
  is_draft BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Canvas items (products/services on canvas)
CREATE TABLE canvas_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canvas_session_id UUID REFERENCES curation_canvas_sessions(id),
  product_id UUID REFERENCES products(id),
  partner_id UUID REFERENCES partners(id),
  item_type VARCHAR(50), -- 'product', 'service', 'delivery'
  position_x DECIMAL(10,2), -- Canvas X position
  position_y DECIMAL(10,2), -- Canvas Y position
  sequence_order INTEGER, -- Order in bundle execution
  is_locked BOOLEAN DEFAULT FALSE, -- Partner locked
  lock_type VARCHAR(50), -- 'hard', 'soft', 'service'
  lock_reason TEXT,
  metadata JSONB, -- Customization, timing, etc.
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Margin calculations (snapshots)
CREATE TABLE margin_calculations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canvas_session_id UUID REFERENCES curation_canvas_sessions(id),
  total_bundle_price DECIMAL(10,2) NOT NULL,
  total_commissions DECIMAL(10,2) NOT NULL,
  platform_fee DECIMAL(10,2) NOT NULL,
  total_margin DECIMAL(10,2) NOT NULL,
  margin_percentage DECIMAL(5,2) NOT NULL,
  calculation_breakdown JSONB, -- Detailed breakdown
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product search cache (for performance)
CREATE TABLE product_search_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  search_query TEXT NOT NULL,
  search_vector vector(1536), -- pgvector embedding
  results JSONB NOT NULL, -- Cached results
  cache_hit_count INTEGER DEFAULT 0,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**UI Components**:

1. **Visual Canvas**:

  - Drag-and-drop interface (React DnD or similar)
  - Product cards with images and details
  - Connection lines showing sequence
  - Timeline visualization
  - Real-time validation feedback

2. **Product Picker Sidebar**:

  - Semantic search (pgvector)
  - Filters (category, price, capabilities)
  - Product preview cards
  - "Add to Canvas" button

3. **Margin Calculator Panel**:

  - Real-time margin display
  - Breakdown by item
  - Optimization suggestions
  - Pricing recommendations

4. **Partner Lock Controls**:

  - Lock/unlock toggle per item
  - Lock type selector
  - Lock reason input
  - Visual lock indicator on canvas

**Integration Points**:

1. **Module 1 (Scout Engine)**:

  - Product Picker queries Scout Engine database
  - Uses pgvector for semantic search
  - Real-time inventory checks

2. **Module 21 (Affiliate)**:

  - Margin Optimizer uses affiliate commission rates
  - Tracks affiliate partners in bundle
  - Calculates total affiliate commissions

3. **Module 5 (Time-Chain Resolver)**:

  - Bundle Validation uses Time-Chain Resolver
  - Checks feasibility before saving
  - Suggests timing adjustments

4. **Module 20 (Curation Engine)**:

  - Saved canvases become curated bundles
  - Partner locks enforced in bundle execution
  - Margin data used for ranking

**API Endpoints**:

```python
# Canvas management
POST   /api/v1/canvas/sessions                    # Create canvas session
GET    /api/v1/canvas/sessions/{id}               # Get canvas session
PUT    /api/v1/canvas/sessions/{id}               # Update canvas
DELETE /api/v1/canvas/sessions/{id}               # Delete canvas
POST   /api/v1/canvas/sessions/{id}/save          # Save as bundle

# Product search
POST   /api/v1/canvas/products/search              # Semantic product search
GET    /api/v1/canvas/products/{id}                # Get product details

# Margin calculation
POST   /api/v1/canvas/margin/calculate             # Calculate margin
GET    /api/v1/canvas/margin/{session_id}          # Get margin for session

# Partner locking
POST   /api/v1/canvas/items/{id}/lock              # Lock partner
DELETE /api/v1/canvas/items/{id}/lock              # Unlock partner

# Validation
POST   /api/v1/canvas/validate                     # Validate bundle feasibility
```

**Implementation Details**:

- **Canvas State Management**: Real-time sync via Supabase Realtime
- **Product Search**: pgvector semantic search with caching
- **Margin Calculation**: Real-time updates as items added/removed
- **Validation**: Async validation with progress indicators
- **Chat-First**: Canvas state exposed via API, Adaptive Cards for bundle previews

**Strategic Considerations**:

1. **Showing Partners vs. Products**:

  - **For Affiliates**: Must show partner (e.g., "Sold by Amazon") for legal/transparency
  - **For White-Glove Bundles**: Can "White Label" entire experience
  - User sees "The USO Anniversary Night"
  - Partners remain hidden as "service nodes" unless problem occurs

2. **Partner Locking Strategy**:

  - **Hard Lock**: Use for exclusive partnerships or quality guarantees
  - **Soft Lock**: Use for preferred partners with fallback options
  - **Service Lock**: Use when specific capability required

**Why This Approach**:

- **Visual Intuitive**: Drag-and-drop makes bundle creation accessible
- **Real-time Feedback**: Margin calculator provides instant insights
- **Flexible Locking**: Partner locks ensure quality and exclusivity
- **Integrated Workflow**: Seamlessly creates bundles for Module 20

### Module 23: Standing Intent Engine (Durable Intent Engine)

**Technology**: Azure Durable Functions (Python v2) + Supabase PostgreSQL + Azure Service Bus

**Implementation**:

- `standing-intent-service/` (Azure Durable Functions)
  - `orchestrator_function.py` - Durable Orchestrator (The "Brain")
  - `intent_watcher_activity.py` - Intent monitoring activity
  - `vendor_scout_activity.py` - Vendor scouting activity
  - `status_narrator_activity.py` - Progress ledger updates
  - `atomic_checkout_activity.py` - Purchase execution
  - `client_function.py` - Entry point for starting orchestrations
  - `external_event_handlers.py` - External event processors

**Key Features**:

1. **Durable Orchestration Pattern**:

  - **Stateful Execution**: Orchestrator can checkpoint and sleep for days
  - **Cost Efficient**: Only pays for execution time, not waiting time
  - **Event Sourcing**: Built-in state tracking via Durable Functions
  - **External Events**: Can wait for user approval, weather conditions, etc.

2. **Standing Intent Workflow**:

  - **Example**: "Send flowers & chocolates on the next sunny Thursday"
  - Orchestrator coordinates:

1. Scout vendors for flowers and chocolates
2. Wait for intent condition (sunny Thursday)
3. Wait for user approval (if required)
4. Execute atomic checkout

  - Can pause for days/weeks without cost

3. **Human-in-the-Loop (HITL)**:

  - **User Approval Events**: `context.wait_for_external_event("UserApproval")`
  - **Configurable Timeout**: 24 hours default, customizable
  - **Trust Level Logic**:
  - High trust: Auto-proceed if no response
  - Medium trust: Cancel if no response
  - Low trust: Always require approval
  - **Approval UI**: Customer can approve/reject via web/mobile

4. **Progress Ledger**:

  - **Thought Logs**: Internal logic and decisions
  - **Narrative Logs**: User-facing status updates
  - **Linked by Orchestration Instance ID**
  - **Real-time Updates**: Customer sees progress in real-time

**Database Schema**:

```sql
-- Standing intents
CREATE TABLE standing_intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  intent_description TEXT NOT NULL,
  intent_conditions JSONB NOT NULL, -- {"weather": "sunny", "day_of_week": "thursday", "time": "afternoon"}
  orchestration_instance_id VARCHAR(255) UNIQUE NOT NULL, -- Durable Functions instance ID
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'active', 'waiting_approval', 'executing', 'completed', 'cancelled'
  trust_level VARCHAR(50) DEFAULT 'medium', -- 'high', 'medium', 'low'
  requires_approval BOOLEAN DEFAULT TRUE,
  approval_timeout_hours INTEGER DEFAULT 24,
  max_wait_days INTEGER, -- Maximum days to wait before auto-cancellation
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ
);

-- Progress ledger (thoughts and narratives)
CREATE TABLE standing_intent_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID REFERENCES standing_intents(id),
  orchestration_instance_id VARCHAR(255) NOT NULL,
  log_type VARCHAR(50) NOT NULL, -- 'thought', 'narrative', 'activity', 'event'
  activity_name VARCHAR(255), -- Name of activity that generated log
  thought TEXT, -- Internal logic/decision
  narrative TEXT, -- User-facing status message
  metadata JSONB, -- Additional context
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Intent conditions tracking
CREATE TABLE intent_condition_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID REFERENCES standing_intents(id),
  condition_type VARCHAR(100) NOT NULL, -- 'weather', 'calendar', 'inventory', 'price'
  condition_value JSONB NOT NULL, -- Condition details
  check_result BOOLEAN, -- True if condition met
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  next_check_at TIMESTAMPTZ -- When to check again
);

-- External events (for HITL)
CREATE TABLE external_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchestration_instance_id VARCHAR(255) NOT NULL,
  event_name VARCHAR(100) NOT NULL, -- 'UserApproval', 'WeatherUpdate', 'InventoryAvailable'
  event_data JSONB,
  event_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processed', 'expired'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

-- Intent watcher schedule
CREATE TABLE intent_watcher_schedule (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID REFERENCES standing_intents(id),
  check_frequency_minutes INTEGER DEFAULT 60, -- How often to check conditions
  last_checked_at TIMESTAMPTZ,
  next_check_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE
);
```

**Durable Functions Implementation**:

```python
# orchestrator_function.py
import azure.functions as func
import azure.durable_functions as df

def orchestrator_function(context: df.DurableOrchestrationContext):
    """
    The "Brain" - Coordinates the Standing Intent workflow
    """
    # Get input data
    intent_data = context.get_input()
    user_id = intent_data['user_id']
    intent_description = intent_data['intent_description']
    conditions = intent_data['conditions']

    # Step 1: Scout vendors
    vendor_results = yield context.call_activity(
        'vendor_scout_activity',
        {
'intent': intent_description,
'conditions': conditions
        }
    )

    # Log progress
    yield context.call_activity(
        'status_narrator_activity',
        {
'instance_id': context.instance_id,
'narrative': f"Found {len(vendor_results)} vendors for your request!",
'thought': f"Scouted {len(vendor_results)} vendors matching criteria"
        }
    )

    # Step 2: Wait for intent condition (e.g., sunny Thursday)
    if conditions.get('wait_for_condition'):
        condition_met = yield context.wait_for_external_event('IntentConditionMet')

        if not condition_met:
# Condition not met, continue waiting or cancel
yield context.call_activity(
'status_narrator_activity',
{
'instance_id': context.instance_id,
'narrative': "Waiting for the perfect conditions...",
'thought': "Intent condition not yet met, continuing to wait"
}
)
return

    # Step 3: Check if user approval required
    if intent_data.get('requires_approval', True):
        approval_timeout = intent_data.get('approval_timeout_hours', 24)

        # Wait for user approval with timeout
        approval_result = yield context.wait_for_external_event(
'UserApproval',
timeout=timedelta(hours=approval_timeout)
        )

        if approval_result is None:
# Timeout - check trust level
trust_level = intent_data.get('trust_level', 'medium')
if trust_level == 'high':
# Auto-proceed
yield context.call_activity(
'status_narrator_activity',
{
'instance_id': context.instance_id,
'narrative': "Proceeding automatically based on your preferences",
'thought': f"Timeout reached, trust level {trust_level}, auto-proceeding"
}
)
else:
# Cancel
yield context.call_activity(
'status_narrator_activity',
{
'instance_id': context.instance_id,
'narrative': "Intent cancelled - no approval received",
'thought': f"Timeout reached, trust level {trust_level}, cancelling"
}
)
return

        if not approval_result.get('approved', False):
# User rejected
yield context.call_activity(
'status_narrator_activity',
{
'instance_id': context.instance_id,
'narrative': "Intent cancelled as requested",
'thought': "User rejected the intent"
}
)
return

    # Step 4: Execute atomic checkout
    checkout_result = yield context.call_activity(
        'atomic_checkout_activity',
        {
'vendor_results': vendor_results,
'user_id': user_id,
'intent_id': intent_data['intent_id']
        }
    )

    # Final status update
    yield context.call_activity(
        'status_narrator_activity',
        {
'instance_id': context.instance_id,
'narrative': "Your order has been placed successfully!",
'thought': f"Checkout completed: {checkout_result['order_id']}"
        }
    )

    return checkout_result

# Activity: Intent Watcher
def intent_watcher_activity(context: df.DurableActivityContext):
    """
    Timer-triggered function that checks intent conditions frequently
    """
    intent_data = context.get_input()
    conditions = intent_data['conditions']
    instance_id = intent_data['orchestration_instance_id']

    # Check weather condition
    if conditions.get('weather'):
        weather_met = check_weather_condition(conditions['weather'])
        if weather_met:
# Send external event to orchestrator
send_external_event(instance_id, 'IntentConditionMet', {'met': True})

    # Check calendar condition
    if conditions.get('day_of_week'):
        day_met = check_day_condition(conditions['day_of_week'])
        if day_met:
send_external_event(instance_id, 'IntentConditionMet', {'met': True})

    # Check inventory condition
    if conditions.get('inventory'):
        inventory_met = check_inventory_condition(conditions['inventory'])
        if inventory_met:
send_external_event(instance_id, 'IntentConditionMet', {'met': True})

    return {'checked': True}

# Activity: Vendor Scout
def vendor_scout_activity(context: df.DurableActivityContext):
    """
    Queries Scout Engine for specific inventory
    """
    scout_data = context.get_input()

    # Call Scout Engine API
    results = scout_engine.search(
        intent=scout_data['intent'],
        conditions=scout_data['conditions']
    )

    return results

# Activity: Status Narrator (Enhanced with Agent Reasoning)
def status_narrator_activity(context: df.DurableActivityContext):
    """
    Updates Progress Ledger with thoughts, narratives, and agent reasoning
    Enhanced with If/Then logic visualization and contextual "Why" explanations
    """
    status_data = context.get_input()

    # Extract context for reasoning
    context_info = status_data.get('context', {})

    # Generate agent reasoning (Module 14)
    agent_reasoning = extract_agent_reasoning(
        status_data=status_data,
        context=context_info
    )

    # Combine narrative with reasoning
    full_narrative = f"{status_data['narrative']} {agent_reasoning}"

    # Extract If/Then logic from metadata
    if_then_logic = status_data.get('metadata', {}).get('if_then_logic')

    # Write to standing_intent_logs
    write_progress_log(
        instance_id=status_data['instance_id'],
        thought=status_data.get('thought'),
        narrative=full_narrative,
        agent_reasoning=agent_reasoning,
        reasoning_context=context_info,
        metadata={
  **status_data.get('metadata', {}),
'if_then_logic': if_then_logic
        }
    )

    # Generate enhanced Progress Ledger Adaptive Card with reasoning
    adaptive_card = generate_progress_ledger_card(
        narrative=status_data['narrative'],
        thought=status_data.get('thought'),
        if_then_logic=if_then_logic,
        agent_reasoning=agent_reasoning,
        context=context_info
    )

    # Send real-time update to user
    send_status_update(
        user_id=status_data.get('user_id'),
        narrative=full_narrative,
        adaptive_card=adaptive_card
    )

    return {'logged': True}

# Enhanced Progress Ledger Card Generator with Agent Reasoning
def generate_progress_ledger_card(
    narrative: str,
    thought: str = None,
    if_then_logic: dict = None,
    agent_reasoning: str = None,
    context: dict = None
) -> dict:
    """
    Generates Progress Ledger Adaptive Card with If/Then logic visualization
    and Agent Reasoning (contextual "Why" explanations)
    """
    card_body = [
        {
"type": "TextBlock",
"text": narrative,
"weight": "Bolder",
"size": "Medium",
"wrap": True
        }
    ]

    # Add Agent Reasoning section (Module 14 enhancement)
    if agent_reasoning:
        reasoning_section = {
"type": "Container",
"style": "default",
"items": [
{
"type": "TextBlock",
"text": "🤔 Agent Reasoning",
"weight": "Bolder",
"color": "Accent",
"size": "Small"
},
{
"type": "TextBlock",
"text": agent_reasoning,
"wrap": True,
"size": "Small",
"spacing": "Small"
}
],
"spacing": "Medium"
        }
        card_body.append(reasoning_section)

    # Add If/Then logic visualization if present
    if if_then_logic:
        logic_map = {
"type": "Container",
"style": "emphasis",
"items": [
{
"type": "TextBlock",
"text": "🔍 Active Monitoring",
"weight": "Bolder",
"color": "Accent"
},
{
"type": "FactSet",
"facts": [
{
"title": "IF",
"value": format_condition(if_then_logic.get('condition'))
},
{
"title": "THEN",
"value": format_action(if_then_logic.get('action'))
}
]
}
]
        }
        card_body.append(logic_map)

    # Add thought (internal logic) if provided
    if thought:
        card_body.append({
"type": "TextBlock",
"text": f"💭 {thought}",
"size": "Small",
"color": "Default",
"isSubtle": True,
"wrap": True
        })

    # Add context details if provided
    if context and context.get('details'):
        context_section = {
"type": "Container",
"items": [
{
"type": "TextBlock",
"text": "📋 Context",
"weight": "Bolder",
"size": "Small",
"color": "Default"
},
{
"type": "FactSet",
"facts": [
{"title": key.replace('_', ' ').title(), "value": str(value)}
for key, value in context['details'].items()
]
}
],
"spacing": "Small"
        }
        card_body.append(context_section)

    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": card_body
    }

def format_condition(condition: dict) -> str:
    """
    Formats condition for display
    Example: {"weather": "sunny", "day_of_week": "thursday"}
    -> "Weather == Sunny AND Day == Thursday"
    """
    if not condition:
        return "N/A"

    parts = []
    for key, value in condition.items():
        key_formatted = key.replace('_', ' ').title()
        value_formatted = str(value).title()
        parts.append(f"{key_formatted} == {value_formatted}")

    return " AND ".join(parts)

def format_action(action: dict) -> str:
    """
    Formats action for display
    Example: {"type": "order", "item": "flowers"}
    -> "Order Flowers"
    """
    if not action:
        return "N/A"

    action_type = action.get('type', '').title()
    action_item = action.get('item', '')

    if action_item:
        return f"{action_type} {action_item.title()}"
    return action_type

# Agent Reasoning Extraction (Module 14)
def extract_agent_reasoning(
    status_data: dict,
    context: dict
) -> str:
    """
    Extracts and formats agent reasoning for status updates
    Provides contextual "Why" explanations
    """
    reasoning_parts = []

    # Check for waiting states
    if status_data.get('status') == 'waiting':
        waiting_reason = context.get('waiting_reason')
        if waiting_reason:
if waiting_reason.get('type') == 'condition':
# Example: Weather condition
condition = waiting_reason.get('condition')
current_value = waiting_reason.get('current_value')
target_value = waiting_reason.get('target_value')

if condition == 'weather':
day = waiting_reason.get('day', 'the requested day')
reasoning_parts.append(
f"because the forecast for {day} just changed to '{current_value}'—monitoring for a clear window"
)
elif condition == 'inventory':
reasoning_parts.append(
f"because {current_value} is currently out of stock—monitoring for availability"
)
elif condition == 'price':
reasoning_parts.append(
f"because the price is currently ${current_value}, waiting for it to drop to ${target_value}"
)

elif waiting_reason.get('type') == 'approval':
item = waiting_reason.get('item', 'this item')
reasoning_parts.append(
f"waiting for your approval on {item}"
)

elif waiting_reason.get('type') == 'partner':
partner_name = waiting_reason.get('partner_name', 'the partner')
reasoning_parts.append(
f"waiting for {partner_name} to confirm availability"
)

elif waiting_reason.get('type') == 'time':
reasoning_parts.append(
f"waiting for the right time window—{waiting_reason.get('reason', 'optimizing schedule')}"
)

    # Check for action states
    elif status_data.get('status') == 'action_taken':
        action_reason = context.get('action_reason')
        if action_reason:
reasoning_parts.append(
f"because {action_reason.get('reason')}"
)

    # Check for decision states
    elif status_data.get('status') == 'decision_made':
        decision_reason = context.get('decision_reason')
        if decision_reason:
reasoning_parts.append(
f"because {decision_reason.get('reason')}"
)

    # Combine reasoning parts
    if reasoning_parts:
        return "I'm " + " ".join(reasoning_parts) + "."

    return ""

# Example usage in orchestrator with Agent Reasoning
def orchestrator_function(context: df.DurableOrchestrationContext):
    # ... existing code ...

    # Check current weather condition
    current_weather = check_weather('Thursday')

    # Log progress with If/Then logic and Agent Reasoning
    yield context.call_activity(
        'status_narrator_activity',
        {
'instance_id': context.instance_id,
'narrative': "Still waiting to buy the flowers",
'thought': "Monitoring weather and day of week conditions",
'context': {
'waiting_reason': {
'type': 'condition',
'condition': 'weather',
'day': 'Thursday',
'current_value': current_weather,  # e.g., 'Rainy'
'target_value': 'Sunny'
},
'details': {
'forecast_changed': True,
'previous_forecast': 'Sunny',
'current_forecast': current_weather
}
},
'metadata': {
'if_then_logic': {
'condition': {
'weather': 'sunny',
'day_of_week': 'thursday'
},
'action': {
'type': 'order',
'item': 'flowers'
}
}
}
        }
    )
    # Result: "Still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."

# Client Function (Entry Point)
def client_function(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    """
    Accepts initial user message, starts orchestration
    """
    client = df.DurableOrchestrationClient(starter)

    # Parse request
    body = req.get_json()
    user_id = body['user_id']
    intent_description = body['intent_description']
    conditions = body.get('conditions', {})

    # Start orchestration
    instance_id = await client.start_new(
        'orchestrator_function',
        None,
        {
'user_id': user_id,
'intent_description': intent_description,
'conditions': conditions,
'requires_approval': body.get('requires_approval', True),
'trust_level': body.get('trust_level', 'medium'),
'approval_timeout_hours': body.get('approval_timeout_hours', 24)
        }
    )

    # Return instance ID for tracking
    return client.create_check_status_response(req, instance_id)
```

**Integration Points**:

1. **Module 1 (Scout Engine)**:

  - Vendor Scout Activity queries Scout Engine
  - Real-time inventory checks

2. **Module 4 (Intent Resolver)**:

  - Can create standing intents from user requests
  - Parses condition requirements

3. **Module 5 (Time-Chain Resolver)**:

  - Validates feasibility before creating standing intent
  - Checks timing constraints

4. **Module 14 (Status Narrator)**:

  - Status Narrator Activity updates user-facing narratives
  - Real-time progress updates

5. **Module 15 (Payment)**:

  - Atomic Checkout Activity executes payment
  - Uses existing checkout flow

**API Endpoints**:

```python
# Standing intent management
POST   /api/v1/standing-intents                    # Create standing intent
GET    /api/v1/standing-intents                    # List user's standing intents
GET    /api/v1/standing-intents/{id}               # Get intent details
PUT    /api/v1/standing-intents/{id}               # Update intent
DELETE /api/v1/standing-intents/{id}               # Cancel intent

# Progress tracking
GET    /api/v1/standing-intents/{id}/progress      # Get progress ledger
GET    /api/v1/standing-intents/{id}/status        # Get current status

# External events (HITL)
POST   /api/v1/standing-intents/{id}/approve       # User approval
POST   /api/v1/standing-intents/{id}/reject         # User rejection
POST   /api/v1/standing-intents/{id}/events         # Send external event
```

**Cost Efficiency**:

- **Waiting State**: $0 cost (orchestrator sleeps)
- **Activity Execution**: Pay only for execution time (seconds)
- **Example**:
  - Intent waits 7 days for sunny Thursday
  - Checks weather every hour (1 second per check)
  - Total cost: ~168 seconds of execution = ~$0.0001
  - vs. Continuous polling: 7 days * 24 hours = $50+ in compute costs

**Implementation Requirements**:

- Azure Durable Functions Python v2 programming model
- Event Sourcing for state management (built-in)
- External event handlers for HITL
- Progress ledger in Supabase for user visibility
- Timer triggers for intent watcher
- Integration with weather APIs, calendar services
- **Chat-First**: Webhook push notifications to chat threads, Progress Ledger Adaptive Cards, JSON-LD for intent state

**Why This Approach**:

- **Cost Efficient**: Only pays for execution, not waiting
- **Stateful**: Can pause for days/weeks without losing state
- **Scalable**: Handles thousands of standing intents simultaneously
- **User-Friendly**: Real-time progress updates via Progress Ledger
- **Flexible**: Supports complex condition-based workflows

### Module 24: Omnichannel Message Broker & HITL Escalation

**Technology**: Azure Durable Functions + Twilio WhatsApp Business API + Twilio SMS + Azure OpenAI Service (Vision) + Supabase PostgreSQL + Azure Container Apps (FastAPI)

**Implementation**:

- `omnichannel-broker-service/` (FastAPI on Container Apps)
  - `message-router.py` - Multi-channel routing logic
  - `negotiation-state-machine.py` - Negotiation state management
  - `nlp-reprocessor.py` - Extract counter-offers from partner text
  - `suggestion-enricher.py` - Enrich suggestions with metadata
  - `preference-manager.py` - Communication preference persistence
  - `webhook-handlers/` - Two-way webhook listeners
  - `twilio-whatsapp-webhook.py` - WhatsApp webhook handler
  - `twilio-sms-webhook.py` - SMS webhook handler
  - `partner-api-webhook.py` - API webhook handler
  - `vision-analyzer.py` - Analyze partner photos (OpenAI Vision)

- `hitl-escalation-service/` (FastAPI on Container Apps)
  - `escalation-trigger.py` - Escalation trigger logic
  - `admin-dashboard-api.py` - Admin dashboard API
  - `silent-monitoring.py` - Silent monitoring for admins
  - `intervention-queue.py` - High-urgency task queue

- `negotiation-orchestrator/` (Azure Durable Functions)
  - `negotiation_orchestrator.py` - Durable orchestrator for negotiations
  - `wait_for_partner_reply.py` - Wait-for-event pattern
  - `negotiation_timeout.py` - Timeout handling

**Key Features**:

1. **Symmetric Negotiation Pattern**:

  - **Stateful Translator**: System acts as translator across all platforms
  - **Negotiation Object**: Tracks status across all channels
  - **User View**: Proposal appears as "Proposal Card" in chat
  - **Partner View**: Structured message with interactive buttons or NLP
  - **Real-time Sync**: Updates user's primary AI thread (Gemini/ChatGPT) in real-time

2. **Multi-Channel Router**:

  - **Communication Mesh**: Translates JSON intents into human-readable messages
  - **Channel Support**: WhatsApp, SMS, Email, API
  - **Preference-Based Routing**: Routes to partner's preferred channel
  - **Channel Translation**: Converts between channel formats

3. **Two-Way Webhooks**:

  - **Twilio WhatsApp Webhook**: Receives partner replies via WhatsApp
  - **Twilio SMS Webhook**: Receives partner replies via SMS
  - **Partner API Webhook**: Receives structured replies via API
  - **Interactive Buttons**: WhatsApp buttons (Accept/Decline/Modify)
  - **Natural Language Processing**: Parses text replies for counter-offers

4. **Negotiation State Machine**:

  - **States**: `pending`, `awaiting_partner_reply`, `awaiting_user_approval`, `accepted`, `rejected`, `counter_offer`, `escalated`
  - **Wait-for-Event Pattern**: Durable Functions waits for partner reply
  - **Timeout Handling**: Escalates if no reply within timeout
  - **Counter-Offer Tracking**: Tracks number of counter-offers

5. **Dynamic Suggestion Engine**:

  - **Text Interpretation**: Extracts counter-offer from partner text (e.g., "Deep Purple Metallic")
  - **Inventory Scouting**: Searches partner's manifest for item metadata
  - **Enrichment**: Adds image, price, specifications
  - **Visual Suggestion Card**: Pushes enriched suggestion to user's AI thread

6. **Human-in-the-Loop (HITL) Escalation**:

  - **Trigger 1: Timeout**: If partner doesn't reply within 15 minutes for JIT request, escalates to Admin Dashboard
  - **Trigger 2: Sentiment/Confusion**: NLP detects frustration (e.g., "I already told you no pink!"), pauses AI and connects human agent
  - **Trigger 3: Deadlock**: More than 3 counter-offers, flags for "High-Touch Intervention"
  - **Trigger 4: Time-Chain Urgency**: If Time-Chain leg is < 2 hours from execution and partner reply is null, moves to Admin Intervention

7. **Human Escape Hatch**:

  - **Admin Dashboard**: Unified view of all active negotiations across channels
  - **Silent Monitoring**: Admins can view live chat without interrupting
  - **Intervention Queue**: High-urgency tasks prioritized
  - **Jump-In Capability**: Admins can join conversation to resolve deadlocks

8. **Vision AI Integration**:

  - **Photo Analysis**: Partner sends photo (e.g., "Will this purple work?")
  - **Quality Check**: AI analyzes photo to ensure it meets "Luxury" criteria
  - **Approval Workflow**: Photo approved before showing to user

**Database Schema**:

```sql
-- Communication preferences
CREATE TABLE communication_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  partner_id UUID REFERENCES partners(id),
  channel VARCHAR(50) NOT NULL, -- 'whatsapp', 'sms', 'email', 'api'
  channel_identifier VARCHAR(255) NOT NULL, -- Phone number, email, API endpoint
  priority INTEGER DEFAULT 1, -- 1 = primary, 2 = secondary
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, partner_id, channel)
);

-- Negotiation objects
CREATE TABLE negotiations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  order_leg_id UUID REFERENCES order_legs(id),
  negotiation_type VARCHAR(50) NOT NULL, -- 'product_change', 'price_negotiation', 'timing_change'
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'awaiting_partner_reply', 'awaiting_user_approval', 'accepted', 'rejected', 'counter_offer', 'escalated'
  orchestration_instance_id VARCHAR(255), -- Durable Functions instance ID
  user_chat_thread_id VARCHAR(255), -- User's primary AI thread (Gemini/ChatGPT)
  partner_channel VARCHAR(50) NOT NULL, -- Partner's communication channel
  partner_channel_id VARCHAR(255) NOT NULL, -- Partner's channel identifier
  original_request JSONB NOT NULL, -- Original request details
  current_proposal JSONB, -- Current proposal being negotiated
  counter_offer_count INTEGER DEFAULT 0,
  escalation_reason TEXT,
  escalated_at TIMESTAMPTZ,
  escalated_to UUID REFERENCES users(id), -- Admin user ID
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Negotiation messages
CREATE TABLE negotiation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id),
  sender_type VARCHAR(50) NOT NULL, -- 'user', 'partner', 'system', 'admin'
  sender_id UUID, -- User ID, Partner ID, or NULL for system
  channel VARCHAR(50) NOT NULL, -- Channel message was sent/received on
  message_type VARCHAR(50) NOT NULL, -- 'text', 'button_click', 'photo', 'structured'
  message_content TEXT,
  structured_data JSONB, -- For structured messages
  photo_url TEXT, -- For photo messages
  vision_analysis JSONB, -- Vision AI analysis results
  is_counter_offer BOOLEAN DEFAULT FALSE,
  counter_offer_data JSONB, -- Extracted counter-offer data
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Escalation records
CREATE TABLE escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id),
  escalation_type VARCHAR(50) NOT NULL, -- 'timeout', 'sentiment', 'deadlock', 'urgency'
  trigger_reason TEXT NOT NULL,
  priority VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'assigned', 'in_progress', 'resolved'
  assigned_to UUID REFERENCES users(id), -- Admin user ID
  assigned_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  resolution_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin monitoring sessions
CREATE TABLE monitoring_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id),
  admin_user_id UUID REFERENCES users(id),
  is_silent BOOLEAN DEFAULT TRUE, -- True = watching, False = actively participating
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  left_at TIMESTAMPTZ
);

-- Suggestion enrichments
CREATE TABLE suggestion_enrichments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id),
  partner_text TEXT NOT NULL, -- Original partner text
  extracted_item TEXT, -- Extracted item name (e.g., "Deep Purple Metallic")
  manifest_item_id UUID REFERENCES products(id),
  enriched_data JSONB NOT NULL, -- Image, price, specifications
  adaptive_card JSONB, -- Generated Adaptive Card
  pushed_to_user BOOLEAN DEFAULT FALSE,
  pushed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Durable Functions Implementation**:

```python
# negotiation_orchestrator.py
import azure.functions as func
import azure.durable_functions as df

def negotiation_orchestrator(context: df.DurableOrchestrationContext):
    """
    Orchestrates two-way negotiation across channels
    """
    negotiation_data = context.get_input()
    negotiation_id = negotiation_data['negotiation_id']
    order_leg_id = negotiation_data['order_leg_id']
    partner_channel = negotiation_data['partner_channel']
    partner_channel_id = negotiation_data['partner_channel_id']
    user_chat_thread_id = negotiation_data['user_chat_thread_id']

    # Step 1: Send initial request to partner
    initial_message = yield context.call_activity(
        'send_partner_message',
        {
'negotiation_id': negotiation_id,
'channel': partner_channel,
'channel_id': partner_channel_id,
'message': negotiation_data['original_request'],
'include_buttons': True
        }
    )

    # Update negotiation status
    yield context.call_activity(
        'update_negotiation_status',
        {
'negotiation_id': negotiation_id,
'status': 'awaiting_partner_reply'
        }
    )

    # Step 2: Wait for partner reply (with timeout)
    timeout_minutes = 15 if negotiation_data.get('is_jit') else 60
    partner_reply = yield context.wait_for_external_event(
        'PartnerReply',
        timeout=timedelta(minutes=timeout_minutes)
    )

    if partner_reply is None:
        # Timeout - escalate
        yield context.call_activity(
'trigger_escalation',
{
'negotiation_id': negotiation_id,
'escalation_type': 'timeout',
'trigger_reason': f'No reply within {timeout_minutes} minutes'
}
        )
        return

    # Step 3: Process partner reply
    reply_analysis = yield context.call_activity(
        'analyze_partner_reply',
        {
'negotiation_id': negotiation_id,
'reply': partner_reply,
'channel': partner_channel
        }
    )

    # Check for sentiment/confusion
    if reply_analysis.get('sentiment') == 'frustrated' or reply_analysis.get('confusion_detected'):
        # Escalate immediately
        yield context.call_activity(
'trigger_escalation',
{
'negotiation_id': negotiation_id,
'escalation_type': 'sentiment',
'trigger_reason': 'Frustration or confusion detected'
}
        )
        return

    # Check if counter-offer
    if reply_analysis.get('is_counter_offer'):
        # Increment counter-offer count
        counter_count = yield context.call_activity(
'increment_counter_offer',
{'negotiation_id': negotiation_id}
        )

        # Check for deadlock (3+ counter-offers)
        if counter_count >= 3:
yield context.call_activity(
'trigger_escalation',
{
'negotiation_id': negotiation_id,
'escalation_type': 'deadlock',
'trigger_reason': f'{counter_count} counter-offers without resolution'
}
)
return

        # Enrich counter-offer
        enriched_suggestion = yield context.call_activity(
'enrich_suggestion',
{
'negotiation_id': negotiation_id,
'partner_text': partner_reply.get('text'),
'partner_id': negotiation_data['partner_id']
}
        )

        # Push to user's AI thread
        yield context.call_activity(
'push_to_user_thread',
{
'chat_thread_id': user_chat_thread_id,
'suggestion': enriched_suggestion,
'adaptive_card': enriched_suggestion['adaptive_card']
}
        )

        # Update status to awaiting user approval
        yield context.call_activity(
'update_negotiation_status',
{
'negotiation_id': negotiation_id,
'status': 'awaiting_user_approval'
}
        )

        # Wait for user approval
        user_approval = yield context.wait_for_external_event(
'UserApproval',
timeout=timedelta(hours=24)
        )

        if user_approval and user_approval.get('approved'):
# Accepted - complete negotiation
yield context.call_activity(
'complete_negotiation',
{
'negotiation_id': negotiation_id,
'status': 'accepted',
'final_proposal': enriched_suggestion
}
)
        else:
# Rejected or timeout - restart negotiation
# Could loop back or escalate
pass
    else:
        # Direct acceptance or rejection
        if reply_analysis.get('accepted'):
yield context.call_activity(
'complete_negotiation',
{
'negotiation_id': negotiation_id,
'status': 'accepted'
}
)
        elif reply_analysis.get('rejected'):
yield context.call_activity(
'complete_negotiation',
{
'negotiation_id': negotiation_id,
'status': 'rejected'
}
)

    return {'completed': True}

# analyze_partner_reply.py (Activity)
def analyze_partner_reply(context: df.DurableActivityContext):
    """
    Analyzes partner reply using NLP and Vision AI
    """
    reply_data = context.get_input()
    reply_text = reply_data.get('text', '')
    photo_url = reply_data.get('photo_url')

    # NLP analysis using Intent Resolver (Module 4)
    nlp_result = intent_resolver.analyze_text(reply_text)

    # Sentiment analysis
    sentiment = analyze_sentiment(reply_text)

    # Check for confusion indicators
    confusion_indicators = ['already told', 'no', 'not', 'wrong', 'incorrect']
    confusion_detected = any(indicator in reply_text.lower() for indicator in confusion_indicators)

    # Extract counter-offer
    is_counter_offer = False
    counter_offer_data = None

    if nlp_result.get('intent') == 'counter_offer':
        is_counter_offer = True
        counter_offer_data = {
'item_name': nlp_result.get('item_name'),
'price': nlp_result.get('price'),
'specifications': nlp_result.get('specifications')
        }

    # Vision AI analysis if photo provided
    vision_analysis = None
    if photo_url:
        vision_analysis = analyze_photo_with_vision(photo_url)
        # Check if meets quality criteria
        if not vision_analysis.get('meets_criteria'):
# Photo doesn't meet standards
pass

    return {
        'sentiment': sentiment,
        'confusion_detected': confusion_detected,
        'is_counter_offer': is_counter_offer,
        'counter_offer_data': counter_offer_data,
        'accepted': nlp_result.get('accepted', False),
        'rejected': nlp_result.get('rejected', False),
        'vision_analysis': vision_analysis
    }

# enrich_suggestion.py (Activity)
def enrich_suggestion(context: df.DurableActivityContext):
    """
    Enriches partner text suggestion with metadata
    """
    suggestion_data = context.get_input()
    partner_text = suggestion_data['partner_text']
    partner_id = suggestion_data['partner_id']

    # Extract item name from text (e.g., "Deep Purple Metallic")
    item_name = extract_item_name(partner_text)

    # Search partner's manifest for item
    manifest_item = scout_engine.search_partner_manifest(
        partner_id=partner_id,
        item_name=item_name
    )

    if manifest_item:
        # Enrich with metadata
        enriched = {
'item_name': manifest_item['name'],
'image_url': manifest_item['image_url'],
'price': manifest_item['price'],
'specifications': manifest_item['specifications'],
'description': manifest_item['description']
        }

        # Generate Adaptive Card
        adaptive_card = generate_suggestion_card(enriched)

        return {
'enriched_data': enriched,
'adaptive_card': adaptive_card
        }

    return None
```

**Integration Points**:

1. **Module 4 (Intent Resolver)**:

  - NLP re-processing for partner replies
  - Counter-offer extraction
  - Sentiment analysis

2. **Module 1 (Scout Engine)**:

  - Searches partner manifest for counter-offer items
  - Retrieves item metadata

3. **Module 12 (Support Hub)**:

  - Uses Multi-Party Support Hub for message routing
  - Unified thread management

4. **Module 5 (Time-Chain Resolver)**:

  - Checks Time-Chain urgency for escalation
  - Updates Time-Chain when negotiation completes

5. **Module 23 (Standing Intent)**:

  - Can trigger negotiations for standing intents
  - Updates standing intent progress

**API Endpoints**:

```python
# Negotiation management
POST   /api/v1/negotiations                    # Start negotiation
GET    /api/v1/negotiations/{id}                # Get negotiation details
PUT    /api/v1/negotiations/{id}                # Update negotiation
POST   /api/v1/negotiations/{id}/approve        # User approval
POST   /api/v1/negotiations/{id}/reject         # User rejection

# Webhook endpoints
POST   /webhooks/twilio/whatsapp                # Twilio WhatsApp webhook
POST   /webhooks/twilio/sms                      # Twilio SMS webhook
POST   /webhooks/partner/{partner_id}            # Partner API webhook

# Escalation management
GET    /api/v1/escalations                      # List escalations
POST   /api/v1/escalations/{id}/assign          # Assign escalation
POST   /api/v1/escalations/{id}/resolve          # Resolve escalation

# Admin dashboard
GET    /api/v1/admin/negotiations                # All active negotiations
GET    /api/v1/admin/negotiations/{id}/monitor   # Start silent monitoring
POST   /api/v1/admin/negotiations/{id}/intervene # Join conversation
```

**Admin Dashboard Features**:

1. **Unified Negotiation View**:

  - All active negotiations across channels
  - Filter by status, channel, urgency
  - Real-time updates

2. **Silent Monitoring**:

  - View live chat without interrupting
  - See all messages across channels
  - Monitor sentiment and confusion

3. **Intervention Queue**:

  - High-urgency tasks prioritized
  - Time-Chain urgency highlighted
  - Escalation reasons displayed

4. **Jump-In Capability**:

  - Join conversation seamlessly
  - Take over from AI
  - Resolve deadlocks

**Why This Approach**:

- **Symmetric Communication**: Works across all channels uniformly
- **No Dead-Ends**: Human escalation ensures resolution
- **Real-time Sync**: User always sees updates in primary thread
- **Intelligent Routing**: Uses partner preferences
- **Cost Efficient**: Durable Functions only pays for execution
- **Scalable**: Handles thousands of concurrent negotiations

### Module 25: The Partner Simulator

**Technology**: Next.js on Vercel + Azure Container Apps (FastAPI) + Supabase PostgreSQL + Azure OpenAI Service (GPT-4o) + Module 1 (Scout Engine) + Module 24 (Omnichannel Broker)

**Purpose**: Create test partners with different products and configurable responses (automated or manual) for various scenarios. **Critical for MVP Live Demo of Autonomous Recovery.**

**Implementation**:

- `partner-simulator/` (Next.js on Vercel)
        - `simulator-dashboard.tsx` - Admin dashboard for creating/managing simulated partners
        - `partner-builder.tsx` - Visual interface for building partner profiles with products
        - `product-manager.tsx` - Product catalog manager for simulated partners
        - `scenario-builder.tsx` - Scenario configuration interface
        - `response-manager.tsx` - Response configuration (automated/manual) with real-time controls
        - `manual-response-queue.tsx` - Queue interface for manual responses
        - `live-demo-setup.tsx` - Quick setup for Live Demo scenarios

- `partner-simulator-api/` (FastAPI on Container Apps)
        - `simulator-engine.py` - Main simulator orchestrator
        - `partner-factory.py` - Creates simulated partner instances
        - `response-handler.py` - Handles automated and manual responses
        - `automated-response-engine.py` - Automated response logic
        - `manual-response-queue.py` - Manual response queue management
        - `scenario-executor.py` - Executes predefined scenarios
        - `product-generator.py` - Generates product catalogs for simulated partners
        - `webhook-handler.py` - Receives requests from Omnichannel Broker (Module 24)

**Key Features**:

1. **Simulated Partner Creation**:

  - Create partner profiles with custom names, locations, capabilities
  - Configure communication preferences (WhatsApp, SMS, API)
  - Set trust scores and reliability metrics
  - Define business hours and availability

2. **Product Catalog Management**:

  - Add/remove products for each simulated partner
  - Configure product attributes (name, price, capabilities, inventory)
  - Set availability rules (always available, conditional, out of stock)
  - Define product images and descriptions

3. **Response Configuration** (Core Feature):

  - **Automated Responses**: Pre-configured responses based on scenarios
  - **Product-Based Logic**: Accept/Reject based on product availability
  - Example: "If product exists in catalog → Accept, else → Reject"
  - **Counter-Offers**: Predefined alternatives when rejecting
  - Example: "I don't have pink flowers, but I have red roses available"
  - **Delay Responses**: Simulate slow partner (configurable delay)
  - Example: Wait 20 minutes before responding
  - **Random Responses**: Simulate unpredictable partner behavior
  - Example: 70% accept, 30% reject
  - **Conditional Logic**: IF/THEN rules for complex scenarios
  - Example: "IF order value > $500 THEN reject, ELSE accept"
  - **Response Templates**: Pre-written message templates
  - Example: "Sorry, I don't have {product_name} available"

  - **Manual Responses**: Admin can manually respond to requests in real-time
  - **Real-Time Queue**: See all pending requests from simulated partners
  - **Response Interface**: Type or select response for each request
  - **Response Templates**: Quick-select templates for common responses
  - **Bulk Actions**: Respond to multiple requests at once
  - **Response History**: Track all manual responses
  - **Switch Mode**: Toggle between automated and manual for specific partners
  - **Notification System**: Get notified when requests arrive

4. **Scenario Builder**:

  - **Predefined Scenarios** (Ready-to-use for Live Demo):
  - **"Partner Rejection"**: Partner always says "No" to change requests
  - Perfect for Live Demo of Autonomous Recovery
  - Example: "No, we don't have pink flowers"
  - **"Product Unavailable"**: Specific products always out of stock
  - Configure which products are unavailable
  - Example: "Red flowers" available, "Pink flowers" unavailable
  - **"Slow Response"**: Partner takes 20+ minutes to respond
  - Configurable delay (seconds, minutes, hours)
  - Simulates real-world partner delays
  - **"Counter-Offer"**: Partner always offers alternatives
  - Pre-configured alternative products
  - Example: "I don't have pink, but I have red roses"
  - **"Price Negotiation"**: Partner negotiates prices
  - Configurable negotiation rules
  - Example: "I can do it for 10% more"
  - **"Conditional Acceptance"**: Accept based on conditions
  - Example: "Accept if order > $100, else reject"

  - **Custom Scenarios**: Create custom response patterns
  - **Visual Scenario Builder**: Drag-and-drop interface
  - **IF/THEN Logic**: Complex conditional responses
  - **Multi-Step Scenarios**: Chain multiple responses
  - **Variable Substitution**: Use request data in responses
  - **Randomization**: Add randomness to responses

  - **Scenario Triggers**: Define when scenarios activate
  - **Product-Based**: Trigger based on product type or name
  - Example: "If product contains 'flowers' → Use rejection scenario"
  - **Request Type**: Trigger based on request type
  - Example: "If change_request → Use rejection scenario"
  - **Time-Based**: Trigger based on time of day
  - Example: "If after 5 PM → Use slow response scenario"
  - **Order Value**: Trigger based on order value
  - Example: "If order > $500 → Use negotiation scenario"
  - **User-Based**: Trigger based on user characteristics
  - Example: "If new user → Use acceptance scenario"
  - **Combination**: Multiple triggers combined with AND/OR logic

5. **Integration with Real System**:

  - Simulated partners appear in Scout Engine (Module 1)
  - Respond to negotiations via Omnichannel Broker (Module 24)
  - Process orders through normal flow
  - Can be used for Live Demo of Autonomous Recovery (Module 6)

**Database Schema**:

```sql
-- Simulated partners
CREATE TABLE simulated_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  business_type VARCHAR(100), -- 'florist', 'limo', 'restaurant', etc.
  location JSONB NOT NULL, -- {lat, lng, address}
  communication_channel VARCHAR(50) DEFAULT 'whatsapp', -- 'whatsapp', 'sms', 'api'
  channel_identifier VARCHAR(255), -- Phone number or API endpoint
  trust_score INTEGER DEFAULT 70, -- 0-100
  reliability_score DECIMAL(5,2) DEFAULT 0.85, -- 0-1
  business_hours JSONB, -- {open: "09:00", close: "17:00", days: [1,2,3,4,5]}
  capabilities JSONB, -- Array of capability tags
  is_active BOOLEAN DEFAULT TRUE,
  created_by UUID REFERENCES users(id), -- Admin who created
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Simulated partner products
CREATE TABLE simulated_partner_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id),
  product_name VARCHAR(255) NOT NULL,
  product_description TEXT,
  price DECIMAL(10,2) NOT NULL,
  capabilities JSONB, -- Array of capability tags
  inventory_count INTEGER DEFAULT 999, -- -1 = unlimited, 0 = out of stock
  availability_rule VARCHAR(50) DEFAULT 'always', -- 'always', 'conditional', 'out_of_stock'
  availability_condition JSONB, -- Conditions for availability
  image_url TEXT,
  metadata JSONB, -- Additional product data
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Response configurations
CREATE TABLE response_configurations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id),
  scenario_type VARCHAR(100) NOT NULL, -- 'rejection', 'unavailable', 'slow', 'counter_offer'
  trigger_conditions JSONB NOT NULL, -- When to trigger this response
  response_type VARCHAR(50) NOT NULL, -- 'automated', 'manual'
  automated_response JSONB, -- Response template for automated
  response_delay_seconds INTEGER DEFAULT 0, -- Delay before responding
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scenario definitions
CREATE TABLE scenario_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  scenario_type VARCHAR(100) NOT NULL,
  configuration JSONB NOT NULL, -- Scenario-specific config
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Manual response queue
CREATE TABLE manual_response_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id),
  negotiation_id UUID REFERENCES negotiations(id),
  request_data JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'responded', 'expired'
  assigned_to UUID REFERENCES users(id), -- Admin assigned to respond
  response_data JSONB,
  responded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Implementation Details**:

```python
# simulator-engine.py
class PartnerSimulator:
    """
    Main simulator orchestrator
    """
    async def create_simulated_partner(
        self,
        partner_config: dict
    ) -> SimulatedPartner:
        """
        Creates a new simulated partner
        """
        # Create partner record
        partner = await create_partner_record(partner_config)

        # Register with Scout Engine (Module 1)
        await scout_engine.register_partner(partner)

        # Set up communication channel
        await setup_communication_channel(partner)

        return partner

    async def handle_request(
        self,
        partner_id: str,
        request: dict
    ) -> dict:
        """
        Handles incoming request to simulated partner
        """
        partner = await get_simulated_partner(partner_id)

        # Check for matching scenario
        scenario = await find_matching_scenario(partner, request)

        if scenario:
# Execute scenario
response = await execute_scenario(scenario, request)
        else:
# Use default response logic
response = await generate_default_response(partner, request)

        # Apply response delay if configured
        if partner.response_delay_seconds > 0:
await asyncio.sleep(partner.response_delay_seconds)

        # Send response
        await send_response(partner, response)

        return response

# response-handler.py
async def handle_response(
    partner_id: str,
    request: dict
) -> dict:
    """
    Main response handler - routes to automated or manual based on configuration
    """
    partner = await get_simulated_partner(partner_id)
    response_config = await get_response_configuration(partner_id, request)

    # Check if manual response is required
    if response_config['response_type'] == 'manual':
        # Add to manual response queue
        queue_item = await add_to_manual_queue(
partner_id=partner_id,
request=request,
response_config=response_config
        )

        # Return pending status
        return {
'status': 'pending_manual',
'queue_id': queue_item['id'],
'message': 'Waiting for manual response'
        }

    # Automated response
    return await generate_automated_response(partner, request, response_config)

async def generate_automated_response(
    partner: SimulatedPartner,
    request: dict,
    response_config: dict
) -> dict:
    """
    Generates automated response based on partner configuration and scenarios
    """
    request_type = request.get('type')

    # Check for matching scenario first
    scenario = await find_matching_scenario(partner.id, request)
    if scenario:
        return await execute_scenario(scenario, request)

    # Default response logic
    if request_type == 'product_change':
        # Check if product available
        requested_item = request.get('requested_item')
        product = await find_product(partner.id, requested_item)

        if product and product.inventory_count > 0:
return {
'accepted': True,
'message': f"Yes, I have {requested_item} available",
'response_type': 'automated'
}
        else:
return {
'accepted': False,
'message': f"Sorry, I don't have {requested_item} available",
'response_type': 'automated'
}

    elif request_type == 'order_request':
        # Check availability and respond
        items = request.get('items', [])
        available = await check_availability(partner.id, items)

        if available:
return {
'accepted': True,
'message': "Order confirmed!",
'response_type': 'automated'
}
        else:
return {
'accepted': False,
'message': "Some items are unavailable",
'response_type': 'automated'
}

    return {
        'accepted': False,
        'message': 'Unable to process request',
        'response_type': 'automated'
    }

# manual-response-queue.py
async def add_to_manual_queue(
    partner_id: str,
    request: dict,
    response_config: dict
) -> dict:
    """
    Adds request to manual response queue
    """
    queue_item = await db.execute("""
        INSERT INTO manual_response_queue (
simulated_partner_id,
negotiation_id,
request_data,
status
        ) VALUES ($1, $2, $3, 'pending')
        RETURNING *
    """, partner_id, request.get('negotiation_id'), json.dumps(request))

    # Notify admins (via Supabase Realtime or webhook)
    await notify_admins_of_pending_response(queue_item['id'])

    return queue_item

async def send_manual_response(
    queue_id: str,
    admin_user_id: str,
    response: dict
) -> dict:
    """
    Sends manual response from admin
    """
    queue_item = await get_queue_item(queue_id)

    # Update queue item
    await db.execute("""
        UPDATE manual_response_queue
        SET status = 'responded',
assigned_to = $1,
response_data = $2,
responded_at = NOW()
        WHERE id = $3
    """, admin_user_id, json.dumps(response), queue_id)

    # Send response via Omnichannel Broker (Module 24)
    await omnichannel_broker.send_response(
        negotiation_id=queue_item['negotiation_id'],
        response=response
    )

    return {'success': True, 'response_sent': True}

# scenario-executor.py
async def execute_scenario(
    scenario: ScenarioDefinition,
    request: dict
) -> dict:
    """
    Executes predefined scenario
    """
    scenario_type = scenario.scenario_type

    if scenario_type == 'rejection':
        return {
'accepted': False,
'message': scenario.configuration.get('rejection_message', 'No')
        }

    elif scenario_type == 'counter_offer':
        alternatives = scenario.configuration.get('alternatives', [])
        if alternatives:
return {
'accepted': False,
'counter_offer': True,
'message': f"I don't have that, but I have {alternatives[0]} available",
'alternatives': alternatives
}

    elif scenario_type == 'slow_response':
        # Will be handled by response_delay_seconds
        return await generate_default_response(scenario.partner, request)

    return await generate_default_response(scenario.partner, request)
```

**Use Cases**:

1. **Live Demo of Autonomous Recovery** (MVP Critical):

  - **Setup**:
  - Create Partner A: "Flower Shop A" with only "red flowers" product
  - Configure automated rejection scenario: "Reject all requests for 'pink flowers'"
  - Create Partner B: "Flower Shop B" with "pink flowers" product
  - Configure automated acceptance scenario: "Accept all requests"
  - **Demo Flow**:
  - User requests: "I want pink flowers instead of red"
  - System sends request to Partner A via Omnichannel Broker (Module 24)
  - Partner A automatically responds: "No, we don't have pink flowers"
  - System triggers Autonomous Recovery (Module 6)
  - System finds Partner B with pink flowers
  - System cancels Partner A order, creates Partner B order
  - System recalculates timeline and notifies user
  - **Result**: Full autonomous recovery demonstrated without human intervention

2. **Testing Scenarios**:

  - **Automated Testing**:
  - Test partner rejection handling
  - Test slow response timeouts
  - Test counter-offer flows
  - Test price negotiations
  - Test edge cases (out of stock, unavailable, etc.)
  - **Manual Testing**:
  - Test human-in-the-loop scenarios
  - Test complex negotiation flows
  - Test escalation paths

3. **Development**:

  - Develop without real partners
  - Test edge cases
  - Validate error handling
  - Test integration points
  - Debug issues in controlled environment

4. **Training**:

  - Train support staff on partner interactions
  - Demo platform capabilities to stakeholders
  - Showcase features to potential partners
  - Practice handling various scenarios

5. **Product Development**:

  - Test new features with simulated partners
  - Validate changes before deploying to production
  - A/B test different response strategies

**API Endpoints**:

```python
# Simulated partner management
POST   /api/v1/simulator/partners                    # Create simulated partner
GET    /api/v1/simulator/partners                    # List simulated partners
GET    /api/v1/simulator/partners/{id}               # Get partner details
PUT    /api/v1/simulator/partners/{id}               # Update partner
DELETE /api/v1/simulator/partners/{id}               # Delete partner

# Product management
POST   /api/v1/simulator/partners/{id}/products     # Add product
GET    /api/v1/simulator/partners/{id}/products      # List products
PUT    /api/v1/simulator/products/{id}               # Update product
DELETE /api/v1/simulator/products/{id}               # Delete product

# Response configuration
POST   /api/v1/simulator/partners/{id}/responses     # Configure response
GET    /api/v1/simulator/partners/{id}/responses     # Get response config
PUT    /api/v1/simulator/responses/{id}              # Update response

# Scenario management
POST   /api/v1/simulator/scenarios                   # Create scenario
GET    /api/v1/simulator/scenarios                   # List scenarios
POST   /api/v1/simulator/partners/{id}/scenarios     # Assign scenario

# Manual response queue
GET    /api/v1/simulator/responses/queue             # Get pending responses
POST   /api/v1/simulator/responses/{id}/respond      # Send manual response
PUT    /api/v1/simulator/responses/{id}/assign       # Assign to admin
GET    /api/v1/simulator/responses/{id}              # Get response details

# Live Demo quick setup
POST   /api/v1/simulator/live-demo/setup             # Quick setup for Live Demo
GET    /api/v1/simulator/live-demo/scenarios          # Get Live Demo scenarios
POST   /api/v1/simulator/live-demo/reset              # Reset Live Demo state
```

**Live Demo Quick Setup**:

```python
# live-demo-setup.py
async def setup_live_demo_autonomous_recovery() -> dict:
    """
    Quick setup for Live Demo of Autonomous Recovery
    Creates two partners: one that rejects, one that accepts
    """
    # Partner A: Rejects pink flowers
    partner_a = await create_simulated_partner({
        'name': 'Flower Shop A',
        'business_type': 'florist',
        'location': {'lat': 40.7128, 'lng': -74.0060},
        'communication_channel': 'whatsapp',
        'channel_identifier': '+1234567890'
    })

    # Add only red flowers
    await add_product(partner_a['id'], {
        'product_name': 'Red Flowers',
        'price': 50.00,
        'inventory_count': 10
    })

    # Configure rejection scenario
    await configure_scenario(partner_a['id'], {
        'scenario_type': 'rejection',
        'trigger_conditions': {
'product_name_contains': 'pink'
        },
        'response_type': 'automated',
        'automated_response': {
'message': "No, we don't have pink flowers available"
        }
    })

    # Partner B: Has pink flowers
    partner_b = await create_simulated_partner({
        'name': 'Flower Shop B',
        'business_type': 'florist',
        'location': {'lat': 40.7580, 'lng': -73.9855},
        'communication_channel': 'whatsapp',
        'channel_identifier': '+1234567891'
    })

    # Add pink flowers
    await add_product(partner_b['id'], {
        'product_name': 'Pink Flowers',
        'price': 55.00,
        'inventory_count': 10
    })

    # Configure acceptance scenario
    await configure_scenario(partner_b['id'], {
        'scenario_type': 'acceptance',
        'response_type': 'automated',
        'automated_response': {
'message': "Yes, I have pink flowers available!"
        }
    })

    return {
        'partner_a': partner_a,
        'partner_b': partner_b,
        'demo_ready': True
    }
```

**Integration Points**:

- **Module 1 (Scout Engine)**: Simulated partners appear in search results
- **Module 24 (Omnichannel Broker)**: Receives and responds to negotiations
- **Module 6 (Autonomous Re-Sourcing)**: Can trigger recovery scenarios
- **Module 5 (Time-Chain Resolver)**: Processes orders normally

**Why This Approach**:

- **MVP Critical**: Essential for Live Demo of Autonomous Recovery
- **Testing**: Enables comprehensive testing without real partners
- **Demos**: Perfect for live demos and showcases
- **Development**: Speeds up development cycle
- **Flexibility**: Supports both automated and manual responses
- **Realistic**: Simulated partners behave like real partners
- **Control**: Full control over partner behavior for testing scenarios
- **Scalability**: Can create unlimited test partners with different configurations

### Design System Implementation Guidelines

**Phase 1: Foundation (Month 1 - Critical Path)**

1. **Design Token System**:
   ```typescript
   // packages/design-system/tokens/colors.ts
   export const colorTokens = {
     primary: {
       50: '#eff6ff',
       100: '#dbeafe',
       // ... full scale
       900: '#1e3a8a',
     },
     // semantic colors
     success: { ... },
     error: { ... },
     warning: { ... },
   } as const;
   ```


  - **Mobile**: Tokens work with React Native StyleSheet
  - **PWA**: Tokens work with CSS custom properties

2. **Component Architecture**:

  - All components extend base shadcn/ui components (web)
  - **Mobile**: React Native components using same design tokens
  - **PWA**: Web components with PWA enhancements (offline, installable)
  - Props-based customization with theme context
  - Variant system (size, color, style) - **Works across all platforms**
  - Composition over configuration
  - **Shared component logic**: Business logic shared, platform-specific UI adapters

3. **Theme System**:
   ```typescript
   // Theme definition
   interface Theme {
     colors: ColorTokens;
     typography: TypographyTokens;
     spacing: SpacingTokens;
     shadows: ShadowTokens;
     borderRadius: BorderRadiusTokens;
   }

   // Runtime theme injection
   const injectTheme = (theme: Theme, themeId: string) => {
     const root = document.documentElement;
     root.setAttribute('data-theme', themeId);
     Object.entries(theme.colors).forEach(([key, value]) => {
       root.style.setProperty(`--color-${key}`, value);
     });
     // ... inject all tokens
   };
   ```

4. **Component Example**:
   ```tsx
   // packages/design-system/components/Button/Button.tsx
   import { Button as ShadcnButton } from '@/components/ui/button';
   import { useTheme } from '@/hooks/use-theme';

   interface ButtonProps extends React.ComponentProps<typeof ShadcnButton> {
     variant?: 'primary' | 'secondary' | 'outline';
     size?: 'sm' | 'md' | 'lg';
   }

   export const Button = ({ variant = 'primary', ...props }: ButtonProps) => {
     const theme = useTheme();
     return (
       <ShadcnButton
         className={cn(
`bg-[var(--color-${variant})]`,
`text-[var(--color-${variant}-foreground)]`,
// ... theme-aware classes
         )}
         {...props}
       />
     );
   };
   ```


**Best Practices**:

1. **Component Development**:

  - Always use design tokens (never hardcode colors/spacing)
  - Support theme prop for runtime customization
  - **Build web, mobile, and PWA versions simultaneously**
  - **Shared business logic, platform-specific UI adapters**
  - Maintain accessibility (ARIA labels, keyboard navigation, mobile screen readers)
  - Document props and usage examples for all platforms
  - Write tests for all variants (web + mobile)
  - **Mobile**: Test on iOS and Android
  - **PWA**: Test offline functionality and installability

2. **Theme Customization**:

  - Validate theme configs before applying
  - Provide theme presets for quick setup
  - Support partial theme overrides
  - Maintain contrast ratios for accessibility

3. **Storefront Builder**:

  - Real-time preview of changes
  - Undo/redo functionality
  - Save drafts before publishing
  - Preview on multiple device sizes
  - Export theme as JSON for backup

4. **Performance**:

  - Lazy load theme assets
  - Cache theme configs
  - Use CSS variables (no JavaScript for theme switching)
  - Minimize theme bundle size

**Component Library Structure**:

```
packages/design-system/
├── tokens/
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── shadows.ts
│   └── index.ts
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   ├── Button.stories.tsx
│   │   └── index.ts
│   ├── Card/
│   ├── Input/
│   └── ... (all components)
├── themes/
│   ├── default.ts
│   ├── presets/
│   │   ├── modern.ts
│   │   ├── classic.ts
│   │   └── minimal.ts
│   └── generator.ts
├── hooks/
│   ├── use-theme.ts
│   └── use-theme-context.ts
├── utils/
│   ├── theme-injector.ts
│   ├── theme-validator.ts
│   └── class-names.ts
└── package.json
```

**Documentation Requirements**:

- Storybook for component documentation
- Design token reference guide
- Theme customization guide
- Component API documentation
- Usage examples and patterns
- Accessibility guidelines

### Module 12: Multi-Party Support Hub

**Technology**: Supabase Realtime + Azure Container Apps (FastAPI) + Supabase PostgreSQL + Twilio WhatsApp API

**Implementation**:

- `support-service/` (FastAPI on Container Apps)
  - `thread-manager.py` - Unified conversation threads (supports web chat + WhatsApp)
  - `participant-tracker.py` - Multi-party presence (customers, vendors, hubs, AI orchestrator)
  - `message-router.py` - Route messages to correct parties across channels
  - `chat-engine.py` - Real-time chat engine with typing indicators, read receipts, message reactions
  - `whatsapp-adapter.py` - WhatsApp Business API integration
  - `channel-sync.py` - Synchronize conversations between web chat and WhatsApp
  - `notification-service.py` - Push notifications for new messages
- **Supabase Realtime** for real-time in-app chat (WebSocket-based)
  - Real-time message delivery
  - Typing indicators
  - Online/offline presence
  - Read receipts
  - File attachments (images, documents)
- **Supabase PostgreSQL** for message history
  - `conversations` table - Unified thread management
  - `messages` table - All messages (web + WhatsApp)
  - `participants` table - Multi-party thread participants
  - `message_attachments` table - File storage references
- **Twilio WhatsApp API** for WhatsApp integration
  - Two-way messaging
  - Status update notifications
  - Rich media support (images, documents, location)
  - Template messages for automated updates
- **Why Supabase Realtime**: Built into database, no separate service needed. Lower cost. Easier to manage. Perfect for multi-party chat scenarios.
- **Why Twilio**: Better developer experience, global reach, reliable delivery, webhook support for incoming messages

**Chat Features**:

- **Multi-party threads**: Customer, all vendors, hubs, and AI orchestrator in same conversation
- **Channel unification**: Messages from WhatsApp appear in web chat and vice versa
- **Rich messaging**: Text, images, documents, location sharing
- **Message status**: Sent, delivered, read receipts
- **Typing indicators**: Real-time typing status
- **File attachments**: Images and documents with preview
- **Message search**: Full-text search across conversation history
- **Thread context**: Each bundle has its own conversation thread
- **AI integration**: AI orchestrator can participate in conversations

### Module 15: Atomic Multi-Checkout

**Technology**: Stripe Connect + Azure Container Apps (FastAPI) + Supabase PostgreSQL

**Implementation**:

- `payment-service/` (FastAPI on Container Apps)
  - `multi-checkout.py` - Atomic payment orchestration
  - `token-manager.py` - Payment token management
  - `stripe-adapter.py` - Stripe Connect integration
  - `api/chat-first.py` - Chat-First checkout API
  - `adaptive-cards/checkout-card.py` - Checkout Adaptive Card
  - `instant-checkout.py` - ChatGPT Instant Checkout support
- Use Stripe Connect for split payments
- Azure Container Apps for payment orchestration
- Supabase PostgreSQL for transaction logging (ACID compliance)

**Chat-First Requirements**:

1. **Checkout API with JSON-LD Payment Schema**:
```json
{
  "data": {
    "checkout_id": "uuid",
    "total": 299.99,
    "items": [...]
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "Order",
    "totalPrice": 299.99,
    "priceCurrency": "USD",
    "paymentMethod": "CreditCard",
    "orderStatus": "PaymentPending"
  },
  "adaptive_card": generate_checkout_card(order_data),
  "instant_checkout": {
    "enabled": true,
    "chatgpt_action": "instant_checkout",
    "token": "payment_token"
  }
}
```

2. **Instant Checkout Support**:

  - ChatGPT-specific one-click checkout
  - Uses AP2 token for authorization
  - No redirect required

### Module 16: Transaction & Escrow Manager

**Technology**: Supabase PostgreSQL + Azure Service Bus

**Implementation**:

- `escrow-service/` (FastAPI on Container Apps)
  - `escrow-manager.py` - Hold/release funds logic
  - `leg-verifier.py` - Verify completion of journey legs
  - `payment-releaser.py` - Automated payment release
- Supabase PostgreSQL for financial transactions (ACID compliance, same as Azure SQL)
- Service Bus for event-driven payment releases

### Module 10: HubNegotiator & Bidding (Phase 2)

**Technology**: Upstash Redis + Azure Container Apps (FastAPI)

**Implementation**:

- `hub-negotiator-service/` (FastAPI on Container Apps)
  - `rfp-manager.py` - Request for Proposal system
  - `bid-processor.py` - Real-time bid processing
  - `capacity-matcher.py` - Match hubs to delivery requests
- **Upstash Redis** for real-time bidding state and leaderboards
- **Why Upstash**: Sub-millisecond latency critical for competitive bidding. Pay-per-request model (no idle costs). Serverless Redis perfect for bursty bidding scenarios.
- Supabase PostgreSQL for persistent bid history and hub profiles

### WhatsApp Integration Module

**Technology**: Twilio WhatsApp Business API + Azure Container Apps (FastAPI) + Supabase PostgreSQL

**Implementation**:

- `whatsapp-service/` (FastAPI on Container Apps)
  - `whatsapp-webhook.py` - Receive incoming WhatsApp messages
  - `message-sender.py` - Send messages via WhatsApp API
  - `status-notifier.py` - Automated status update notifications
  - `template-manager.py` - Manage WhatsApp template messages
  - `conversation-bridge.py` - Bridge WhatsApp messages to Module 12 chat threads
  - `opt-in-manager.py` - Handle user opt-in/opt-out for WhatsApp notifications

**Features**:

- **Status Updates**: Automated notifications for bundle status changes
  - "Your gift box has been picked up from Hub A"
  - "Customization complete! Your item is being delivered"
  - "Bundle delivered successfully!"
- **Two-way Conversations**: Customers can reply to status updates and chat with support
- **Rich Media**: Send images, documents, location pins
- **Template Messages**: Pre-approved templates for common status updates
- **Interactive Messages**: Quick reply buttons, list messages
- **Channel Sync**: WhatsApp messages sync to web chat (Module 12)
- **Opt-in Management**: Users must opt-in to receive WhatsApp messages

**Integration Points**:

- **Module 12 (Support Hub)**: WhatsApp messages appear in unified chat threads
- **Module 14 (Status Narrator)**: Status updates with Agent Reasoning sent via WhatsApp and chat cards
- **Module 5 (Time-Chain Resolver)**: Real-time delivery updates via WhatsApp
- **Module 16 (Escrow)**: Payment confirmation messages

**WhatsApp Message Types**:

1. **Status Notifications** (Template Messages):

  - Order confirmed
  - Item discovered and sourced
  - Item in transit to hub
  - Customization started
  - Customization complete
  - Out for delivery
  - Delivered
  - Payment processed

2. **Interactive Messages**:

  - Quick replies: "Track Order", "Contact Support", "View Details"
  - List messages: Show order items, delivery options

3. **Conversational Messages**:

  - Customer-initiated questions
  - Support responses
  - AI orchestrator responses

**Webhook Flow**:

```
WhatsApp Message → Twilio Webhook → whatsapp-service →
  → Module 12 (Support Hub) → Unified Thread →
  → All Participants (Web + WhatsApp) see message
```

**Cost Considerations**:

- Twilio WhatsApp: ~$0.005-0.01 per message (varies by country)
- Template messages: Free (pre-approved)
- Session messages: Paid per message
- Free tier: 1,000 messages/month for testing
- Estimated MVP cost: $5-50/month (1K-10K messages)

**Database Schema for Chat (Supabase PostgreSQL)**:

```sql
-- Unified conversation threads
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB -- Additional thread metadata
);

-- Conversation participants (multi-party)
CREATE TABLE conversation_participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  user_id UUID REFERENCES users(id), -- Clerk user ID
  user_type VARCHAR(50), -- 'customer', 'vendor', 'hub', 'ai_orchestrator'
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  last_read_at TIMESTAMPTZ,
  UNIQUE(conversation_id, user_id)
);

-- Messages (unified for web + WhatsApp)
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  sender_id UUID REFERENCES users(id),
  sender_type VARCHAR(50),
  content TEXT,
  message_type VARCHAR(50), -- 'text', 'image', 'document', 'location', 'status_update'
  channel VARCHAR(50), -- 'web', 'whatsapp'
  whatsapp_message_id VARCHAR(255), -- Twilio message SID
  status VARCHAR(50), -- 'sent', 'delivered', 'read'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB -- Rich media URLs, location data, etc.
);

-- Message attachments
CREATE TABLE message_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES messages(id),
  file_url TEXT,
  file_type VARCHAR(50),
  file_name VARCHAR(255),
  file_size BIGINT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WhatsApp opt-in tracking
CREATE TABLE whatsapp_opt_ins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  phone_number VARCHAR(20),
  opted_in BOOLEAN DEFAULT FALSE,
  opted_in_at TIMESTAMPTZ,
  opted_out_at TIMESTAMPTZ,
  UNIQUE(user_id, phone_number)
);

-- Enable Supabase Realtime for messages
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE conversation_participants;
```

**Frontend Chat Component (Next.js)**:

- Real-time message subscription via Supabase Realtime
- Typing indicators using Supabase presence
- File upload to Azure Blob Storage
- Message status indicators (sent, delivered, read)
- WhatsApp message badge/indicator
- Channel switcher (if user has both web and WhatsApp)

### IAM Implementation

**Technology**: Clerk + Azure Key Vault

**Implementation**:

- `auth-service/` (integrated with Clerk SDK)
  - `user-auth.ts` - Customer authentication (Clerk)
  - `partner-auth.ts` - Partner authentication (Clerk with custom roles)
  - `admin-auth.ts` - Admin authentication (Clerk with MFA)
  - `agentic-handoff.ts` - SSO 2.0 for AI agents (Clerk's built-in support)
  - `passkey-handler.ts` - FIDO2 passkey support (Clerk native)
  - `link-account.py` - Zero-friction account linking (FastAPI)
  - `agentic-consent-manager.py` - Consent dashboard API
- **Clerk** for all authentication (users, partners, admins)
- **Why Clerk**:
  - Best-in-class for Agentic Handoffs (SSO 2.0) - critical for ChatGPT/Gemini integration
  - Handles complex RBAC natively (capability-based access for partners)
  - Zero infrastructure management (no Azure AD B2C setup complexity)
  - Built-in passkey support (FIDO2)
  - Superior developer experience with React/Next.js
  - Free tier: 10K MAU (sufficient for MVP)
- Custom metadata for capability-based RBAC stored in Clerk user metadata

**Chat-First Requirements**:

1. **Link Account API**:
```python
@router.post("/api/v1/auth/link-account")
async def link_account(
    platform: str,
    platform_user_id: str,
    oauth_token: str
):
    # Verify and link account
    account_link = await create_account_link(...)

    return {
        "data": {
"linked": True,
"session_token": token
        },
        "machine_readable": {
"@context": "https://schema.org",
"@type": "AuthenticationAction",
"result": "Success"
        }
    }
```

2. **Agentic Consent Manager API**:

  - GET `/api/v1/auth/consents` - List active agent consents
  - POST `/api/v1/auth/consents/{id}/revoke` - Revoke consent
  - Returns JSON-LD with consent details

---

## Complete Database Schema - MVP Modules

### Schema Overview

**Database**: Supabase PostgreSQL
**Schema Organization**: `public` schema for MVP
**Naming Conventions**: 
- Tables: `snake_case` (e.g., `order_items`, `time_chain_legs`)
- Columns: `snake_case` (e.g., `created_at`, `partner_id`)
- Indexes: `idx_{table}_{column(s)}` (e.g., `idx_products_partner_id`)

**Migration Strategy**:
- Use Supabase migrations or custom migration tool
- Migration files: `YYYYMMDD_HHMMSS_description.sql`
- All migrations must be reversible (rollback scripts)

### Core Tables - MVP Modules

#### Module 1: Scout Engine

```sql
-- Products table
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  capabilities JSONB, -- Array of capability tags
  metadata JSONB, -- Flexible metadata (images, specs, etc.)
  manifest_url TEXT, -- UCP/ACP manifest URL
  embedding VECTOR(1536), -- pgvector embedding for semantic search
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ -- Soft delete
);

CREATE INDEX idx_products_partner_id ON products(partner_id);
CREATE INDEX idx_products_capabilities ON products USING GIN(capabilities);
CREATE INDEX idx_products_name_search ON products USING GIN(to_tsvector('english', name));
CREATE INDEX idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_products_created_at ON products(created_at DESC);
CREATE INDEX idx_products_deleted_at ON products(deleted_at) WHERE deleted_at IS NULL;

COMMENT ON TABLE products IS 'Product catalog from all partners';
COMMENT ON COLUMN products.capabilities IS 'Array of capability tags for matching';
COMMENT ON COLUMN products.embedding IS 'Vector embedding for semantic search';

-- Product capabilities junction table
CREATE TABLE product_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  capability_tag VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, capability_tag)
);

CREATE INDEX idx_product_capabilities_product_id ON product_capabilities(product_id);
CREATE INDEX idx_product_capabilities_tag ON product_capabilities(capability_tag);

-- Partner manifests cache
CREATE TABLE partner_manifests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  manifest_url TEXT NOT NULL,
  manifest_type VARCHAR(20) NOT NULL, -- 'UCP', 'ACP', 'LEGACY'
  manifest_data JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_validated_at TIMESTAMPTZ,
  validation_status VARCHAR(20) DEFAULT 'pending' -- 'valid', 'invalid', 'pending'
);

CREATE INDEX idx_partner_manifests_partner_id ON partner_manifests(partner_id);
CREATE INDEX idx_partner_manifests_expires_at ON partner_manifests(expires_at);
CREATE INDEX idx_partner_manifests_url ON partner_manifests(manifest_url);

-- Manifest cache metadata
CREATE TABLE manifest_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manifest_url TEXT NOT NULL UNIQUE,
  etag TEXT,
  last_modified TIMESTAMPTZ,
  cache_ttl INTEGER DEFAULT 3600, -- seconds
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  hit_count INTEGER DEFAULT 0,
  last_hit_at TIMESTAMPTZ
);

CREATE INDEX idx_manifest_cache_url ON manifest_cache(manifest_url);
CREATE INDEX idx_manifest_cache_cached_at ON manifest_cache(cached_at);
```

#### Module 4: Intent Resolver

```sql
-- User intents
CREATE TABLE intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  original_text TEXT NOT NULL,
  intent_type VARCHAR(50), -- 'immediate', 'standing'
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'resolved', 'failed'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_intents_user_id ON intents(user_id);
CREATE INDEX idx_intents_status ON intents(status);
CREATE INDEX idx_intents_created_at ON intents(created_at DESC);

-- Intent graphs (Graph of Needs)
CREATE TABLE intent_graphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id UUID REFERENCES intents(id) ON DELETE CASCADE,
  graph_data JSONB NOT NULL, -- Graph of Needs structure
  entities JSONB, -- Extracted entities
  confidence_score DECIMAL(3,2), -- 0.00 to 1.00
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intent_graphs_intent_id ON intent_graphs(intent_id);
CREATE INDEX idx_intent_graphs_graph_data ON intent_graphs USING GIN(graph_data);

-- Extracted entities
CREATE TABLE intent_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id UUID REFERENCES intents(id) ON DELETE CASCADE,
  entity_type VARCHAR(50) NOT NULL, -- 'product', 'date', 'location', 'preference'
  entity_value TEXT NOT NULL,
  confidence DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intent_entities_intent_id ON intent_entities(intent_id);
CREATE INDEX idx_intent_entities_type ON intent_entities(entity_type);
```

#### Module 5: Time-Chain Resolver

```sql
-- Time-chain calculations
CREATE TABLE time_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  total_duration_minutes INTEGER NOT NULL,
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  deadline TIMESTAMPTZ,
  is_feasible BOOLEAN NOT NULL,
  confidence_score DECIMAL(3,2),
  calculation_data JSONB -- Full calculation details
);

CREATE INDEX idx_time_chains_bundle_id ON time_chains(bundle_id);
CREATE INDEX idx_time_chains_deadline ON time_chains(deadline);
CREATE INDEX idx_time_chains_calculated_at ON time_chains(calculated_at DESC);

-- Time-chain legs
CREATE TABLE time_chain_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time_chain_id UUID REFERENCES time_chains(id) ON DELETE CASCADE,
  leg_sequence INTEGER NOT NULL,
  leg_type VARCHAR(50) NOT NULL, -- 'pickup', 'processing', 'delivery', 'wait'
  start_location POINT, -- PostGIS point
  end_location POINT,
  estimated_duration_minutes INTEGER NOT NULL,
  actual_duration_minutes INTEGER,
  deadline TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
  partner_id UUID REFERENCES partners(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_time_chain_legs_time_chain_id ON time_chain_legs(time_chain_id);
CREATE INDEX idx_time_chain_legs_status ON time_chain_legs(status);
CREATE INDEX idx_time_chain_legs_locations ON time_chain_legs USING GIST(start_location, end_location);

-- Route calculations (PostGIS)
CREATE TABLE routes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time_chain_leg_id UUID REFERENCES time_chain_legs(id) ON DELETE CASCADE,
  route_geometry LINESTRING, -- PostGIS linestring
  distance_meters DECIMAL(10,2),
  estimated_duration_seconds INTEGER,
  traffic_factor DECIMAL(3,2) DEFAULT 1.0,
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_routes_leg_id ON routes(time_chain_leg_id);
CREATE INDEX idx_routes_geometry ON routes USING GIST(route_geometry);

-- Conflict simulation results
CREATE TABLE conflict_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  new_item_id UUID REFERENCES products(id),
  has_conflict BOOLEAN NOT NULL,
  time_impact_minutes INTEGER,
  conflicts JSONB, -- Array of conflict details
  suggestions JSONB, -- Proactive suggestions
  analysis_data JSONB, -- Full analysis
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conflict_analyses_order_id ON conflict_analyses(order_id);
CREATE INDEX idx_conflict_analyses_has_conflict ON conflict_analyses(has_conflict);
```

#### Module 6: Autonomous Recovery

```sql
-- Autonomous recovery records (enhanced)
CREATE TABLE autonomous_recoveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  original_leg_id UUID REFERENCES order_legs(id),
  change_request JSONB NOT NULL,
  partner_rejection JSONB NOT NULL,
  recovery_action VARCHAR(50) NOT NULL, -- 'cancelled', 'found_alternative', 'escalated'
  alternative_item_id UUID REFERENCES products(id),
  alternative_vendor_id UUID REFERENCES partners(id),
  timeline_changed BOOLEAN DEFAULT FALSE,
  delay_minutes INTEGER,
  new_timeline JSONB,
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'completed'
  user_approved_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_autonomous_recoveries_order_id ON autonomous_recoveries(order_id);
CREATE INDEX idx_autonomous_recoveries_status ON autonomous_recoveries(status);
CREATE INDEX idx_autonomous_recoveries_created_at ON autonomous_recoveries(created_at DESC);

-- Recovery attempt history
CREATE TABLE recovery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recovery_id UUID REFERENCES autonomous_recoveries(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  search_criteria JSONB,
  alternatives_found INTEGER DEFAULT 0,
  best_alternative_id UUID REFERENCES products(id),
  search_duration_seconds INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recovery_attempts_recovery_id ON recovery_attempts(recovery_id);

-- Alternative search logs
CREATE TABLE alternative_searches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recovery_id UUID REFERENCES autonomous_recoveries(id) ON DELETE CASCADE,
  search_query TEXT NOT NULL,
  results_count INTEGER,
  search_duration_seconds INTEGER,
  filters_applied JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alternative_searches_recovery_id ON alternative_searches(recovery_id);
```

#### Module 7: Premium Registry

```sql
-- Premium products (blanks)
CREATE TABLE premium_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_name VARCHAR(100) NOT NULL,
  product_name TEXT NOT NULL,
  product_type VARCHAR(50) NOT NULL,
  base_price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  description TEXT,
  images JSONB, -- Array of image URLs
  specifications JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_premium_products_brand ON premium_products(brand_name);
CREATE INDEX idx_premium_products_type ON premium_products(product_type);

-- Capability tags taxonomy
CREATE TABLE capability_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tag_name VARCHAR(100) NOT NULL UNIQUE,
  tag_category VARCHAR(50), -- 'service', 'product', 'customization'
  description TEXT,
  parent_tag_id UUID REFERENCES capability_tags(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capability_tags_name ON capability_tags(tag_name);
CREATE INDEX idx_capability_tags_category ON capability_tags(tag_category);
CREATE INDEX idx_capability_tags_parent ON capability_tags(parent_tag_id);

-- Product to capability mappings
CREATE TABLE product_capability_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  capability_tag_id UUID REFERENCES capability_tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, capability_tag_id)
);

CREATE INDEX idx_product_capability_mappings_product ON product_capability_mappings(product_id);
CREATE INDEX idx_product_capability_mappings_tag ON product_capability_mappings(capability_tag_id);
```

#### Module 9: Capability Portal

```sql
-- Partners (enhanced)
CREATE TABLE partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  business_name TEXT NOT NULL,
  business_type VARCHAR(50),
  tax_id VARCHAR(50),
  legal_entity_name TEXT,
  contact_email TEXT NOT NULL,
  contact_phone TEXT,
  address JSONB,
  verification_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'verified', 'rejected'
  trust_score INTEGER DEFAULT 0, -- 0-100
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  verified_at TIMESTAMPTZ
);

CREATE INDEX idx_partners_user_id ON partners(user_id);
CREATE INDEX idx_partners_verification_status ON partners(verification_status);
CREATE INDEX idx_partners_trust_score ON partners(trust_score DESC);
CREATE INDEX idx_partners_is_active ON partners(is_active);

-- Partner capability registrations
CREATE TABLE partner_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  capability_tag_id UUID REFERENCES capability_tags(id) ON DELETE CASCADE,
  service_area JSONB, -- Geographic coverage (PostGIS polygon)
  capacity_limit INTEGER,
  current_capacity INTEGER DEFAULT 0,
  pricing_structure JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id, capability_tag_id)
);

CREATE INDEX idx_partner_capabilities_partner ON partner_capabilities(partner_id);
CREATE INDEX idx_partner_capabilities_tag ON partner_capabilities(capability_tag_id);
CREATE INDEX idx_partner_capabilities_service_area ON partner_capabilities USING GIST(service_area);

-- Real-time capacity tracking
CREATE TABLE capacity_tracking (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_capability_id UUID REFERENCES partner_capabilities(id) ON DELETE CASCADE,
  current_load INTEGER NOT NULL,
  max_capacity INTEGER NOT NULL,
  utilization_percentage DECIMAL(5,2),
  tracked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capacity_tracking_partner_capability ON capacity_tracking(partner_capability_id);
CREATE INDEX idx_capacity_tracking_tracked_at ON capacity_tracking(tracked_at DESC);
```

#### Module 12: Support Hub

```sql
-- Conversation threads
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  order_id UUID REFERENCES orders(id),
  title TEXT,
  status VARCHAR(20) DEFAULT 'active', -- 'active', 'resolved', 'archived'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_conversations_bundle_id ON conversations(bundle_id);
CREATE INDEX idx_conversations_order_id ON conversations(order_id);
CREATE INDEX idx_conversations_status ON conversations(status);

-- Messages (web + WhatsApp)
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  sender_id UUID REFERENCES users(id),
  sender_type VARCHAR(20) NOT NULL, -- 'user', 'partner', 'hub', 'worker', 'ai'
  sender_name TEXT,
  content TEXT NOT NULL,
  message_type VARCHAR(20) DEFAULT 'text', -- 'text', 'image', 'document', 'location'
  channel VARCHAR(20) NOT NULL, -- 'web', 'whatsapp', 'sms', 'email'
  channel_message_id TEXT, -- External channel message ID
  attachments JSONB, -- Array of attachment metadata
  status VARCHAR(20) DEFAULT 'sent', -- 'sent', 'delivered', 'read', 'failed'
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_sent_at ON messages(sent_at DESC);
CREATE INDEX idx_messages_channel ON messages(channel);

-- Thread participants
CREATE TABLE participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  participant_type VARCHAR(20) NOT NULL, -- 'customer', 'partner', 'hub', 'worker', 'admin'
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  last_read_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(conversation_id, user_id)
);

CREATE INDEX idx_participants_conversation_id ON participants(conversation_id);
CREATE INDEX idx_participants_user_id ON participants(user_id);

-- Message attachments
CREATE TABLE message_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type VARCHAR(50),
  file_size_bytes INTEGER,
  storage_url TEXT NOT NULL,
  storage_provider VARCHAR(20) DEFAULT 'azure_blob',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_message_attachments_message_id ON message_attachments(message_id);
```

#### Module 14: Status Narrator

```sql
-- Status update history
CREATE TABLE status_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundles(id),
  status_type VARCHAR(50) NOT NULL,
  previous_status VARCHAR(50),
  new_status VARCHAR(50) NOT NULL,
  narrative TEXT NOT NULL,
  agent_reasoning TEXT,
  adaptive_card JSONB,
  sent_via JSONB, -- Array of channels: ['web', 'whatsapp', 'email']
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_status_updates_order_id ON status_updates(order_id);
CREATE INDEX idx_status_updates_bundle_id ON status_updates(bundle_id);
CREATE INDEX idx_status_updates_created_at ON status_updates(created_at DESC);

-- Progress ledger entries
CREATE TABLE progress_ledgers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID, -- References standing intent orchestration instance
  order_id UUID REFERENCES orders(id),
  step_number INTEGER NOT NULL,
  step_name TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
  thought TEXT, -- Internal reasoning
  narrative TEXT, -- User-facing narrative
  if_then_logic JSONB, -- If/Then conditions visualization
  adaptive_card JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_progress_ledgers_order_id ON progress_ledgers(order_id);
CREATE INDEX idx_progress_ledgers_status ON progress_ledgers(status);
CREATE INDEX idx_progress_ledgers_created_at ON progress_ledgers(created_at DESC);

-- Agent reasoning logs
CREATE TABLE agent_reasoning_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status_update_id UUID REFERENCES status_updates(id),
  reasoning_context JSONB NOT NULL,
  extracted_reasoning TEXT,
  confidence_score DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_reasoning_logs_status_update ON agent_reasoning_logs(status_update_id);
```

#### Module 15: Payment

```sql
-- Orders
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundles(id),
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded'
  payment_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'authorized', 'captured', 'failed', 'refunded'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_bundle_id ON orders(bundle_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Order line items
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),
  partner_id UUID REFERENCES partners(id),
  item_name TEXT NOT NULL,
  quantity INTEGER DEFAULT 1,
  unit_price DECIMAL(10,2) NOT NULL,
  total_price DECIMAL(10,2) NOT NULL,
  customization_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_partner_id ON order_items(partner_id);

-- Payment transactions
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  payment_method VARCHAR(50) NOT NULL, -- 'stripe', 'ap2_token', 'other'
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'authorized', 'captured', 'failed', 'refunded'
  stripe_payment_intent_id TEXT,
  transaction_id TEXT,
  failure_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  authorized_at TIMESTAMPTZ,
  captured_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id);

-- Multi-party payment splits
CREATE TABLE payment_splits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
  recipient_type VARCHAR(20) NOT NULL, -- 'partner', 'platform', 'affiliate'
  recipient_id UUID, -- Partner ID or platform account ID
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  split_type VARCHAR(20), -- 'commission', 'payment', 'fee'
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'transferred', 'failed'
  stripe_transfer_id TEXT,
  transferred_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payment_splits_payment_id ON payment_splits(payment_id);
CREATE INDEX idx_payment_splits_recipient ON payment_splits(recipient_type, recipient_id);
CREATE INDEX idx_payment_splits_status ON payment_splits(status);
```

#### Module 16: Escrow

```sql
-- Escrow accounts
CREATE TABLE escrow_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'held', -- 'held', 'released', 'refunded', 'disputed'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  released_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ
);

CREATE INDEX idx_escrow_accounts_order_id ON escrow_accounts(order_id);
CREATE INDEX idx_escrow_accounts_status ON escrow_accounts(status);

-- Escrow transactions
CREATE TABLE escrow_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  escrow_account_id UUID REFERENCES escrow_accounts(id) ON DELETE CASCADE,
  transaction_type VARCHAR(20) NOT NULL, -- 'deposit', 'release', 'refund', 'hold'
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  recipient_id UUID, -- Partner ID or user ID
  recipient_type VARCHAR(20), -- 'partner', 'user', 'platform'
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'failed'
  transaction_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_escrow_transactions_account_id ON escrow_transactions(escrow_account_id);
CREATE INDEX idx_escrow_transactions_type ON escrow_transactions(transaction_type);
CREATE INDEX idx_escrow_transactions_status ON escrow_transactions(status);

-- Escrow release records
CREATE TABLE escrow_releases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  escrow_account_id UUID REFERENCES escrow_accounts(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id),
  release_trigger VARCHAR(50) NOT NULL, -- 'delivery_confirmed', 'time_chain_complete', 'manual'
  amount DECIMAL(10,2) NOT NULL,
  recipient_id UUID NOT NULL,
  recipient_type VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  released_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escrow_releases_account_id ON escrow_releases(escrow_account_id);
CREATE INDEX idx_escrow_releases_recipient ON escrow_releases(recipient_id, recipient_type);
```

#### Module 24: Omnichannel Broker

```sql
-- Negotiation records
CREATE TABLE negotiations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id),
  partner_id UUID REFERENCES partners(id),
  negotiation_type VARCHAR(50) NOT NULL, -- 'change_request', 'counter_offer', 'availability_check'
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'counter_offered', 'escalated', 'timeout'
  channel VARCHAR(20) NOT NULL, -- 'whatsapp', 'sms', 'email', 'api'
  counter_offer_count INTEGER DEFAULT 0,
  timeout_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  responded_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_negotiations_order_id ON negotiations(order_id);
CREATE INDEX idx_negotiations_partner_id ON negotiations(partner_id);
CREATE INDEX idx_negotiations_status ON negotiations(status);
CREATE INDEX idx_negotiations_timeout_at ON negotiations(timeout_at) WHERE status = 'pending';

-- Negotiation message history
CREATE TABLE negotiation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id) ON DELETE CASCADE,
  message_type VARCHAR(20) NOT NULL, -- 'request', 'response', 'counter_offer'
  content TEXT NOT NULL,
  channel VARCHAR(20) NOT NULL,
  channel_message_id TEXT,
  metadata JSONB, -- Enriched data (images, prices, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_negotiation_messages_negotiation_id ON negotiation_messages(negotiation_id);
CREATE INDEX idx_negotiation_messages_created_at ON negotiation_messages(created_at DESC);

-- Communication preferences
CREATE TABLE communication_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  channel VARCHAR(20) NOT NULL, -- 'whatsapp', 'sms', 'email', 'api'
  channel_identifier TEXT NOT NULL, -- Phone number, email, API endpoint
  is_preferred BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id, channel)
);

CREATE INDEX idx_communication_preferences_partner_id ON communication_preferences(partner_id);
CREATE INDEX idx_communication_preferences_channel ON communication_preferences(channel);

-- HITL escalation records
CREATE TABLE escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id) ON DELETE CASCADE,
  escalation_reason VARCHAR(50) NOT NULL, -- 'timeout', 'sentiment', 'deadlock', 'urgency'
  severity VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'assigned', 'in_progress', 'resolved'
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_escalations_negotiation_id ON escalations(negotiation_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_severity ON escalations(severity DESC);
```

#### Module 25: Partner Simulator

```sql
-- Simulated partners
CREATE TABLE simulated_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  business_type VARCHAR(50),
  location POINT, -- PostGIS point
  communication_channel VARCHAR(20) NOT NULL, -- 'whatsapp', 'sms', 'api'
  channel_identifier TEXT NOT NULL,
  trust_score INTEGER DEFAULT 80,
  reliability_metrics JSONB,
  business_hours JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_partners_name ON simulated_partners(name);
CREATE INDEX idx_simulated_partners_location ON simulated_partners USING GIST(location);
CREATE INDEX idx_simulated_partners_is_active ON simulated_partners(is_active);

-- Simulated products
CREATE TABLE simulated_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  inventory_count INTEGER,
  availability_rule VARCHAR(50) DEFAULT 'always', -- 'always', 'conditional', 'out_of_stock'
  availability_conditions JSONB,
  images JSONB,
  capabilities JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_products_partner_id ON simulated_products(simulated_partner_id);
CREATE INDEX idx_simulated_products_availability ON simulated_products(availability_rule);

-- Response scenario configurations
CREATE TABLE simulated_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  scenario_type VARCHAR(50) NOT NULL, -- 'rejection', 'unavailable', 'slow', 'counter_offer', 'accept'
  trigger_conditions JSONB NOT NULL,
  response_template TEXT NOT NULL,
  response_type VARCHAR(20) DEFAULT 'automated', -- 'automated', 'manual'
  response_delay_seconds INTEGER DEFAULT 0,
  randomization JSONB, -- Randomization rules
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_responses_partner_id ON simulated_responses(simulated_partner_id);
CREATE INDEX idx_simulated_responses_scenario_type ON simulated_responses(scenario_type);

-- Simulation activity logs
CREATE TABLE simulation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  request_type VARCHAR(50) NOT NULL,
  request_data JSONB,
  response_data JSONB,
  response_time_ms INTEGER,
  scenario_triggered VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulation_logs_partner_id ON simulation_logs(simulated_partner_id);
CREATE INDEX idx_simulation_logs_created_at ON simulation_logs(created_at DESC);
```

### Supporting Tables

```sql
-- Users (Clerk integration)
CREATE TABLE users (
  id UUID PRIMARY KEY, -- Clerk user ID
  email TEXT,
  phone_number TEXT,
  legal_name TEXT,
  display_name TEXT,
  metadata JSONB, -- Additional user data
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone_number);

-- Bundles
CREATE TABLE bundles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  intent_id UUID REFERENCES intents(id),
  bundle_name TEXT,
  total_price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'confirmed', 'processing', 'completed', 'cancelled'
  visibility_mode VARCHAR(20) DEFAULT 'transparent', -- 'transparent', 'concierge', 'hybrid'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  confirmed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_bundles_user_id ON bundles(user_id);
CREATE INDEX idx_bundles_status ON bundles(status);
CREATE INDEX idx_bundles_created_at ON bundles(created_at DESC);

-- Bundle legs
CREATE TABLE bundle_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  leg_sequence INTEGER NOT NULL,
  product_id UUID REFERENCES products(id),
  partner_id UUID REFERENCES partners(id),
  leg_type VARCHAR(50) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  customization_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bundle_legs_bundle_id ON bundle_legs(bundle_id);
CREATE INDEX idx_bundle_legs_sequence ON bundle_legs(bundle_id, leg_sequence);

-- Order legs (for tracking)
CREATE TABLE order_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  bundle_leg_id UUID REFERENCES bundle_legs(id),
  partner_id UUID REFERENCES partners(id),
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_order_legs_order_id ON order_legs(order_id);
CREATE INDEX idx_order_legs_partner_id ON order_legs(partner_id);
CREATE INDEX idx_order_legs_status ON order_legs(status);

-- Webhook deliveries
CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL, -- 'chatgpt', 'gemini', 'whatsapp'
  thread_id VARCHAR(255) NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'delivered', 'failed'
  delivered_at TIMESTAMPTZ,
  retry_count INTEGER DEFAULT 0,
  failure_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_platform_thread ON webhook_deliveries(platform, thread_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX idx_webhook_deliveries_created_at ON webhook_deliveries(created_at DESC);

-- Chat thread mappings (from 02-architecture.md)
CREATE TABLE chat_thread_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL, -- 'chatgpt', 'gemini', 'whatsapp'
  thread_id VARCHAR(255) NOT NULL,
  platform_user_id VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, thread_id)
);

CREATE INDEX idx_chat_thread_mappings_user_id ON chat_thread_mappings(user_id);
CREATE INDEX idx_chat_thread_mappings_platform_thread ON chat_thread_mappings(platform, thread_id);

-- Account links (from 02-architecture.md)
CREATE TABLE account_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL, -- 'google', 'openai', 'apple'
  platform_user_id VARCHAR(255) NOT NULL,
  oauth_token_hash TEXT,
  permissions JSONB,
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, platform, platform_user_id)
);

CREATE INDEX idx_account_links_user_id ON account_links(user_id);
CREATE INDEX idx_account_links_platform ON account_links(platform);
```

### Indexes Strategy

**Primary Indexes**: All tables have UUID PRIMARY KEY with `gen_random_uuid()` default

**Foreign Key Indexes**: All foreign keys have indexes for JOIN performance

**Query Optimization Indexes**:
- Frequently queried columns: `status`, `created_at`, `user_id`, `partner_id`, `order_id`
- Composite indexes for multi-column queries: `(bundle_id, leg_sequence)`, `(platform, thread_id)`
- Partial indexes for filtered queries: `WHERE deleted_at IS NULL`, `WHERE status = 'pending'`

**Special Indexes**:
- **GIN indexes** for JSONB columns: `capabilities`, `metadata`, `graph_data`
- **GIST indexes** for PostGIS: `POINT`, `LINESTRING`, `POLYGON` columns
- **ivfflat indexes** for pgvector: `embedding` columns for semantic search
- **Full-text search indexes**: `to_tsvector` for text search

### Data Retention Policies

- **Order history**: 2 years (then archive to cold storage)
- **Logs**: 90 days (then delete)
- **Cache**: TTL-based (auto-expire)
- **Status updates**: 1 year
- **Messages**: 1 year (then archive)
- **Simulation logs**: 30 days (testing data)

### Migration Scripts Structure

**Naming Convention**: `YYYYMMDD_HHMMSS_description.sql`

**Example**: `20240115_143000_create_products_table.sql`

**Migration Template**:
```sql
-- Migration: Create products table
-- Date: 2024-01-15
-- Description: Initial products table for Module 1

BEGIN;

CREATE TABLE products (
  -- table definition
);

CREATE INDEX idx_products_partner_id ON products(partner_id);

COMMENT ON TABLE products IS 'Product catalog from all partners';

COMMIT;

-- Rollback script (separate file: YYYYMMDD_HHMMSS_description_rollback.sql)
-- BEGIN;
-- DROP TABLE IF EXISTS products;
-- COMMIT;
```
