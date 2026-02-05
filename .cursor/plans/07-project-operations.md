---
name: AI Universal Service Orchestrator Platform - Project Operations
overview: Project Structure, Cost Optimization, Security, Testing, Deployment, Technology Comparison
todos: []
---

# Project Operations

## Project Structure

```
/
├── apps/
│   ├── web/                    # Next.js web application (main platform)
│   │   ├── app/                # App Router pages
│   │   ├── components/         # App-specific components
│   │   └── lib/                # Client utilities
│   ├── mobile/                 # React Native app (shared codebase)
│   │   ├── src/
│   │   │   ├── screens/        # Mobile screens (parallel to web pages)
│   │   │   ├── components/     # Mobile-specific components
│   │   │   ├── navigation/    # React Navigation setup
│   │   │   └── services/      # Mobile services (push, camera, GPS)
│   │   ├── ios/                # iOS native code
│   │   └── android/           # Android native code
│   ├── storefront-platform/   # Multi-tenant storefront system
│   │   ├── storefront-builder/ # Visual customization interface
│   │   ├── storefront-runtime/ # Runtime storefront renderer
│   │   └── api/                # Storefront management API
│   └── admin/                  # Admin dashboard (Next.js)
│       └── mobile/            # Admin mobile app (React Native)
├── packages/
│   ├── design-system/          # Core design system package
│   │   ├── tokens/             # Design tokens
│   │   ├── components/         # Base components
│   │   ├── themes/             # Theme definitions
│   │   └── utils/              # Theme utilities
│   ├── ui-components/          # Shared UI components (uses design-system)
│   │   ├── product-card/       # Product display components
│   │   ├── checkout/           # Checkout flow components
│   │   ├── navigation/        # Navigation components
│   │   └── chat/               # Chat components (Module 12)
│   └── shared/
│       ├── types/              # TypeScript types
│       ├── schemas/            # Zod/JSON schemas
│       └── utils/              # Shared utilities
├── services/
│   ├── orchestrator-service/    # AI Agents entry point (FastAPI on Container Apps)
│   │   ├── api/
│   │   │   └── chat.py         # POST /api/v1/chat (Intent → Discovery)
│   │   └── clients.py          # Intent + Discovery service clients
│   ├── discovery-service/      # Module 1 (FastAPI on Container Apps)
│   │   ├── api/
│   │   │   └── chat-first.py  # Chat-First API endpoints
│   │   └── adaptive-cards/    # Adaptive Card generators
│   ├── intent-service/         # Module 4 (FastAPI on Container Apps)
│   │   ├── api/
│   │   │   └── chat-first.py  # Chat-First API endpoints
│   │   └── adaptive-cards/     # Intent Adaptive Cards
│   ├── timechain-service/      # Module 5 (FastAPI on Container Apps)
│   ├── re-sourcing-service/    # Module 6 (FastAPI on Container Apps) - MVP Critical
│   │   ├── autonomous-recovery.py # Main recovery orchestrator
│   │   ├── partner-rejection-handler.py # Handles partner "No" responses
│   │   ├── alternative-finder.py # Finds alternatives using Scout Engine
│   │   ├── order-cancellation.py # Cancels original orders
│   │   ├── bundle-updater.py # Updates bundle with new items
│   │   ├── timeline-recalculator.py # Recalculates Time-Chain
│   │   └── recovery-notifier.py # Notifies user of recovery
│   ├── registry-service/        # Module 7 (FastAPI on Container Apps)
│   ├── partner-portal/         # Module 9 (Next.js on Vercel)
│   ├── support-service/        # Module 12 (FastAPI on Container Apps)
│   ├── partner-simulator/      # Module 25 (Next.js on Vercel) - MVP Critical
│   │   ├── simulator-dashboard.tsx
│   │   ├── partner-builder.tsx
│   │   ├── product-manager.tsx
│   │   ├── scenario-builder.tsx
│   │   ├── response-manager.tsx
│   │   ├── manual-response-queue.tsx
│   │   └── live-demo-setup.tsx
│   ├── partner-simulator-api/  # Module 25 (FastAPI on Container Apps)
│   │   ├── simulator-engine.py
│   │   ├── partner-factory.py
│   │   ├── response-handler.py
│   │   ├── automated-response-engine.py
│   │   ├── manual-response-queue.py
│   │   ├── scenario-executor.py
│   │   ├── product-generator.py
│   │   └── webhook-handler.py
│   ├── webhook-service/        # Webhook Push Notification Bridge
│   │   ├── chatgpt-webhook.py  # ChatGPT webhook handler
│   │   ├── gemini-webhook.py   # Gemini webhook handler
│   │   └── whatsapp-webhook.py # WhatsApp webhook handler
│   │   ├── chat-engine.py      # Real-time chat engine
│   │   ├── thread-manager.py   # Conversation threads
│   │   └── message-router.py  # Message routing
│   ├── whatsapp-service/       # WhatsApp Integration
│   │   ├── whatsapp-webhook.py # Incoming messages
│   │   ├── message-sender.py   # Outgoing messages
│   │   ├── status-notifier.py  # Status updates
│   │   └── conversation-bridge.py # Channel sync
│   ├── curation-service/       # Module 20 (FastAPI on Container Apps)
│   │   ├── bundle-abstraction.py # Curated bundles
│   │   ├── ranking-engine.py   # Boost engine
│   │   ├── meta-manifest-processor.py # Pre-packaged experiences
│   │   └── visibility-controller.py # Admin toggles
│   ├── affiliate-service/     # Module 21 (FastAPI on Container Apps)
│   │   ├── affiliate-onboarding.py # Self-service registration
│   │   ├── link-wrapper.py    # Tracking ID injection
│   │   ├── kyc-verification.py # Business verification
│   │   └── commission-calculator.py # Commission logic
│   ├── curation-picker/        # Module 22 (Next.js on Vercel)
│   │   ├── visual-canvas.tsx   # Drag-and-drop builder
│   │   ├── product-picker.tsx  # Product search UI
│   │   └── margin-calculator.tsx # Real-time margin
│   ├── curation-picker-api/    # Module 22 API (FastAPI on Container Apps)
│   │   ├── canvas-manager.py   # Canvas state
│   │   ├── margin-optimizer.py # Margin calculation
│   │   └── bundle-validator.py # Feasibility validation
│   ├── standing-intent-service/ # Module 23 (Azure Durable Functions)
│   │   ├── orchestrator_function.py # Durable orchestrator
│   │   ├── intent_watcher_activity.py # Intent monitoring
│   │   ├── vendor_scout_activity.py # Vendor scouting
│   │   ├── status_narrator_activity.py # Progress updates
│   │   ├── atomic_checkout_activity.py # Purchase execution
│   │   ├── client_function.py # Entry point
│   │   └── external_event_handlers.py # HITL events
│   ├── omnichannel-broker-service/ # Module 24 (FastAPI on Container Apps)
│   │   ├── message-router.py # Multi-channel routing
│   │   ├── negotiation-state-machine.py # Negotiation states
│   │   ├── nlp-reprocessor.py # Counter-offer extraction
│   │   ├── suggestion-enricher.py # Enrich suggestions
│   │   ├── preference-manager.py # Communication preferences
│   │   ├── vision-analyzer.py # Photo analysis
│   │   └── webhook-handlers/ # Two-way webhooks
│   │       ├── twilio-whatsapp-webhook.py
│   │       ├── twilio-sms-webhook.py
│   │       └── partner-api-webhook.py
│   ├── hitl-escalation-service/ # Module 24 HITL (FastAPI on Container Apps)
│   │   ├── escalation-trigger.py # Escalation logic
│   │   ├── admin-dashboard-api.py # Admin dashboard
│   │   ├── silent-monitoring.py # Silent monitoring
│   │   └── intervention-queue.py # High-urgency queue
│   ├── negotiation-orchestrator/ # Module 24 (Azure Durable Functions)
│   │   ├── negotiation_orchestrator.py # Durable orchestrator
│   │   ├── wait_for_partner_reply.py # Wait-for-event
│   │   └── negotiation_timeout.py # Timeout handling
│   ├── payment-service/        # Module 15 (FastAPI on Container Apps)
│   ├── escrow-service/         # Module 16 (FastAPI on Container Apps)
│   └── auth-service/           # IAM (Clerk integration)
├── shared/
│   ├── types/                  # TypeScript types
│   ├── schemas/                # Zod/JSON schemas
│   ├── json-ld/                # JSON-LD schema definitions
│   │   ├── product-schema.py   # Product JSON-LD
│   │   ├── intent-schema.py    # Intent JSON-LD
│   │   ├── order-schema.py     # Order JSON-LD
│   │   └── payment-schema.py   # Payment JSON-LD
│   ├── adaptive-cards/         # Shared Adaptive Card templates
│   │   ├── product-card.json   # Product card template
│   │   ├── bundle-card.json    # Bundle card template
│   │   ├── proof-card.json     # Proof card template
│   │   └── checkout-card.json  # Checkout card template
│   └── utils/                  # Shared utilities
├── infrastructure/
│   ├── azure/                  # Azure ARM/Bicep templates
│   ├── docker/                 # Dockerfiles
│   └── scripts/                # Deployment scripts
├── docs/
│   ├── architecture/           # Architecture diagrams
│   ├── api/                    # API documentation
│   └── protocols/              # UCP/ACP integration docs
└── tests/
    ├── unit/                   # Unit tests
    ├── integration/            # Integration tests
    └── e2e/                    # End-to-end tests
```

