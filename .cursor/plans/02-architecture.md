---
name: AI Universal Service Orchestrator Platform - Architecture
overview: Architecture Overview, Design System, Chat-First Standards
todos: []
---

# Architecture Overview

## System Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  Next.js on Vercel (Edge) + React Native Mobile + PWA   │
└─────────────────────────────────────────────────────────┘
│
┌─────────────────────────────────────────────────────────┐
│                   API Gateway Layer                      │
│         Azure API Management (Consumption)              │
└─────────────────────────────────────────────────────────┘
│
┌─────────────────────────────────────────────────────────┐
│            Microservices Layer (Azure Container Apps)    │
│  ┌──────────────┐  AI Agents entry (ChatGPT, Gemini)    │
│  │Orchestrator │  POST /api/v1/chat → Intent + Discovery │
│  │(FastAPI)    │                                        │
│  └──────────────┘                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │Discovery │  │Intent    │  │Time-Chain│  │Payment   ││
│  │Service   │  │Resolver  │  │Resolver  │  │Service   ││
│  │(FastAPI) │  │(FastAPI) │  │(FastAPI) │  │(FastAPI) ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │Partner   │  │Task      │  │Support   │  │IAM       ││
│  │Portal    │  │Queue     │  │Hub       │  │(Clerk)   ││
│  └──────────┘  └──────────┘  │(Chat+    │  └──────────┘│
│                               │WhatsApp) │             │
│  ┌──────────┐                 └──────────┘             │
│  │WhatsApp  │                 ┌──────────┐             │
│  │Service   │                 │Status    │             │
│  └──────────┘                 │Narrator  │             │
│  ┌──────────┐                 └──────────┘             │
│  │Curation  │                 ┌──────────┐             │
│  │Service   │                 │Storefront│             │
│  │(Module20)│                 │Platform  │             │
│  └──────────┘                 └──────────┘             │
│  ┌──────────┐                 ┌──────────┐             │
│  │Affiliate │                 │Curation  │             │
│  │Service   │                 │Picker    │             │
│  │(Module21)│                 │(Module22)│             │
│  └──────────┘                 └──────────┘             │
│  ┌──────────┐                 ┌──────────┐             │
│  │Standing  │                 │Omnichannel│             │
│  │Intent    │                 │Broker     │             │
│  │(Module23)│                 │(Module24) │             │
│  │Durable   │                 │+ HITL     │             │
│  │Functions │                 │Escalation │             │
│  └──────────┘                 └──────────┘             │
└─────────────────────────────────────────────────────────┘
│
┌─────────────────────────────────────────────────────────┐
│                  Data & Storage Layer                    │
│  Supabase (PostgreSQL+pgvector) │ Upstash Redis │       │
│  Azure Blob Storage │ Service Bus                       │
└─────────────────────────────────────────────────────────┘
│
┌─────────────────────────────────────────────────────────┐
│                  External Integrations                   │
│  UCP/ACP │ Stripe │ Azure OpenAI │ Gemini │ Retailer   │
│  Twilio WhatsApp API                                     │
└─────────────────────────────────────────────────────────┘
```

## Design System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Design System Package                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │Design Tokens │  │  Components  │  │   Themes     │ │
│  │- Colors      │  │- Button      │  │- Default     │ │
│  │- Typography  │  │- Card        │  │- Presets     │ │
│  │- Spacing     │  │- Input       │  │- Generator   │ │
│  │- Shadows     │  │- Navigation  │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
│
┌───────────┴───────────┐
│                       │
▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Main Platform App      │  │  Partner Storefronts     │
│   (Next.js)              │  │  (Multi-tenant)          │
│   - Uses design-system   │  │  - Uses design-system   │
│   - Default theme        │  │  - Custom themes         │
└──────────────────────────┘  └──────────────────────────┘
│                       │
└───────────┬───────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│         Runtime Theme Injection                         │
│  CSS Custom Properties (CSS Variables)                   │
│  :root[data-theme="partner-123"] {                      │
│    --color-primary: #3b82f6;                            │
│    --font-family: 'Inter', sans-serif;                   │
│    ...                                                    │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│              Rendered UI                                 │
│  - Consistent components                                 │
│  - Partner-specific branding                             │
│  - Maintained design quality                             │
└─────────────────────────────────────────────────────────┘
```

