"""
Shared prompts - single source of truth for model interaction prompts.

These files are the canonical source. The database (model_interaction_prompts) is seeded
from migrations. When the DB has no prompt, code reads from these files.

To update: edit the .txt file, then run:
  python scripts/sync_prompts_to_migration.py
to generate SQL for the migration.
"""

import os

_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_intent_system_prompt() -> str:
    """Load intent system prompt from the canonical source file."""
    path = os.path.join(_PROMPTS_DIR, "intent_system.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


__all__ = ["get_intent_system_prompt"]
