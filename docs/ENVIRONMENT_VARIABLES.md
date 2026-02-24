# Environment Variables & Secrets Management

Reference for all environment variables used across the AI Universal Service Orchestrator.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values
```

## Required Variables by Component

### Database (Supabase)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Project URL (e.g., `https://xxxxx.supabase.co`) |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Publishable key for client-side (RLS). Format: `sb_publishable_...` |
| `SUPABASE_SECRET_KEY` | Yes | Secret key for server-side (bypasses RLS). Format: `sb_secret_...` |
| `SUPABASE_DB_URL` | Optional | Direct Postgres URL for connection pooling |

**Where to get**: Supabase Dashboard → Project Settings → API

**Migration from legacy keys**: If you have `SUPABASE_ANON_KEY` or `SUPABASE_SERVICE_KEY` (JWT format), rename to `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY` and use the new keys from Project Settings → API. Legacy keys are deprecated; migrate before November 2025.

### Authentication (Clerk)

| Variable | Required | Description |
|----------|----------|-------------|
| `CLERK_PUBLISHABLE_KEY` | Yes | Public key for frontend (pk_test_ or pk_live_) |
| `CLERK_SECRET_KEY` | Yes | Secret key for backend (sk_test_ or sk_live_) |
| `CLERK_WEBHOOK_SECRET` | Optional | For webhook signature verification |

**Where to get**: Clerk Dashboard → API Keys

### AI / LLM (Platform Config)

LLM providers (Azure, Gemini, OpenRouter, Custom) are configured via Platform Config UI at `/platform/config`. Add providers and set one as active.

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_CONFIG_ENCRYPTION_KEY` | For LLM | Encrypt API keys in llm_providers; 32+ chars. Required in production. |

### Messaging (Twilio)

| Variable | Required | Description |
|----------|----------|-------------|
| `TWILIO_ACCOUNT_SID` | For Module 24 | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | For Module 24 | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | For Module 24 | WhatsApp-enabled phone number |

**Where to get**: Twilio Console → Account Info

### Cache (Upstash Redis)

| Variable | Required | Description |
|----------|----------|-------------|
| `UPSTASH_REDIS_REST_URL` | For bidding/cache | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | For bidding/cache | Upstash Redis REST token |

**Where to get**: Upstash Console → Redis database

### Payments (Stripe)

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_SECRET_KEY` | For Module 15 | Stripe secret key (sk_test_ or sk_live_) |
| `STRIPE_PUBLISHABLE_KEY` | For Module 15 | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | For webhooks | Webhook signing secret |

**Where to get**: Stripe Dashboard → Developers → API keys

### Application

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | No | `development`, `staging`, `production` (default: development) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: INFO) |
| `API_BASE_URL` | No | Base URL for API (e.g., `http://localhost:8000`) |
| `DISCOVERY_SERVICE_URL` | For server tests, orchestrator | Discovery service URL (default: `http://localhost:8000`) |
| `INTENT_SERVICE_URL` | For orchestrator | Intent service URL (default: `http://localhost:8001`) |

### Discovery service (embeddings)

Used by the **Discovery service** for semantic product search (pgvector). If not set, semantic search is skipped and only text/capability search is used.

| Variable | Required | Description |
|----------|----------|-------------|
| `EMBEDDING_PROVIDER` | For semantic | `openai` or `azure` (default: `azure`) |
| `EMBEDDING_MODEL` | For semantic | Model name, e.g. `text-embedding-3-small` |
| `OPENAI_API_KEY` | For semantic (OpenAI) | OpenAI API key when `EMBEDDING_PROVIDER=openai` |
| `AZURE_OPENAI_ENDPOINT` | For semantic (Azure) | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | For semantic (Azure) | Azure OpenAI API key |

After setting these, run the [embedding backfill](MODULE1_SCOUT_ENGINE.md#how-to-enable-semantic-search-fix-no-results-from-semantic) so products get vectors and semantic search returns results.

## Local vs Production

| Aspect | Local | Production |
|--------|-------|------------|
| **Supabase** | Cloud dev project or `supabase start` | Dedicated project, connection pooler |
| **Clerk** | Development instance (pk_test_, sk_test_) | Production instance (pk_live_, sk_live_) |
| **Stripe** | Test mode (sk_test_) | Live mode (sk_live_) |
| **Twilio** | Trial account or dev number | Production number |
| **Secrets** | `.env` file | Azure Key Vault or CI secrets |

## Secrets Management

### Local Development

- Use `.env` file (add to `.gitignore`)
- Never commit `.env` to git
- `.env.example` documents required variables without values

### Production (Azure Key Vault)

For production, store secrets in Azure Key Vault:

1. Create Key Vault in Azure
2. Add secrets for each variable
3. Grant app identity access via Managed Identity
4. Load at runtime: `DefaultAzureCredential` + Key Vault client

```python
# Example: Load from Key Vault in production
if os.getenv("ENVIRONMENT") == "production":
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=os.getenv("AZURE_KEY_VAULT_URL"), credential=credential)
    SUPABASE_SECRET_KEY = client.get_secret("SUPABASE-SECRET-KEY").value
else:
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
```

### CI/CD (GitHub Actions)

Store secrets in GitHub repository settings:

- Settings → Secrets and variables → Actions
- Add: `SUPABASE_SECRET_KEY`, `CLERK_SECRET_KEY`, `DISCOVERY_SERVICE_URL` (for server tests), etc.
- Reference in workflow: `${{ secrets.SUPABASE_SECRET_KEY }}`

### CI/CD (Azure DevOps)

- Pipeline → Library → Variable groups
- Link to Azure Key Vault or define variables
- Mark sensitive variables as secret

## MVP Minimum

To run the discovery service and basic development:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`

All other variables can be added as you implement their modules.
