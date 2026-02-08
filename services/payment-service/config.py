"""Configuration from environment variables."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


class Settings:
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SECRET_KEY") or get_env("SUPABASE_SERVICE_KEY") or ""
    stripe_secret_key: str = get_env("STRIPE_SECRET_KEY") or ""
    stripe_webhook_secret: str = get_env("STRIPE_WEBHOOK_SECRET") or ""

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key)


settings = Settings()
