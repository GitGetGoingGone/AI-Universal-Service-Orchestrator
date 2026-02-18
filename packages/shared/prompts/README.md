# Shared Prompts – Single Source of Truth

Model interaction prompts live here as the **canonical source**. The database (`model_interaction_prompts`) is seeded from migrations. At runtime:

1. **DB first**: If `model_interaction_prompts` has a prompt for the interaction type, use it (admin-editable).
2. **File fallback**: If DB is empty or unavailable, code reads from these files.

## Files

| File | Used by | DB table |
|------|---------|----------|
| `intent_system.txt` | Intent service | `model_interaction_prompts` where `interaction_type = 'intent'` |

## Updating a Prompt

1. Edit the `.txt` file (e.g. `intent_system.txt`).
2. Run the sync script to generate migration SQL:
   ```bash
   python3 scripts/sync_prompts_to_migration.py
   ```
3. Create a new migration in `supabase/migrations/` with the output, or paste into an existing intent migration.
4. Run migrations to update the DB.

## Admin Overrides

Admins can edit prompts in **Platform Config → Model Interactions**. Those edits override the file. The file remains the source for:
- New deployments (migration seeds the DB)
- Fallback when DB is unavailable
- Version control and code review of prompt changes
