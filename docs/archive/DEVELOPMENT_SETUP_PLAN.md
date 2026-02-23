# Pre-Implementation Development Setup Plan

**Goal**: Unblock development by adding critical setup documentation and configuration. Team can begin coding immediately after Critical items are complete.

**Implementation Order**: Critical → High Priority → Medium Priority

---

## Phase 1: Critical (Block Development Start)

### 1.1 Development Environment Setup

**Location**: `docs/DEVELOPMENT_ENVIRONMENT.md`

**Content**:

| Section | Details |
|---------|---------|
| **Required Tools** | Python 3.11+, Node.js 20+, pnpm/npm, Docker Desktop, Git, Azure CLI (optional), Supabase CLI |
| **Python Setup** | pyenv or system Python, virtualenv/venv, `pip install -r requirements.txt` |
| **Node.js Setup** | For Next.js apps, React Native, design system packages |
| **IDE Configuration** | VS Code/Cursor: recommended extensions (Python, Pylance, ESLint, Prettier, Tailwind), settings.json snippets |
| **Local Database** | Supabase local dev (Docker) OR cloud project connection |
| **Azure Emulators** | Azure Storage Emulator, Service Bus Emulator (if available) - or use cloud dev resources |
| **Quick Start Commands** | Clone → Install → Migrate → Run discovery-service |

**Deliverables**:
- `docs/DEVELOPMENT_ENVIRONMENT.md` - Full setup guide
- `docs/IDE_SETUP.md` - IDE-specific config (optional, can merge into above)

---

### 1.2 Database Setup & Migration Process

**Location**: `docs/DATABASE_SETUP.md` + enhance existing `supabase/`

**Content**:

| Section | Details |
|---------|---------|
| **Supabase Project Setup** | Create project at supabase.com, get connection string, enable pgvector + PostGIS |
| **Local Connection** | `SUPABASE_URL`, `SUPABASE_SECRET_KEY` for migrations |
| **Migration Tool** | Supabase CLI: `supabase init`, `supabase db push`, `supabase migration list` |
| **Migration Commands** | `supabase db push` (apply), `supabase db reset` (reset + reapply) |
| **Seed Data Scripts** | `supabase/seed.sql` - test users, capability_tags, sample partner, sample product |
| **Reset Procedures** | When to reset, how to reset, backup considerations |
| **Connection Pooling** | Supabase connection pooler settings for serverless |

**Deliverables**:
- `docs/DATABASE_SETUP.md` - Full database setup guide
- `supabase/config.toml` - Supabase project config (if using local)
- `supabase/seed.sql` - Minimal seed data for local dev

---

### 1.3 Environment Variables & Secrets Management

**Location**: `.env.example` + `docs/ENVIRONMENT_VARIABLES.md`

**Content**:

| Section | Details |
|---------|---------|
| **Required Variables** | List all: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `CLERK_SECRET_KEY`, `AZURE_*`, `TWILIO_*`, etc. |
| **.env.example** | Template with placeholder values, no secrets |
| **Local vs Production** | What differs (URLs, keys, feature flags) |
| **Azure Key Vault** | When to use, local dev alternative (env vars), production setup |
| **Secrets in CI** | How GitHub Actions / Azure DevOps get secrets |

**Deliverables**:
- `.env.example` - Template with all required variables
- `docs/ENVIRONMENT_VARIABLES.md` - Documentation for each variable

---

### 1.4 Authentication Setup (Clerk Integration)

**Location**: `docs/AUTHENTICATION_SETUP.md`

**Content**:

| Section | Details |
|---------|---------|
| **Clerk Project Setup** | Create Clerk application, get API keys |
| **Local Development Auth** | Clerk dev instance, localhost redirect URLs |
| **Test Users** | How to create test users in Clerk dashboard |
| **Role/Permission Setup** | RBAC: customer, partner, hub, admin, gig_worker |
| **Link Account Flows** | Zero-friction auth for chat agents (reference to plan) |
| **Clerk Webhook** | User sync to `users` table (if applicable) |

**Deliverables**:
- `docs/AUTHENTICATION_SETUP.md` - Full Clerk setup guide

---

## Phase 2: High Priority (Needed Early)

### 2.1 Code Standards & Conventions

**Location**: `docs/CODE_STANDARDS.md` + config files

**Content**:

| Section | Details |
|---------|---------|
| **Python** | PEP 8, Black (line length 100), Ruff (lint + format), type hints |
| **TypeScript/JavaScript** | ESLint, Prettier, consistent config |
| **Naming** | snake_case (Python, DB), camelCase (TS/JS), PascalCase (components) |
| **Docstrings** | Google or NumPy style for Python |
| **Code Review** | Checklist: tests, lint, no secrets, error handling |

**Deliverables**:
- `docs/CODE_STANDARDS.md` - Written standards
- `pyproject.toml` - Black, Ruff config
- `.eslintrc.cjs` / `eslint.config.js` - ESLint config (when TS apps exist)
- `.prettierrc` - Prettier config

---

### 2.2 Git Workflow & Branching Strategy

**Location**: `docs/GIT_WORKFLOW.md` + `.github/` templates

**Content**:

| Section | Details |
|---------|---------|
| **Branch Naming** | `feature/MODULE-123-short-description`, `fix/`, `chore/` |
| **PR Process** | Create PR → Review → Approve → Merge |
| **PR Template** | `.github/PULL_REQUEST_TEMPLATE.md` |
| **Commit Messages** | Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:` |
| **Merge Strategy** | Squash for feature branches, merge commit for release |

**Deliverables**:
- `docs/GIT_WORKFLOW.md` - Full workflow doc
- `.github/PULL_REQUEST_TEMPLATE.md` - PR template
- `.github/COMMIT_CONVENTION.md` - Commit message guide (optional, can be in GIT_WORKFLOW)

---

### 2.3 API Contracts/Specifications

**Location**: `docs/api/` or `openapi/` + per-service specs

**Content**:

| Section | Details |
|---------|---------|
| **OpenAPI/Swagger** | MVP modules: Scout (Module 1), Intent (4), Time-Chain (5), Recovery (6), Payment (15), Support (12) |
| **Request/Response Examples** | At least one per endpoint |
| **Authentication** | Bearer token, Clerk JWT validation |
| **Rate Limiting** | Per-endpoint limits (e.g., Scout: 100/min, Payment: 20/min) |
| **Error Responses** | Reference to 02-architecture.md error format |

**Deliverables**:
- `openapi/discovery-service.yaml` - Module 1 API spec
- `openapi/README.md` - How to generate clients, view specs
- Add OpenAPI to FastAPI apps: `app.openapi()` or redoc/swagger UI

---

## Phase 3: Medium Priority (Can Add During Development)

### 3.1 CI/CD Pipeline Setup

**Location**: `.github/workflows/` or `azure-pipelines.yml`

**Content**:

| Section | Details |
|---------|---------|
| **Build** | Python: lint (Ruff), test (pytest); Node: build, lint |
| **Test** | Unit tests, integration tests (if DB available) |
| **Deploy Staging** | On merge to `main` or `develop` |
| **Environment Promotion** | Staging → Production approval process |

**Deliverables**:
- `.github/workflows/ci.yml` - Lint, test on PR
- `.github/workflows/deploy-staging.yml` - Deploy to staging (placeholder)

---

### 3.2 Testing Setup

**Location**: `docs/TESTING.md` + test config

**Content**:

| Section | Details |
|---------|---------|
| **Test Environment** | pytest for Python, Jest/Vitest for TS |
| **Test Data** | Fixtures, factories, seed data |
| **Mocks** | Mock Supabase, Clerk, external APIs |
| **Running Tests** | `pytest`, `pnpm test` |
| **Coverage** | Target 80% for critical paths |

**Deliverables**:
- `docs/TESTING.md` - Testing guide
- `pytest.ini` or `pyproject.toml` [tool.pytest]
- Example test: `services/discovery-service/tests/test_health.py`

---

### 3.3 Developer Onboarding Guide

**Location**: `docs/ONBOARDING.md` or `README.md` section

**Content**:

| Section | Details |
|---------|---------|
| **Getting Started Checklist** | 1. Clone 2. Read DEV_ENV 3. Install tools 4. Run migrations 5. Start service |
| **Common Tasks** | Add endpoint, add migration, run tests |
| **Troubleshooting** | Common errors, DB connection, Clerk redirect |
| **Team Channels** | Slack/Discord, where to ask questions |

**Deliverables**:
- `docs/ONBOARDING.md` - Full onboarding guide
- Update `README.md` with "Getting Started" linking to docs

---

## Implementation Checklist

### Critical (Do First)

- [x] Create `docs/DEVELOPMENT_ENVIRONMENT.md`
- [x] Create `docs/DATABASE_SETUP.md`
- [x] Create `supabase/seed.sql`
- [x] Create `.env.example`
- [x] Create `docs/ENVIRONMENT_VARIABLES.md`
- [x] Create `docs/AUTHENTICATION_SETUP.md`

### High Priority

- [ ] Create `docs/CODE_STANDARDS.md`
- [ ] Add `pyproject.toml` (Black, Ruff)
- [ ] Create `docs/GIT_WORKFLOW.md`
- [ ] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Create `openapi/discovery-service.yaml` (Module 1)

### Medium Priority

- [ ] Create `.github/workflows/ci.yml`
- [ ] Create `docs/TESTING.md`
- [ ] Add example test
- [ ] Create `docs/ONBOARDING.md`
- [ ] Update README with Getting Started

---

## File Structure After Implementation

```
/
├── .env.example
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml
│       └── deploy-staging.yml
├── docs/
│   ├── DEVELOPMENT_ENVIRONMENT.md
│   ├── DATABASE_SETUP.md
│   ├── ENVIRONMENT_VARIABLES.md
│   ├── AUTHENTICATION_SETUP.md
│   ├── CODE_STANDARDS.md
│   ├── GIT_WORKFLOW.md
│   ├── TESTING.md
│   ├── ONBOARDING.md
│   └── DEVELOPMENT_SETUP_PLAN.md (this file)
├── openapi/
│   ├── README.md
│   └── discovery-service.yaml
├── pyproject.toml
├── supabase/
│   ├── config.toml (optional)
│   └── seed.sql
└── ...
```

---

## Success Criteria

- **Critical**: A new developer can clone the repo, follow docs, and run the discovery service with a local DB in under 30 minutes.
- **High**: Code reviews are consistent; API contracts are documented.
- **Medium**: CI runs on every PR; onboarding doc answers "how do I...?" questions.