## WhatsApp Integration Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Customer (WhatsApp)                   │
└─────────────────────────────────────────────────────────┘
│
│ Sends Message
▼
┌─────────────────────────────────────────────────────────┐
│              Twilio WhatsApp Business API                │
└─────────────────────────────────────────────────────────┘
│
│ Webhook
▼
┌─────────────────────────────────────────────────────────┐
│            WhatsApp Service (Container Apps)             │
│  - Webhook Handler                                        │
│  - Message Parser                                         │
│  - Channel Bridge                                         │
└─────────────────────────────────────────────────────────┘
│
│ Store & Route
▼
┌─────────────────────────────────────────────────────────┐
│         Support Hub Service (Module 12)                 │
│  - Unified Thread Manager                                 │
│  - Multi-party Router                                     │
└─────────────────────────────────────────────────────────┘
│
┌───────────┴───────────┐
│                       │
▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Supabase Realtime      │  │   Supabase PostgreSQL   │
│   (Web Chat)             │  │   (Message History)     │
└──────────────────────────┘  └──────────────────────────┘
│                       │
└───────────┬───────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│         All Participants See Message                     │
│  - Customer (WhatsApp)                                   │
│  - Customer (Web Chat)                                   │
│  - Vendors (Web Chat)                                    │
│  - Hubs (Web Chat)                                       │
│  - AI Orchestrator (Web Chat)                            │
└─────────────────────────────────────────────────────────┘
```

## Status Update Flow

```
┌─────────────────────────────────────────────────────────┐
│         Time-Chain Resolver (Module 5)                  │
│         Status Narrator (Module 14)                     │
│         Escrow Manager (Module 16)                      │
└─────────────────────────────────────────────────────────┘
│
│ Status Change Event
▼
┌─────────────────────────────────────────────────────────┐
│            WhatsApp Service                              │
│  - Status Notifier                                       │
│  - Template Manager                                      │
└─────────────────────────────────────────────────────────┘
│
│ Send Template Message
▼
┌─────────────────────────────────────────────────────────┐
│         Twilio WhatsApp API                             │
│  - Template: "Your order status: {status}"              │
│  - Interactive: Quick Reply Buttons                      │
└─────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│              Customer (WhatsApp)                        │
│  Receives: "Your gift box has been picked up!"          │
│  Can Reply: "Track Order" | "Contact Support"            │
└─────────────────────────────────────────────────────────┘
```

## Chat-First / Headless Architecture

```
┌─────────────────────────────────────────────────────────┐
│              AI Agent Interfaces                         │
│  ChatGPT │ Gemini │ Custom Agents │ WhatsApp             │
└─────────────────────────────────────────────────────────┘
│
│ REST API + JSON-LD
│ Adaptive Cards
│ Webhook Callbacks
▼
┌─────────────────────────────────────────────────────────┐
│              API Gateway Layer                           │
│  Azure API Management (Chat-First Endpoints)             │
│  - Standardized REST API                                 │
│  - JSON-LD in all responses                              │
│  - Adaptive Cards for complex states                     │
└─────────────────────────────────────────────────────────┘
│
│
┌─────────────────────────────────────────────────────────┐
│            Microservices Layer                           │
│  All services expose Chat-First APIs                    │
└─────────────────────────────────────────────────────────┘
│
│ Async Updates
▼
┌─────────────────────────────────────────────────────────┐
│         Webhook Push Notification Bridge                 │
│  - Durable Functions → Chat Thread Updates               │
│  - Real-time status pushes                               │
│  - Platform-specific webhooks (ChatGPT, Gemini)          │
└─────────────────────────────────────────────────────────┘
```

# Chat-First Implementation Standards

## API-First Development Requirements

**All API Endpoints Must**:

1. **Standardized Response Format**:
```json
{
  "data": {
    // Response data
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "Product",
    // JSON-LD structured data
  },
  "adaptive_card": {
    // Optional: Adaptive Card JSON for complex states
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
  }
}
```

2. **JSON-LD Machine-Readable Block**:

- Every response includes `machine_readable` field
- Uses Schema.org vocabulary
- Enables LLM to parse and understand responses
- Example types: Product, Offer, Order, Person, Organization

3. **API Versioning**:

- All endpoints: `/api/v1/...`
- Backward compatibility maintained
- Deprecation notices in responses

## Generative UI Support

**Adaptive Cards Implementation**:

1. **Card Types**:

- **Product Card**: Product details with image, price, capabilities
- **Bundle Card**: Bundle composition with timeline
- **Proof Card**: Virtual proofing preview with approval buttons
- **Time-Chain Card**: Visual timeline of multi-leg journey
- **Progress Ledger Card**: Standing intent progress with thoughts/narratives
- **Checkout Card**: Order summary with instant checkout button

2. **Card Schema Example**:
```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "Product Name",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "Image",
      "url": "https://...",
      "size": "Medium"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Price", "value": "$99.99"},
        {"title": "Capabilities", "value": "Embroidery, Engraving"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "Add to Bundle",
      "data": {
        "action": "add_to_bundle",
        "product_id": "uuid"
      }
    }
  ]
}
```

3. **Platform-Specific Triggers**:

- **Gemini**: Dynamic View triggers for rich UI
- **ChatGPT**: Instant Checkout for one-click purchases
- **WhatsApp**: Interactive message buttons

## Asynchronous Webhooks

**Webhook Push Notification Bridge**:

1. **Webhook Architecture**:
```python
# Webhook service (FastAPI on Container Apps)
@router.post("/webhooks/chat/{platform}/{thread_id}")
async def push_to_chat(
    platform: str,  # 'chatgpt', 'gemini', 'whatsapp'
    thread_id: str,
    update_data: dict
):
    # Route to platform-specific webhook handler
    if platform == 'chatgpt':
        await send_chatgpt_webhook(thread_id, update_data)
    elif platform == 'gemini':
        await send_gemini_webhook(thread_id, update_data)
    # ...
