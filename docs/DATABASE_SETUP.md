# Database Setup & Migration Process

Supabase PostgreSQL with pgvector and PostGIS for the AI Universal Service Orchestrator.

## Supabase Project Setup

### 1. Create Project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose organization, name (e.g., `uso-dev`), password, region
3. Wait for project to be provisioned

### 2. Get Connection Details

**Project Settings → API**:

- **Project URL**: `SUPABASE_URL` (e.g., `https://xxxxx.supabase.co`)
- **Secret key** (sb_secret_...): `SUPABASE_SECRET_KEY` (for migrations, server-side)
- **Publishable key** (sb_publishable_...): `SUPABASE_PUBLISHABLE_KEY` (for client-side, RLS)

*Note: Legacy anon/service_role keys (JWT format) are deprecated; use the new keys.*

### 3. Enable Extensions

Extensions are enabled in the first migration (`00_extensions.sql`). If applying manually:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

## Local Connection

### Environment Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

For local Supabase (`supabase start`):

```env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SECRET_KEY=<from supabase start output>
SUPABASE_PUBLISHABLE_KEY=<from supabase start output>
```

## Migration Tool (Supabase CLI)

### Install

```bash
brew install supabase/tap/supabase  # macOS
```

### Link to Project (Cloud)

```bash
supabase login
supabase link --project-ref <your-project-ref>
```

Project ref is in the URL: `https://app.supabase.com/project/<project-ref>`. supabase link --project-ref cnpftqkqqabuxctlsjpp

### Migration Commands

| Command | Description |
|---------|-------------|
| `supabase db push` | Apply all pending migrations |
| `supabase db reset` | Reset DB and reapply all migrations (local only) |
| `supabase migration list` | List migrations and status |
| `supabase db diff` | Generate migration from schema changes |

### Migration Files

Located in `supabase/migrations/`. Use format `YYYYMMDDHHmmss_description.sql` (each timestamp must be unique):

- `20240128000000_extensions.sql` - pgvector, PostGIS
- `20240128000001_core_and_scout.sql` - users, partners, products
- `20240128000002_intent_and_bundle.sql` - intents, bundles
- `20240128000003_orders_and_payments.sql` - orders, payments, escrow
- `20240128000004_timechain_recovery_support.sql` - time-chains, support, status
- `20240128000005_omnichannel_simulator_supporting.sql` - negotiations, simulator, webhooks

### Applying Migrations (Cloud)

**Option 1: Supabase Dashboard**

1. SQL Editor → New Query
2. Copy contents of each migration file in order
3. Run each migration

**Option 2: Supabase CLI**

```bash
supabase link --project-ref <ref>
supabase db push
```

### Applying Migrations (Local)

```bash
supabase start
supabase db reset  # Applies migrations + seed
```

## Seed Data

`supabase/seed.sql` contains minimal data for local development:

- Test user
- Capability tags
- Sample partner
- Sample product

Run after migrations:

```bash
# Local
supabase db reset  # Includes seed

# Cloud: Run seed.sql in SQL Editor after migrations
```

## Repairing Failed Migrations

If a migration fails partway (e.g., duplicate version error), the database may be in a partial state.

**For a fresh start on a linked remote project**:

1. Supabase Dashboard → SQL Editor
2. Run to clear migration history and drop objects (destructive—only for dev):

```sql
-- Clear migration tracking
TRUNCATE supabase_migrations.schema_migrations;

-- Drop extensions (optional, they'll be recreated)
DROP EXTENSION IF EXISTS postgis;
DROP EXTENSION IF EXISTS vector;
```

3. Then drop all created tables in reverse dependency order, or use Dashboard → Database → Reset (if available)
4. Re-run `supabase db push`

**Alternative**: Create a new Supabase project and link to it for a clean slate.

## Reset Procedures

### When to Reset

- Schema experiments
- Corrupted test data
- Fresh start for new developer

### Local Reset

```bash
supabase db reset
```

This drops all data, reapplies migrations, and runs seed.

### Cloud Reset

**Warning**: Cloud reset is destructive. Use a dedicated dev project.

1. Supabase Dashboard → Database → Reset database (if available)
2. Or: Drop and recreate via SQL (destructive)
3. Re-run migrations and seed

### Backup Before Reset

```bash
# Export schema + data (local)
supabase db dump -f backup.sql

# Cloud: Use Supabase Dashboard → Database → Backups
```

## Connection Pooling

For serverless (Azure Container Apps, Vercel):

- Use **Connection Pooler** URL: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
- Port `6543` = transaction mode (recommended)
- Port `5432` = session mode

Configure in app:

```python
# Use pooler URL for serverless
DATABASE_URL = os.getenv("SUPABASE_DB_URL")  # Pooler URL
```

## Naming Conventions

- Tables: `snake_case` (e.g., `order_items`, `time_chain_legs`)
- Columns: `snake_case` (e.g., `created_at`, `partner_id`)
- Indexes: `idx_{table}_{column(s)}` (e.g., `idx_products_partner_id`)

## Next Steps

- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [Authentication Setup](./AUTHENTICATION_SETUP.md)
