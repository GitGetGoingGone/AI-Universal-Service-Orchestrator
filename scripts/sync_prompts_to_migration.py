#!/usr/bin/env python3
"""
Sync prompts from single source to migration SQL.

Single source: packages/shared/prompts/intent_system.txt
Run this script when you change the intent prompt, then add a new migration
or update the existing intent migration with the output.

Usage:
  python scripts/sync_prompts_to_migration.py
  # Copies output to clipboard or prints; paste into a new migration file.
"""
import os
import sys

# Project root (parent of scripts/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROMPTS_DIR = os.path.join(ROOT, "packages", "shared", "prompts")
INTENT_FILE = os.path.join(PROMPTS_DIR, "intent_system.txt")


def escape_sql_string(s: str) -> str:
    """Escape single quotes for SQL."""
    return s.replace("'", "''")


def main() -> None:
    if not os.path.exists(INTENT_FILE):
        print(f"Error: {INTENT_FILE} not found", file=sys.stderr)
        sys.exit(1)

    with open(INTENT_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print("Error: intent_system.txt is empty", file=sys.stderr)
        sys.exit(1)

    escaped = escape_sql_string(content)

    sql = f"""-- Migration: Update intent prompt from single source
-- Source: packages/shared/prompts/intent_system.txt
-- Run: python scripts/sync_prompts_to_migration.py to regenerate

BEGIN;

UPDATE model_interaction_prompts
SET
  system_prompt = '{escaped}',
  updated_at = NOW()
WHERE interaction_type = 'intent';

COMMIT;
"""

    print(sql)


if __name__ == "__main__":
    main()