## Cost Optimization Strategies

1. **Serverless First**: Azure Container Apps scales to zero (no idle costs)
2. **Database**: Supabase free tier (500MB database, 2GB bandwidth) for MVP
3. **Redis**: Upstash pay-per-request model (no idle costs)
4. **Frontend**: Vercel free tier (100GB bandwidth, unlimited requests for hobby projects)
5. **IAM**: Clerk free tier (10K MAU)
6. **API Management**: Use Consumption tier (pay per API call) or skip if using Vercel API routes
7. **Blob Storage**: Azure Blob Storage Cool tier for archived data, Hot tier for active
8. **Monitoring**: Application Insights free tier (5GB/month)

**Estimated Monthly Costs (MVP, 0-10K users):**

- Azure Container Apps: $0-30 (scales to zero, pay per vCPU-second)
- Supabase: $0 (free tier) or $25/month (Pro tier if needed)
- Upstash Redis: $0-10 (pay per request, typically <$5 for MVP)
- Vercel: $0 (hobby tier) or $20/month (Pro if needed)
- Clerk: $0 (free tier: 10K MAU)
- Azure Blob Storage: $5-15
- Azure Service Bus: $0-10 (first 13M operations free)
- Azure OpenAI: Pay-per-use (~$50-200/month depending on usage)
- Twilio WhatsApp: ~$5-50/month (1K-10K messages, varies by country)
- **Total: ~$10-145/month** (excluding OpenAI/Stripe usage, significantly lower than Azure-only stack)