```

2. **Durable Functions Integration**:
```python
# In Status Narrator Activity (Module 23)
def status_narrator_activity(context: df.DurableActivityContext):
    status_data = context.get_input()

    # Write to Progress Ledger
    write_progress_log(...)

    # Push to chat thread via webhook
    if status_data.get('chat_thread_id'):
        send_webhook_update(
platform=status_data['platform'],
thread_id=status_data['chat_thread_id'],
update={
'narrative': status_data['narrative'],
'adaptive_card': generate_progress_card(status_data)
}
        )
```

3. **Webhook Endpoints**:

- `/webhooks/chat/chatgpt/{thread_id}` - ChatGPT updates
- `/webhooks/chat/gemini/{thread_id}` - Gemini updates
- `/webhooks/chat/whatsapp/{phone_number}` - WhatsApp updates
- `/webhooks/standing-intent/{instance_id}` - Standing intent updates

4. **Database Schema**:
```sql
-- Chat thread mappings
CREATE TABLE chat_thread_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL, -- 'chatgpt', 'gemini', 'whatsapp'
  thread_id VARCHAR(255) NOT NULL, -- Platform-specific thread ID
  platform_user_id VARCHAR(255), -- User ID in platform
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, thread_id)
);

-- Webhook delivery log
CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL,
  thread_id VARCHAR(255) NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'delivered', 'failed'
  delivered_at TIMESTAMPTZ,
  retry_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```


## Zero-Friction Auth

**Link Account Flows**:

1. **One-Tap Account Linking**:

- User in ChatGPT/Gemini clicks "Link Account"
- Redirects to platform with OAuth token
- One tap to bind Google/OpenAI identity to USO account
- Returns to chat with session established

2. **Implementation**:
```python
# Link Account endpoint
@router.post("/auth/link-account")
async def link_account(
    platform: str,  # 'google', 'openai'
    platform_user_id: str,
    oauth_token: str,
    user_id: UUID  # Optional: if user already logged in
):
    # Verify OAuth token with platform
    verified = verify_oauth_token(platform, oauth_token)

    if verified:
        # Create or update account link
        account_link = create_account_link(
user_id=user_id,
platform=platform,
platform_user_id=platform_user_id,
oauth_token_hash=hash_token(oauth_token)
        )

        # Return session token
        return {
"data": {
"linked": True,
"session_token": generate_session_token(user_id)
},
"machine_readable": {
"@context": "https://schema.org",
"@type": "AuthenticationAction",
"result": "Success"
}
        }
