# Development Environment Setup

This guide gets you from clone to running the discovery service in under 30 minutes.

## Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Backend services (FastAPI) |
| **Node.js** | 20+ LTS | Next.js, React Native, design system |
| **pnpm** or npm | Latest | Package management for Node apps |
| **Docker Desktop** | Latest | Supabase local dev (optional) |
| **Git** | 2.x | Version control |
| **Supabase CLI** | Latest | Database migrations |
| **Azure CLI** | Optional | Azure resource management |

### Install Commands (macOS)

```bash
# Python (via Homebrew)
brew install python@3.11

# Node.js (via nvm recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# pnpm
npm install -g pnpm

# Supabase CLI
brew install supabase/tap/supabase

# Docker Desktop - download from docker.com
```

## Python Setup

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: Install dev tools
pip install black ruff pytest pytest-asyncio
```

## Node.js Setup

Used when building Next.js apps, React Native, and design system packages:

```bash
# From repo root (when apps exist)
pnpm install
```

## IDE Configuration (VS Code / Cursor)

### Recommended Extensions

- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Ruff** (charliermarsh.ruff)
- **Black Formatter** (ms-python.black-formatter)
- **ESLint** (dbaeumer.vscode-eslint)
- **Prettier** (esbenp.prettier-vscode)
- **Tailwind CSS** (bradlc.vscode-tailwindcss)

### Settings Snippet

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "ruff.lint.args": ["--config", "pyproject.toml"]
}
```

## Local Database Options

### Option A: Supabase Cloud (Recommended—No Docker Required)

1. Create a project at [supabase.com](https://supabase.com)
2. Get `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_SECRET_KEY` from Project Settings → API
3. Copy `.env.example` to `.env` and fill in values
4. Link and push migrations:

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

### Option B: Supabase Local (Requires Docker Desktop)

**Prerequisite**: [Docker Desktop](https://docs.docker.com/desktop/) must be installed and running.

```bash
# Start local Supabase (Docker must be running)
supabase start

# Apply migrations
supabase db reset

# Stop when done
supabase stop
```

If you see `Cannot connect to the Docker daemon`, start Docker Desktop first. Local URLs are printed by `supabase start` (typically `http://127.0.0.1:54321`).

## Azure Emulators

For local development without cloud costs:

- **Azure Storage Emulator**: Use Azurite (`npm install -g azurite`) for blob/queue storage
- **Service Bus**: No official local emulator; use a dev Azure namespace or mock in tests

For MVP, you can defer Azure setup and use env vars pointing to dev resources.

## Quick Start Commands

```bash
# 1. Clone
git clone <repo-url>
cd "AI Universal Service Orchestrator"

# 2. Python environment
python3.11 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
# Edit .env with your Supabase credentials

# 4. Database (Supabase Cloud)
# Apply migrations via Supabase Dashboard SQL Editor, or:
supabase link --project-ref <your-project-ref>
supabase db push

# 5. Run discovery service
cd services/discovery-service
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 6. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Cannot connect to the Docker daemon` | Start Docker Desktop, or use Supabase Cloud instead (`supabase db push`) |
| `ModuleNotFoundError: packages.shared` | Run from repo root or ensure `PYTHONPATH` includes repo root |
| Supabase connection refused | Check `SUPABASE_URL` and firewall; ensure project is not paused |
| pgvector not found | Enable in Supabase: SQL Editor → `CREATE EXTENSION IF NOT EXISTS vector;` |
| Port 8000 in use | Use `--port 8001` or another port |

## What You Can Skip Initially

- **Clerk webhook** (`CLERK_WEBHOOK_SECRET`): Only needed when you have sign-up flows (Next.js, Partner Portal). Use lazy user sync until then.
- **Twilio, Stripe, Azure OpenAI**: Add when implementing those modules.

## Next Steps

- [Database Setup](./DATABASE_SETUP.md) - Migration details, seed data
- [Environment Variables](./ENVIRONMENT_VARIABLES.md) - All required vars
- [Authentication Setup](./AUTHENTICATION_SETUP.md) - Clerk integration