**Cost Comparison:**

- **Original Azure Stack**: ~$60-240/month
- **Hybrid Stack (Gemini's recommendations)**: ~$5-95/month
- **Savings**: 60-85% cost reduction for MVP phase

## Key Design Decisions

1. **Chat-First / Headless Architecture**: API-first design with machine-readable responses (JSON-LD), Adaptive Cards for complex states, webhook push notifications, and zero-friction auth. All features accessible via REST API for AI agent consumption.
2. **Microservices Architecture**: Azure Container Apps (FastAPI) for independent scaling and better concurrency handling
3. **Event-Driven**: Service Bus for loose coupling between services, Upstash Redis for real-time bidding
4. **Unified Database**: Supabase PostgreSQL for all data (replaces Cosmos DB + SQL DB). JSONB for flexibility, PostGIS for geospatial, pgvector for semantic search
5. **Serverless-First**: Container Apps scales to zero, Upstash pay-per-request, Supabase free tier
6. **Python Backend**: FastAPI for better AI/ML integration and async performance
7. **TypeScript Frontend**: Next.js on Vercel for optimal AI streaming and edge delivery
8. **Real-time Where Needed**: Supabase Realtime for support hub, Upstash Redis for bidding
9. **Hybrid Cloud**: Best-of-breed services (not vendor lock-in to Azure)
10. **Design System First**: All React components built on design system from day one. Ensures consistency, maintainability, and enables white-label customization
11. **Multi-Tenant Storefronts**: Partners can launch custom storefronts with full branding control while maintaining platform quality and consistency
12. **Mobile-First Development**: React Native and PWA built alongside web features, not as separate tasks. Shared codebase ensures feature parity across platforms from day one
13. **Progressive Enhancement**: PWA features (offline support, push notifications, background sync) implemented with each feature, not retrofitted
14. **Cross-Platform Design System**: Design tokens and components work seamlessly across web, mobile, and PWA from the foundation

## Security Considerations

1. **Authentication**: Clerk for all users (customers, partners, admins) with built-in MFA and passkey support
2. **Authorization**: Capability-based RBAC stored in Clerk user metadata + Supabase PostgreSQL
3. **API Security**: Clerk middleware for API routes, Azure API Management optional
4. **Data Encryption**: At-rest (Supabase default) + in-transit (TLS everywhere)
5. **Secrets**: Azure Key Vault for all secrets (API keys, database credentials, Twilio tokens)
6. **Payment Security**: PCI compliance via Stripe (no card data stored)
7. **Agentic Handoff**: Clerk's SSO 2.0 support for seamless ChatGPT/Gemini integration
8. **WhatsApp Security**:

  - Twilio webhook signature verification
  - User opt-in/opt-out management (GDPR/CCPA compliance)
  - Message encryption in transit
  - Rate limiting for WhatsApp API calls
  - Template message approval process (Meta requirement)

## Testing Strategy

1. **Unit Tests**: Jest for all services, React Testing Library for components
2. **Integration Tests**: Test Azure Functions with local emulators
3. **E2E Tests**: Playwright for web, Detox for mobile
4. **Load Testing**: Azure Load Testing (free tier: 50 virtual users)
5. **Design System Tests**:

  - Visual regression testing (Chromatic or Percy)
  - Component snapshot tests
  - Theme switching tests
  - Accessibility tests (axe-core)

## Monitoring, Observability & Alerting

### Monitoring Stack

**Primary Tools**:
- **Azure Application Insights**: Application Performance Monitoring (APM), distributed tracing, custom metrics
- **Azure Monitor**: Infrastructure metrics (CPU, memory, disk, network)
- **Azure Log Analytics**: Centralized log aggregation and querying
- **Supabase Dashboard**: Database metrics (query performance, connection pool, slow queries)
- **Custom Dashboards**: Application Insights dashboards or Grafana (if needed)

**Integration Points**:
- All services send logs to Azure Log Analytics
- All services send metrics to Application Insights
- Database metrics from Supabase
- Custom business metrics via Application Insights custom events

### Metrics Catalog

#### Technical Metrics

**API Metrics** (per endpoint):
- Request rate (requests/second)
- Latency percentiles (p50, p95, p99)
- Error rate (errors/total requests)
- Throughput (successful requests/second)
- Response size (bytes)

**Service Metrics** (per service):
- CPU utilization (%)
- Memory utilization (%)
- Response time (average, p95, p99)
- Active connections
- Request queue length

**Database Metrics**:
- Query performance (average query time, slow queries > 5s)
- Connection pool usage (active/total connections)
- Transaction rate (transactions/second)
- Lock wait time
- Cache hit rate (if using query cache)

**Cache Metrics**:
- Hit rate (%)
- Miss rate (%)
- Eviction rate
- Cache size (items, memory)
- TTL effectiveness

**Queue Metrics**:
- Message count (pending, processing, completed)
- Processing rate (messages/second)
- DLQ size (dead letter queue messages)
- Processing latency (time in queue)

#### Business Metrics

**Order Metrics**:
- Order volume (orders/day, orders/hour)
- Order success rate (%)
- Order cancellation rate (%)
- Average order value
- Revenue (daily, weekly, monthly)

**Autonomous Recovery Metrics**:
- Recovery success rate (%)
- Alternative found rate (%)
- Average recovery time (seconds)
- Recovery attempts per order
- User approval rate (%)

**Partner Performance Metrics**:
- Partner response time (average, p95)
- Partner acceptance rate (%)
- Partner rejection rate (%)
- Partner availability rate (%)

**Time-Chain Metrics**:
- Time-Chain accuracy (actual vs predicted arrival time)
- Conflict detection rate (%)
- Average calculation time (seconds)
- Feasibility rate (%)

**Payment Metrics**:
- Payment success rate (%)
- Payment processing time (average, p95)
- Split payment success rate (%)
- Refund rate (%)

**User Satisfaction Metrics** (if tracked):
- User satisfaction score
- Support ticket volume
- Escalation rate (%)

#### Module-Specific Metrics

**Module 1 (Scout Engine)**:
- Scout query latency (p50, p95, p99)
- Cache hit rate (%)
- Manifest fetch failures (count, rate)
- Semantic search performance (query time)
- Products discovered per query (average)

**Module 4 (Intent Resolver)**:
- Intent resolution accuracy (%)
- LLM response time (average, p95)
- Intent parsing failures (count)
- Entity extraction accuracy (%)

**Module 5 (Time-Chain Resolver)**:
- Time-Chain calculation time (average, p95)
- Conflict detection rate (%)
- Route optimization time (seconds)
- PostGIS query performance

**Module 6 (Autonomous Recovery)**:
- Recovery success rate (%)
- Alternative found rate (%)
- Average recovery time (seconds)
- Recovery escalation rate (%)

**Module 12 (Support Hub)**:
- Message delivery time (average, p95)
- Chat thread activity (messages/day)
- Response time (time to first response)
- Real-time connection success rate (%)

**Module 15 (Payment)**:
- Payment processing time (average, p95)
- Split payment success rate (%)
- Payment authorization failures (count)
- Refund processing time

**Module 24 (Omnichannel Broker)**:
- Negotiation success rate (%)
- Escalation rate (%)
- Average response time (partner response time)
- Channel delivery success rate (by channel)

### Alerting Rules

#### Critical Alerts (P0 - Immediate Response)

**API Error Rate**:
- Condition: Error rate > 5% for 5 minutes
- Action: Page on-call engineer, create incident
- Example: "API error rate is 7.2% (threshold: 5%)"

**Payment Processing Failures**:
- Condition: Payment failures > 1% for 5 minutes
- Action: Page on-call engineer, notify payment team
- Example: "Payment failure rate is 2.1% (threshold: 1%)"

**Database Connection Failures**:
- Condition: Database connection failures detected
- Action: Page on-call engineer immediately
- Example: "Database connection pool exhausted"

**Service Unavailable**:
- Condition: 503 errors > 10 in 1 minute
- Action: Page on-call engineer, check service health
- Example: "Service returning 503 errors"

**Autonomous Recovery Failures**:
- Condition: Recovery failures > 10% for 10 minutes
- Action: Page on-call engineer, check Scout Engine
- Example: "Autonomous recovery failure rate is 15%"

#### High Priority Alerts (P1 - Response within 1 hour)

**API Latency**:
- Condition: API latency p95 > 2s for 10 minutes
- Action: Notify on-call engineer, investigate performance
- Example: "API latency p95 is 2.5s (threshold: 2s)"

**Database Query Performance**:
- Condition: Database query time > 5s
- Action: Notify on-call engineer, check slow queries
- Example: "Slow query detected: 8.2s execution time"

**Cache Hit Rate**:
- Condition: Cache hit rate < 70% for 30 minutes
- Action: Notify on-call engineer, check cache configuration
- Example: "Cache hit rate is 65% (threshold: 70%)"

**Dead Letter Queue**:
- Condition: DLQ message count > 100
- Action: Notify on-call engineer, investigate failed messages
- Example: "DLQ has 150 messages requiring attention"

**Partner API Failures**:
- Condition: Partner API failures > 20% for 15 minutes
- Action: Notify on-call engineer, check partner connectivity
- Example: "Partner API failure rate is 25%"

#### Medium Priority Alerts (P2 - Response within 4 hours)

**API Latency Degradation**:
- Condition: API latency p95 > 1s for 30 minutes
- Action: Create ticket for investigation
- Example: "API latency p95 is 1.2s (threshold: 1s)"

**Error Rate Increase**:
- Condition: Error rate > 1% for 30 minutes
- Action: Create ticket for investigation
- Example: "Error rate is 1.5% (threshold: 1%)"

**Resource Utilization**:
- Condition: Disk usage > 80% OR Memory usage > 85%
- Action: Create ticket for capacity planning
- Example: "Disk usage is 82% (threshold: 80%)"

#### Low Priority Alerts (P3 - Daily review)

**Cost Threshold**:
- Condition: Monthly cost > 80% of budget
- Action: Review cost optimization opportunities
- Example: "Monthly cost is $850 (budget: $1000)"

**Unusual Traffic Patterns**:
- Condition: Traffic spike > 200% of baseline
- Action: Review for potential issues or marketing events
- Example: "Traffic increased 250% from baseline"

**Performance Degradation Trends**:
- Condition: Gradual performance degradation over 7 days
- Action: Schedule performance optimization
- Example: "API latency increased 20% over 7 days"

### Dashboard Requirements

#### Operations Dashboard

**Real-Time Service Health**:
- Service status (healthy, degraded, down) for all services
- Current error rate per service
- Current latency per service
- Active incidents count

**Error Rate Trends**:
- Error rate over time (1h, 24h, 7d)
- Error rate by service
- Error rate by endpoint
- Error breakdown by error code

**Latency Trends**:
- Latency percentiles over time (p50, p95, p99)
- Latency by service
- Latency by endpoint
- Slowest endpoints

**Active Incidents**:
- Current incidents with severity
- Incident timeline
- Resolution status

**Recent Deployments**:
- Deployment history
- Deployment impact (error rate, latency changes)
- Rollback events

#### Business Dashboard

**Order Volume and Success Rate**:
- Orders per day/hour
- Order success rate (%)
- Revenue trends
- Average order value

**Revenue Metrics**:
- Daily/weekly/monthly revenue
- Revenue by partner
- Revenue trends

**Partner Performance**:
- Partner response times
- Partner acceptance rates
- Top performing partners
- Underperforming partners

**User Activity**:
- Active users (DAU, MAU)
- User engagement metrics
- Feature usage

#### Module-Specific Dashboards

**Scout Engine Dashboard**:
- Query performance (latency, throughput)
- Cache metrics (hit rate, miss rate)
- Manifest fetch success rate
- Products discovered metrics

**Autonomous Recovery Dashboard**:
- Recovery success rate
- Recovery time distribution
- Alternative found rate
- Escalation rate

**Payment Dashboard**:
- Transaction volume
- Payment success rate
- Processing time
- Refund rate

**Support Hub Dashboard**:
- Message volume
- Response times
- Channel distribution (web, WhatsApp)
- Thread activity

### Logging Standards

#### Log Levels

**ERROR**:
- System errors requiring immediate attention
- Exceptions and failures
- Critical business logic failures
- Security violations

**WARN**:
- Degraded performance
- Recoverable errors
- Retryable failures
- Deprecated API usage

**INFO**:
- Important business events
- Order created, payment processed
- User actions (login, registration)
- Service lifecycle events (startup, shutdown)

**DEBUG**:
- Detailed debugging information
- Development only (not in production)
- Step-by-step execution traces
- Variable values

#### Structured Logging Format

**Standard Log Entry**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "service": "scout-engine",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "error_code": "SCOUT_001",
  "message": "Failed to fetch manifest from partner",
  "category": "transient",
  "context": {
    "partner_id": "partner_456",
    "manifest_url": "https://partner.com/manifest.json",
    "retry_count": 2,
    "http_status": 503,
    "response_time_ms": 5000
  },
  "stack_trace": "Traceback (most recent call last):\n...",
  "correlation_id": "corr_789"
}
```

**Business Event Log Entry**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "payment-service",
  "event_type": "order_created",
  "order_id": "order_123",
  "user_id": "user_456",
  "amount": 299.99,
  "currency": "USD",
  "request_id": "req_789"
}
```

