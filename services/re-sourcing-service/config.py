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
    discovery_service_url: str = get_env("DISCOVERY_SERVICE_URL") or "http://localhost:8001"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


settings = Settings()
