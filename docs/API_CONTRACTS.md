# API Contracts

This document describes the API contract strategy for the AI Universal Service Orchestrator platform.

## Overview

- **OpenAPI 3.1** specs define the contract for each service.
- Specs live in `docs/api/` and are the source of truth for consumers and generators.
- FastAPI auto-generates OpenAPI from code; we maintain hand-authored specs for documentation and contract-first workflows.

## Discovery Service (Module 1)

| Spec | Path | Description |
|------|------|-------------|
| Discovery Service | `docs/api/discovery-service.openapi.yaml` | Module 1: Product discovery, health probes |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/discover` | Discover products by intent (Chat-First: JSON-LD + Adaptive Card) |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/` | Service info |

## Orchestrator Service

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Chat-First: resolve intent + discover products (when discover) |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (checks Intent + Discovery) |
| GET | `/` | Service info |

## Intent Service (Module 4)

| Spec | Path | Description |
|------|------|-------------|
| Intent Service | `docs/api/intent-service.openapi.yaml` | Module 4: Natural language to structured intent |

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/resolve` | Resolve intent from user message (Azure OpenAI or fallback) |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/` | Service info |

### Example Request

```bash
curl "http://localhost:8000/api/v1/discover?intent=flowers&limit=10"
```

### Example Response (200)

```json
{
  "data": {
    "products": [
      {
        "id": "uuid",
        "name": "Bouquet",
        "description": "...",
        "price": 29.99,
        "currency": "USD",
        "capabilities": ["delivery", "same-day"]
      }
    ],
    "count": 1
  },
  "machine_readable": {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "numberOfItems": 1,
    "itemListElement": [...]
  },
  "adaptive_card": {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [...]
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "2024-01-28T12:00:00Z",
    "request_id": "uuid"
  }
}
```

## Using the Specs

### View in Swagger UI

FastAPI serves auto-generated OpenAPI at `/docs`. For the hand-authored spec:

```bash
# Using openapi-generator or redoc-cli
npx @redocly/cli preview-docs docs/api/discovery-service.openapi.yaml
```

### Generate Clients

```bash
# OpenAPI Generator (example for TypeScript)
npx @openapitools/openapi-generator-cli generate \
  -i docs/api/discovery-service.openapi.yaml \
  -g typescript-fetch \
  -o clients/discovery-ts
```

### Validate Implementation

Ensure FastAPI routes match the spec. Run integration tests that assert against the OpenAPI schema.

## Error Responses

All error responses follow the shared `ErrorResponse` schema (see `packages/shared/errors/models.py`):

- `error.code`: Module-prefixed code (e.g. `MODULE_01`)
- `error.category`: `transient` | `permanent` | `user` | `system`
- `machine_readable`: JSON-LD block for AI agent consumption

## Versioning

- API version in path: `/api/v1/`
- Breaking changes require a new major version (e.g. `v2`).
- Non-breaking additions (new optional params, new fields) are allowed within the same version.

## Adding New Services

1. Create `docs/api/<service-name>.openapi.yaml`.
2. Define paths, components, and tags.
3. Add a row to the table in this document.
4. Wire FastAPI routes to match the spec.