#### What to Log

**All API Requests**:
- `request_id`: Unique request identifier
- `endpoint`: API endpoint path
- `method`: HTTP method
- `user_id`: User making request
- `timestamp`: Request timestamp
- `duration`: Request processing time (ms)
- `status_code`: HTTP status code
- `response_size`: Response size (bytes)

**All Errors**:
- `error_code`: Standardized error code
- `category`: Error category (transient, permanent, user, system)
- `context`: Error context (partner_id, order_id, etc.)
- `stack_trace`: Full stack trace (for system errors)
- `request_id`: Associated request ID
- `retry_count`: Number of retry attempts

**Business Events**:
- `event_type`: Event type (order_created, payment_processed, recovery_triggered)
- `order_id`: Associated order (if applicable)
- `user_id`: User who triggered event
- `event_data`: Event-specific data (JSON)
- `timestamp`: Event timestamp

**Performance Metrics**:
- `query_time`: Database query execution time (ms)
- `api_latency`: API response time (ms)
- `cache_hit`: Cache hit/miss indicator
- `external_api_time`: External API call time (ms)

**Security Events**:
- `event_type`: Security event type (auth_failure, authorization_denial, suspicious_activity)
- `user_id`: User involved
- `ip_address`: Request IP address
- `user_agent`: User agent string
- `details`: Security event details