```

3. **Agentic Consent Manager**:

- Dashboard showing which AI agents have active tokens
- Token permissions (can purchase, can modify orders, etc.)
- Revoke access functionality
- Token expiration management

4. **Database Schema**:
```sql
-- Account links
CREATE TABLE account_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL, -- 'google', 'openai', 'apple'
  platform_user_id VARCHAR(255) NOT NULL,
  oauth_token_hash TEXT, -- Hashed token
  permissions JSONB, -- Token permissions
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, platform, platform_user_id)
);

-- Agentic consent records
CREATE TABLE agentic_consents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(100) NOT NULL, -- 'ChatGPT', 'Gemini', etc.
  permissions JSONB NOT NULL, -- What agent can do
  token_id UUID REFERENCES account_links(id),
  consented_at TIMESTAMPTZ DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);
```


## Module-Specific Chat-First Requirements

**All Modules Must Implement**:

- **Module 1 (Scout Engine)**: JSON-LD Product schema, Product Adaptive Card, webhook for inventory updates
- **Module 4 (Intent Resolver)**: JSON-LD Intent schema, Intent confirmation Adaptive Card, standing intent API
- **Module 5 (Time-Chain Resolver)**: JSON-LD Order schema with timeline, Time-Chain Adaptive Card, webhook for timeline changes
- **Module 8 (Virtual Proofing)**: Proof preview Adaptive Card, JSON-LD ImageObject schema, approval actions in card
- **Module 12 (Support Hub)**: Message thread Adaptive Card, webhook for new messages, Link Account for chat participants
- **Module 15 (Payment)**: Checkout Adaptive Card, Instant Checkout support (ChatGPT), JSON-LD Payment schema
- **Module 23 (Standing Intent)**: Progress Ledger Adaptive Card, webhook push for status updates, JSON-LD for intent state
- **Module 24 (Omnichannel Broker)**: Negotiation Adaptive Cards, multi-channel webhooks, JSON-LD for negotiation state, escalation notifications

## Error Handling & Resilience Patterns

### Standardized Error Response Format

All API endpoints must return errors in a consistent format to enable proper error handling by AI agents and clients.

**Error Response Schema**:
```json
{
  "error": {
    "code": "SCOUT_001",
    "message": "Failed to fetch manifest from partner",
    "category": "transient",
    "details": {
      "partner_id": "uuid",
      "manifest_url": "https://...",
      "retry_after": 30
    },
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "Error",
    "errorCode": "SCOUT_001",
    "description": "Failed to fetch manifest from partner"
  }
}
```

**Error Code Format**: `{MODULE}_{NUMBER}`
- Module prefix: `SCOUT`, `INTENT`, `TIMECHAIN`, `RECOVERY`, `PAYMENT`, etc.
- Number: 3-digit error code (001-999)
- Examples:
  - `SCOUT_001`: Manifest fetch failure
  - `INTENT_002`: LLM service unavailable
  - `PAYMENT_003`: Payment processing timeout

**HTTP Status Code Mapping**:
- `400 Bad Request`: Client errors (validation, invalid input)
- `401 Unauthorized`: Authentication failures
- `403 Forbidden`: Authorization failures
- `404 Not Found`: Resource not found
- `409 Conflict`: Business rule violations
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: System errors
- `503 Service Unavailable`: Service temporarily unavailable
- `504 Gateway Timeout`: Upstream service timeout

### Error Categories

**1. Transient Errors (Retryable)**
- Network timeouts
- Temporary service unavailability (503, 504)
- Rate limit exceeded (429) - retry after delay
- Database connection failures
- External API temporary failures

**2. Permanent Errors (Non-Retryable)**
- Invalid input (400)
- Authentication failures (401)
- Authorization failures (403)
- Resource not found (404)
- Business rule violations (409)

**3. User Errors**
- Validation failures
- Invalid request format
- Missing required fields
- Business rule violations (e.g., "Order already cancelled")

**4. System Errors**
- Internal server errors (500)
- Database errors
- Service configuration errors
- Unexpected exceptions

### Retry Policies

**Exponential Backoff Configuration**:
```python
# Retry configuration per service
RETRY_CONFIG = {
    "scout_engine": {
        "max_attempts": 3,
        "initial_delay": 1.0,  # seconds
        "max_delay": 10.0,
        "exponential_base": 2.0,
        "retryable_codes": ["SCOUT_001", "SCOUT_002", "SCOUT_003"]
    },
    "intent_resolver": {
        "max_attempts": 2,
        "initial_delay": 2.0,
        "max_delay": 8.0,
        "exponential_base": 2.0,
        "retryable_codes": ["INTENT_001", "INTENT_002"]
    },
    "payment_service": {
        "max_attempts": 3,
        "initial_delay": 5.0,
        "max_delay": 30.0,
        "exponential_base": 2.0,
        "retryable_codes": ["PAYMENT_001", "PAYMENT_002"]
    }
}
```

**Retry Headers in Responses**:
- `Retry-After`: Seconds to wait before retry (for 429, 503)
- `X-Retry-Count`: Current retry attempt number
- `X-Max-Retries`: Maximum retry attempts allowed

**Retry Implementation Example**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(TransientError)
)
async def fetch_manifest(manifest_url: str):
    # Implementation with automatic retry
    pass
```

