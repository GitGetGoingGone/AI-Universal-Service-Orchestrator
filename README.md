# AI Universal Service Orchestrator

Platform for orchestrating complex multi-vendor orders via AI agents (ChatGPT, Gemini). Chat-First / Headless architecture.

## Critical Items (Implemented)

### 1. Error Handling (`packages/shared/errors/`)

- **Standardized error response** per `02-architecture.md`
- **Custom exceptions**: `USOException`, `ValidationError`, `NotFoundError`, etc.
- **FastAPI middleware**: Request ID propagation, exception handlers
- **Error codes**: `{MODULE}_{NUMBER}` format (e.g., `SCOUT_001`)

### 2. Database Schema (`supabase/migrations/`)

- **6 migration files** covering all MVP modules
- **Extensions**: pgvector, PostGIS
- **Tables**: users, partners, products, intents, bundles, orders, payments, escrow, time-chains, autonomous recoveries, support hub, status narrator, omnichannel, partner simulator, supporting tables
- **Naming**: `YYYYMMDD_HHMMSS_description.sql`

### 3. Monitoring (`packages/shared/monitoring/`)

- **Health checks**: `/health` (liveness), `/ready` (readiness with dependency checks)
- **Structured logging**: JSON format with request_id, context
- **Dependency checks**: Pluggable for database, cache, etc.

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd "AI Universal Service Orchestrator"
cp .env.example .env   # Edit with your Supabase credentials

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Database: Apply migrations via Supabase Dashboard or `supabase db push`
#    Run supabase/seed.sql for sample products

# 4. Run discovery service (Module 1)
cd services/discovery-service && uvicorn main:app --reload

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl "http://localhost:8000/api/v1/discover?intent=flowers"
```

**Full setup**: See [Development Environment](docs/DEVELOPMENT_ENVIRONMENT.md)

## Project Structure

```
├── packages/shared/          # Shared utilities
│   ├── errors/               # Error handling
│   ├── monitoring/           # Health, logging
│   └── retry.py              # Retry policies
├── services/
│   └── discovery-service/    # Module 1: Scout Engine
├── supabase/migrations/      # Database schema
└── requirements.txt
```

## Documentation

- [Development Environment](docs/DEVELOPMENT_ENVIRONMENT.md) - Tools, IDE, quick start
- [Database Setup](docs/DATABASE_SETUP.md) - Migrations, seed data
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) - All required vars
- [Authentication Setup](docs/AUTHENTICATION_SETUP.md) - Clerk integration
- [API Contracts](docs/API_CONTRACTS.md) - OpenAPI specs, discovery service contract
- [Server Testing](docs/SERVER_TESTING.md) - Server-based tests against deployed services
- [Staging Setup](docs/STAGING_SETUP.md) - Deploy staging environment for CI and QA
- [Git and Azure CLI](docs/GIT_AZURE_CLI_SETUP.md) - Connect Git with Azure via CLI

## Plan Reference

- Architecture: `.cursor/plans/02-architecture.md`
- Modules: `.cursor/plans/03-modules-all.md`
- Operations: `.cursor/plans/07-project-operations.md`