#### Error Correlation

**Request ID Propagation**:
- Generate unique `request_id` at API gateway
- Propagate `request_id` to all downstream services
- Include `request_id` in all logs for the request
- Use `request_id` to trace errors across services

**Correlation ID**:
- Use `correlation_id` for related operations (e.g., all operations for an order)
- Link all logs for a business transaction
- Enable end-to-end tracing

**User Context**:
- Include `user_id` in all user-initiated operations
- Enable user-specific error tracking
- Support user activity analysis

**Business Context**:
- Include `order_id` or `bundle_id` for business operations
- Enable business transaction tracing
- Support order lifecycle analysis

### Distributed Tracing

**Request ID Propagation**:
- Generate `request_id` at API gateway (UUID)
- Include `request_id` in HTTP headers (`X-Request-ID`)
- Propagate to all microservices
- Include in all logs and metrics

**Trace Correlation**:
- All logs for a request share the same `request_id`
- Query logs by `request_id` to see full request flow
- Identify bottlenecks and failures across services

**Service Dependency Mapping**:
- Track service calls (Service A → Service B)
- Map service dependencies
- Identify critical paths

**Performance Bottleneck Identification**:
- Measure time spent in each service
- Identify slow services
- Optimize high-latency operations

### Cost Monitoring

**Cost Alerts**:
- **50% Budget**: Warning alert (email notification)
- **80% Budget**: High priority alert (notify team)
- **100% Budget**: Critical alert (page on-call, stop non-essential services)

