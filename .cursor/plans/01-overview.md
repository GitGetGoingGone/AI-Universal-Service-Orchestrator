---
name: AI Universal Service Orchestrator Platform - Overview
overview: Executive Summary, Master Directive, Technology Stack
todos: []
---

# AI Universal Service Orchestrator - Implementation Plan

## Executive Summary

This plan outlines the architecture and implementation strategy for an AI Universal Service Orchestrator platform. The system orchestrates complex multi-vendor orders (e.g., "customized gift box + dinner reservation by 6 PM") by discovering products, coordinating logistics, managing payments, and facilitating communication across retailers, artisans, and gig workers.

## Master Directive: Chat-First / Headless Implementation

The platform is designed with a **Chat-First / Headless** architecture, prioritizing AI agent interactions (ChatGPT, Gemini) over traditional web interfaces. All features are accessible via standardized APIs with machine-readable responses.

### Core Principles

1. **API-First Development**:
 - All features (Scouting, Pricing, Curation) accessible via REST API
- Every API response includes machine-readable JSON-LD block for LLM consumption
- Standardized response format across all endpoints
- API versioning and backward compatibility

2. **Generative UI Support**:

- **Adaptive Cards (JSON)** for all complex states:
  - Virtual Proofing previews
  - Time-Chain visualizations
  - Progress Ledger displays
  - Bundle compositions
- **Dynamic View Triggers** for Gemini integration
- **Instant Checkout** support for ChatGPT
- Cards render natively in chat interfaces

3. **Asynchronous Webhooks**:

- **Push Notification Bridge**: Durable Functions send updates to specific Chat Thread ID
- Webhook endpoints for each chat platform (ChatGPT, Gemini, WhatsApp)
- Real-time status updates pushed to chat threads
- No polling required by chat agents

4. **Zero-Friction Auth**:

- **Link Account Flows**: One-tap binding of Google/OpenAI identity to USO account
- Delegated OAuth tokens for seamless handoff
- No login screens for chat-initiated sessions
- Agentic Consent Manager for token management

### Implementation Requirements

**All Modules Must**:

- Expose REST API endpoints
- Include JSON-LD in responses
- Support Adaptive Cards for complex states
- Support webhook callbacks for async updates
- Support Link Account flows for authentication

**MVP Priority Modules (3-6 months):**

- **AI Agents Integration** (Core) - Entry point for ChatGPT, Gemini
  - Orchestrator service: `POST /api/v1/chat` (Intent → Discovery)
  - Single endpoint: resolve natural language + discover products
  - JSON-LD + Adaptive Cards in responses **CRITICAL: Live Demo of AI Agents Integration**
- Module 1: Multi-Protocol Scout Engine (Core)
- Module 4: Intent Resolver (Core)
- Module 5: Time-Chain Resolver (Core) - **Includes Conflict Simulation**
- Module 6: Autonomous Re-Sourcing (Core) - 
- Module 7: Premium Registry & Capability Mapping (Core)
- Module 9: Generic Capability Portal (Core)
- Module 12: Multi-Party Support Hub (Core)
- Module 14: Status Narrator (Core) - **Includes Agent Reasoning**
- Module 15: Atomic Multi-Checkout (Core)
- Module 16: Transaction & Escrow Manager (Core)
- Module 24: Omnichannel Message Broker (Core) - **For partner communication**
- Module 25: The Partner Simulator (Core) - **CRITICAL: For Live Demo of Autonomous Recovery**
- Basic IAM (User/Partner login)

**MVP Critical Feature: Live Demo of AI Agents Integration and Autonomous Recovery**

- User requests change (e.g., "pink flowers" instead of "red")
- Partner rejects request
- AI automatically: cancels original order, finds alternative, updates bundle, recalculates timeline, updates user
- **No human intervention required**

**Phase 2 Modules (6-12 months):**

- Module 2: Legacy Adapter Layer
- Module 3: AI-First Discoverability
- Module 8: Virtual Proofing Engine
- Module 10: HubNegotiator & Bidding
- Module 11: Multi-Vendor Task Queue
- Module 13: Hybrid Response Logic
- Module 14: Status Narrator
- WhatsApp Integration (Status Updates & Conversations)
- Enhanced Real-time Chat Features (Module 12)
- **Storefront Customization & White-Label Platform** (Module 19)
- **Curation, Merchandising & Promotion Engine** (Module 20)
- **Affiliate Onboarding & Link Orchestration** (Module 21)
- **The Curation Picker** (Module 22)
- **Standing Intent Engine** (Module 23) - Durable, condition-based tasks
- **Omnichannel Message Broker & HITL Escalation** (Module 24) - Two-way negotiation across channels
- **The Partner Simulator** (Module 25) - **MVP Critical**: Testing and demo partner simulation for Live Demo of Autonomous Recovery
- Advanced IAM features