### Circuit Breaker Pattern

Circuit breakers prevent cascading failures by stopping requests to failing services.

**Circuit Breaker States**:
- **Closed**: Normal operation, requests pass through
- **Open**: Service failing, requests fail fast without calling service
- **Half-Open**: Testing if service recovered, allowing limited requests

**Configuration**:
```python
CIRCUIT_BREAKER_CONFIG = {
    "scout_engine": {
        "failure_threshold": 5,  # Open after 5 failures
        "success_threshold": 2,  # Close after 2 successes (half-open)
        "timeout": 60,  # Seconds before trying half-open
        "fallback": "return_cached_results"
    },
    "intent_resolver": {
        "failure_threshold": 3,
        "success_threshold": 1,
        "timeout": 30,
        "fallback": "use_rule_based_parsing"
    }
}
```

**Fallback Behaviors**:
- **Module 1 (Scout Engine)**: Return cached results, partial results, or empty results with warning
- **Module 4 (Intent Resolver)**: Fallback to rule-based parsing if LLM unavailable
- **Module 5 (Time-Chain)**: Return estimated timeline based on historical data
- **Module 6 (Autonomous Recovery)**: Escalate to human if no alternative found
- **Module 12 (Support Hub)**: Queue messages if real-time fails, deliver when available
- **Module 15 (Payment)**: Queue payment for retry, notify user of delay

**Circuit Breaker Implementation Example**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def scout_products(intent: str, location: str):
    try:
        return await scout_engine.search(intent, location)
    except Exception as e:
        # Fallback to cache
        return await get_cached_results(intent, location)
```

### Timeout Configuration

**Timeout Values by Service Type**:
```python
TIMEOUT_CONFIG = {
    "scout_queries": 5.0,  # 5 seconds for product discovery
    "intent_resolution": 10.0,  # 10 seconds for LLM processing
    "timechain_calculation": 30.0,  # 30 seconds for route optimization
    "payment_processing": 60.0,  # 60 seconds for payment
    "webhook_delivery": 10.0,  # 10 seconds for webhook calls
    "database_queries": 5.0,  # 5 seconds for database operations
    "external_api_calls": 15.0  # 15 seconds for partner APIs
}
```

**Timeout Handling**:
- Return timeout error with `504 Gateway Timeout` status
- Log timeout for monitoring
- Trigger circuit breaker if timeouts exceed threshold
- Implement graceful degradation (return partial results if possible)

**Timeout Implementation Example**:
```python
import asyncio
from fastapi import HTTPException