**Cost Breakdown by Service**:
- Azure Container Apps costs
- Supabase costs
- Azure OpenAI costs
- Twilio costs
- Other service costs

**Cost Trends and Forecasting**:
- Daily/weekly/monthly cost trends
- Cost per user
- Cost per order
- Forecasted costs based on growth

**Cost Optimization Recommendations**:
- Identify high-cost services
- Recommend optimization opportunities
- Track cost savings from optimizations

### Health Checks

**Health Check Endpoints**:
- `/health`: Basic health check (service is running)
- `/ready`: Readiness check (service is ready to accept traffic)
- `/live`: Liveness check (service is alive)

**Health Check Implementation**:
```python
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/ready")
async def readiness_check():
    # Check database connection
    db_healthy = await check_database_connection()
    # Check external dependencies
    deps_healthy = await check_dependencies()
    
    if db_healthy and deps_healthy:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Service not ready")
```

**Dependency Health Checks**:
- Database connection (Supabase)
- External APIs (partner APIs, Twilio)
- Cache (Upstash Redis)
- Message queue (Azure Service Bus)

**Health Check Aggregation**:
- Aggregate health from all services
- Overall system health status
- Health check dashboard
- Alert on service health degradation

### Incident Response Integration

**Alert Routing**:
- **P0 Alerts**: Page on-call engineer (PagerDuty, Opsgenie, or phone)
- **P1 Alerts**: Notify on-call engineer (email, Slack)
- **P2 Alerts**: Create ticket (Jira, Azure DevOps)
- **P3 Alerts**: Daily review (dashboard)