**Phase 3 Modules (12-18 months):**

- Module 17: Reverse Logistics & RMA
- Module 18: Operational Admin Command Center
- Module 20: Advanced Curation Features (A/B testing, personalization)
- Future enhancements

## Technology Stack (Optimized Hybrid Stack)

### Core Infrastructure

- **Orchestration/API**: **Azure Container Apps (ACA)** - Serverless Kubernetes. Ideal for Python/FastAPI services. Scales to zero (cost-effective) but handles high-concurrency "Scout" bursts better than standard Functions. Supports long-running connections and WebSocket connections needed for real-time features.
- **Long-Running Orchestration**: **Azure Durable Functions (Python v2)** - For Standing Intents (Module 23). Stateful orchestration that can checkpoint and sleep for days, waiting for external events. Cost-efficient: only pays for execution time, not waiting time.
- **Database**: **Supabase (PostgreSQL)** - Includes pgvector extension for semantic product discovery (replaces expensive Azure Cognitive Search). Built-in Realtime subscriptions perfect for Multi-Party Support Hub (Module 12). More cost-effective than Cosmos DB (free tier: 500MB database, 2GB bandwidth). Full PostgreSQL compatibility for complex queries.
- **Real-time Bidding/Cache**: **Upstash (Serverless Redis)** - Used for HubNegotiator (Module 10). Sub-millisecond latency with pay-per-request model (no idle costs). Perfect for real-time bidding scenarios where Azure Service Bus would be overkill.
- **Message Queue**: Azure Service Bus (for reliable async messaging between services) + Azure Event Grid (event-driven)
- **Storage**: Azure Blob Storage (files, images, virtual proofing assets) + Azure Table Storage (cheap key-value for metadata)
- **CDN**: Azure Front Door (global distribution) or Vercel Edge Network (if using Vercel)

### AI/ML Services

- **LLM Integration**: **Azure OpenAI Service** - Provides private, enterprise-grade access to GPT-4o for Intent Resolver (Module 4) and Status Narrator (Module 14). Direct API calls to Google Gemini for multi-model support.
- **Image Generation**: Azure OpenAI DALL-E 3 (for virtual proofing in Module 8)
- **Semantic Search**: **Supabase pgvector** - Native vector similarity search in PostgreSQL. More cost-effective and easier to manage than Azure Cognitive Search for product discovery.
- **NLP**: Azure Language Service (intent extraction, sentiment analysis)

### Authentication & Security

- **IAM**: **Clerk** - Best-in-class for Agentic Handoffs (SSO 2.0). Handles complex RBAC for Partners and Admins natively with zero infrastructure management. Built-in passkey support (FIDO2). Superior developer experience compared to Azure AD B2C for modern applications.
- **Secrets**: Azure Key Vault
- **Security**: Azure Application Gateway (WAF), Azure DDoS Protection

### Payment & Financial

- **Payment Processing**: Stripe Connect (multi-party payments)
- **Escrow**: Custom implementation using Supabase PostgreSQL (ACID compliance) + Service Bus workflows

### Communication & Messaging

- **WhatsApp Integration**: **Twilio WhatsApp Business API** or **Meta WhatsApp Business API** - For status updates and two-way conversations. Twilio recommended for better developer experience and global reach.
- **Real-time Chat**: Supabase Realtime (WebSocket-based) for in-app chat
- **Message Queue**: Azure Service Bus for reliable message delivery to WhatsApp

### Monitoring & DevOps

- **Monitoring**: Azure Application Insights (APM) + Azure Monitor
- **Logging**: Azure Log Analytics
- **CI/CD**: Azure DevOps (free tier for small teams) or GitHub Actions
- **Container Registry**: Azure Container Registry

### Frontend

- **Web Framework**: **Next.js 14 on Vercel** - Superior for AI Streaming and Edge delivery. Essential for "Agentic Handoff" from ChatGPT/Gemini. Vercel's edge network provides low-latency global distribution. Built-in support for streaming responses from LLMs.
- **Mobile**: React Native (shared codebase) or Progressive Web App (PWA)
- **Design System**: **Custom Design System** built on top of shadcn/ui + Tailwind CSS
  - Design tokens (colors, typography, spacing, shadows)
  - Component library with consistent API
  - Theme customization engine
  - Multi-tenant theming support
  - White-label capabilities
- **UI Library Base**: shadcn/ui + Tailwind CSS (foundation)
- **State Management**: Zustand or React Query
- **Real-time**: Supabase Realtime (replaces Azure SignalR for Module 12)
- **Theming**: CSS Variables + Tailwind CSS custom properties for runtime theme switching