async def scout_with_timeout(intent: str, location: str):
    try:
        return await asyncio.wait_for(
            scout_engine.search(intent, location),
            timeout=TIMEOUT_CONFIG["scout_queries"]
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "SCOUT_004",
                "message": "Scout query timeout",
                "category": "transient"
            }
        )
```

### Graceful Degradation Strategies

**Module 1 (Scout Engine)**:
- Fallback to cached results if manifest fetch fails
- Return partial results if some partners unavailable
- Use semantic search on cached data if real-time search fails

**Module 4 (Intent Resolver)**:
- Fallback to rule-based parsing if LLM service unavailable
- Use keyword matching if entity extraction fails
- Return simplified intent graph if full parsing fails

**Module 5 (Time-Chain Resolver)**:
- Return estimated timeline based on historical data if calculation fails
- Use simplified route calculation if full optimization fails
- Skip conflict simulation if route data unavailable

**Module 6 (Autonomous Recovery)**:
- Escalate to human admin if no alternative found
- Use broader search criteria if initial search fails
- Accept longer timeline if no exact match found

**Module 12 (Support Hub)**:
- Queue messages if real-time delivery fails
- Store in database and deliver when service recovers
- Fallback to email notifications if chat unavailable

**Module 15 (Payment)**:
- Retry payment with exponential backoff
- Queue payment for later processing if immediate processing fails
- Notify user of payment delay
- Escalate to support if payment fails after retries

### Dead Letter Queue (DLQ) Handling

**DLQ Configuration**:
- Failed messages after max retries sent to DLQ
- DLQ monitored for alerting
- DLQ messages processed manually or via admin dashboard

**DLQ Processing**:
```python
# DLQ message structure
{
    "message_id": "uuid",
    "original_topic": "order_processing",
    "failure_reason": "Payment service timeout",
    "retry_count": 3,
    "original_message": {...},
    "failed_at": "2024-01-15T10:30:00Z"
}
```

**DLQ Alerts**:
- Alert when DLQ message count > 10
- Alert when DLQ message count > 100 (critical)
- Daily DLQ review process

### Error Logging Standards

**Structured Logging Format**:
```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "ERROR",
    "service": "scout-engine",
    "request_id": "uuid",
    "user_id": "uuid",
    "error_code": "SCOUT_001",
    "message": "Failed to fetch manifest from partner",
    "category": "transient",
    "context": {
        "partner_id": "uuid",
        "manifest_url": "https://...",
        "retry_count": 2,
        "http_status": 503
    },
    "stack_trace": "...",
    "correlation_id": "uuid"
}
```

**Log Levels**:
- **ERROR**: System errors, failures requiring attention, exceptions
- **WARN**: Degraded performance, recoverable errors, retryable failures
- **INFO**: Important business events (order created, payment processed)
- **DEBUG**: Detailed debugging information (development only)

**What to Log**:
- All API requests: `request_id`, `endpoint`, `user_id`, `timestamp`, `duration`
- All errors: `error_code`, `category`, `context`, `stack_trace`, `request_id`
- Business events: `order_id`, `event_type`, `user_id`, `timestamp`
- Performance metrics: `query_time`, `api_latency`, `cache_hit`
- Security events: `auth_failure`, `authorization_denial`, `suspicious_activity`

**Error Correlation**:
- Use `request_id` to trace errors across services
- Use `correlation_id` for related operations (e.g., all operations for an order)
- Include `user_id` for user-specific error tracking
- Include `order_id` or `bundle_id` for business context

**Log Aggregation**:
- All logs sent to Azure Log Analytics
- Structured JSON format for easy querying
- Log retention: 90 days for production, 30 days for development
- Error logs retained for 1 year for compliance