**On-Call Rotation Setup**:
- Define on-call schedule
- Escalation path (primary → secondary → manager)
- On-call handoff procedures

**Alert Grouping**:
- Group related alerts (e.g., all alerts for same service)
- Reduce alert noise
- Identify root cause faster

**Alert Acknowledgment and Resolution**:
- Track alert acknowledgment
- Track alert resolution time
- Post-incident review process
- Alert effectiveness metrics

## Deployment Strategy

1. **Development**: Azure DevTest Labs or local development
2. **Staging**: Separate Azure resource group
3. **Production**: Production resource group with monitoring
4. **CI/CD**: Azure DevOps pipelines or GitHub Actions
5. **Infrastructure as Code**: ARM templates or Bicep

## Technology Stack Comparison

| Layer | Original (Azure-Only) | Gemini's Recommendation | Why Better |
|-------|----------------------|------------------------|------------|
| **Orchestration** | Azure Functions | Azure Container Apps | Better concurrency, long-running connections, Python/FastAPI native |
| **Frontend** | Self-hosted Next.js | Vercel (Next.js) | AI streaming, edge delivery, agentic handoff support |
| **Database** | Cosmos DB + SQL DB | Supabase (PostgreSQL) | pgvector for semantic search, built-in Realtime, 60-85% cost savings |
| **Real-time Bidding** | Azure Service Bus | Upstash Redis | Sub-millisecond latency, pay-per-request, purpose-built for bidding |
| **IAM** | Azure AD B2C + AD | Clerk | Agentic handoff (SSO 2.0), better RBAC, zero infra management |
| **AI/LLM** | Azure OpenAI | Azure OpenAI | Kept - best enterprise option |

