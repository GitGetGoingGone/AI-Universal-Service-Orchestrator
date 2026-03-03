# Supabase migrations

Migrations run in **timestamp order** (filename prefix `YYYYMMDDHHMMSS`).  
`supabase db push` only runs migrations that are **not** already recorded as applied on the remote database.

## Why some migrations don’t show when running `supabase db push`

If **`20240128000008_partner_portal_production.sql`** and **`20240129000004_pillar1_4_schema.sql`** (or any other file) do **not** appear when you run `supabase db push`, it usually means:

- They are **already applied**: the remote DB’s migration history (e.g. `supabase_migrations.schema_migrations`) already contains these migration versions, so the CLI skips them. No need to run them again.

So in normal use you do **not** need to run those files manually. They either ran in a previous push or when the project was first set up.

## When to run migrations manually

Run SQL manually only if:

1. You are **onboarding a new database** that was created without the CLI (e.g. restored from backup, or created in the Dashboard) and the migration history is missing or different.
2. The CLI reports **migration history conflicts** and you’ve decided to fix the DB state by hand and then repair history.

### Steps if you must run them manually

1. **Run the SQL**  
   In Supabase: **SQL Editor** → paste the contents of the migration file → Run.  
   Or with `psql`:  
   `psql "$DATABASE_URL" -f supabase/migrations/20240128000008_partner_portal_production.sql`  
   then the same for `20240129000004_pillar1_4_schema.sql`.

2. **Tell the CLI they are applied** (so `db push` won’t try to run them again):
   ```bash
   supabase migration repair --status applied 20240128000008
   supabase migration repair --status applied 20240129000004
   ```

3. Run **`supabase db push`** again; any remaining unapplied migrations will run as usual.

## Check what’s applied

- **CLI**: `supabase migration list` (or your CLI’s equivalent) to see which migrations are applied vs pending.
- **Database**: query the migration history table (e.g. `supabase_migrations.schema_migrations`) on the remote DB to see recorded migration versions.

## Order and dependencies

- **20240128000008_partner_portal_production.sql** depends on: `core_and_scout`, `orders_and_payments`, `timechain_recovery_support` (run after the corresponding 20240128* migrations).
- **20240129000004_pillar1_4_schema.sql** depends on: `platform_config`, `core_and_scout` (run after those; `partner_portal_production` creates tables this one extends).

Run migrations in timestamp order; the CLI does this by default.
