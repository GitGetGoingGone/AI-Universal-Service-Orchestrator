# Agentic Consent Flow

Agentic AI agency boundaries and consent flow for the orchestrator. Per Pillar 2 and Month 0 Integration Hub.

## Overview

The agent can take actions on behalf of the user within defined boundaries. User consent is implicit for discovery and browsing; explicit confirmation is required for checkout and add-to-bundle.

## Allowed Actions (No Explicit Confirmation)

| Action | Description |
|--------|-------------|
| `resolve_intent` | Parse user message to structured intent |
| `discover_products` | Search and browse products |
| `start_orchestration` | Start long-running workflow |
| `create_standing_intent` | Create standing intent (approval requested via card) |

## Requires Confirmation

| Action | Description |
|--------|-------------|
| `checkout` | Proceed to payment |
| `add_to_bundle` | Add product to bundle |

## Standing Intent Handoff

When the agent detects a condition-based or delayed intent (e.g. "notify me when", "remind me to"), it calls `create_standing_intent`:

1. Creates standing intent via `POST /api/v1/standing-intents`
2. Durable Orchestrator starts `standing_intent_orchestrator`
3. Approval card is pushed to chat (platform + thread_id)
4. User clicks Approve/Reject
5. `POST /api/v1/standing-intents/{id}/approve` raises `UserApproval` event
6. Orchestrator resumes and completes

## API

- `GET /api/v1/agentic-consent` – Returns scope, allowed_actions, requires_confirmation
- `GET /api/v1/agentic-handoff` – Returns Clerk config when configured (SSO 2.0)