## Why Gemini's Recommendations Are Superior

### 1. Azure Container Apps vs Azure Functions

- **Better Concurrency**: Container Apps handles high-concurrency "Scout" bursts (Module 1) better than Functions
- **Long-Running Connections**: Supports WebSocket and long-running HTTP connections needed for real-time features
- **Python/FastAPI Native**: Better for AI/ML workloads and async operations
- **Cost**: Still scales to zero when idle (same cost model as Functions)

### 2. Vercel vs Self-Hosted Next.js

- **AI Streaming**: Superior edge delivery for streaming LLM responses (critical for Intent Resolver)
- **Agentic Handoff**: Essential for seamless handoff from ChatGPT/Gemini to custom UI
- **Global Edge Network**: Lower latency for international users
- **Developer Experience**: Zero-config deployments, built-in CI/CD

### 3. Supabase vs Cosmos DB

- **Cost**: Free tier (500MB database, 2GB bandwidth) vs Cosmos DB's $25/month minimum
- **pgvector**: Native PostgreSQL extension for semantic search (replaces expensive Azure Cognitive Search)
- **Realtime**: Built-in real-time subscriptions (replaces Azure SignalR for Module 12)
- **PostGIS**: Native geospatial support for Time-Chain Resolver (Module 5)
- **Easier Management**: Single PostgreSQL database vs managing Cosmos DB + SQL DB

### 4. Upstash Redis vs Azure Service Bus (for bidding)

- **Latency**: Sub-millisecond for real-time bidding (Module 10)
- **Cost Model**: Pay-per-request (no idle costs) vs Service Bus's base cost
- **Purpose-Built**: Redis is ideal for real-time bidding scenarios

### 5. Clerk vs Azure AD B2C

- **Agentic Handoff**: Best-in-class SSO 2.0 support (critical requirement)
- **Developer Experience**: Much simpler setup and integration
- **RBAC**: Native support for complex role hierarchies (partners, admins)
- **Passkeys**: Built-in FIDO2 support
- **Cost**: Free tier (10K MAU) vs Azure AD B2C's complexity

### 6. Azure OpenAI Service (Kept)

- **Enterprise-Grade**: Private, secure access to GPT-4o
- **Compliance**: Better for enterprise customers
- **Integration**: Seamless with Azure Container Apps
