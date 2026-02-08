"""Configuration from environment variables."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.getenv(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean env var."""
    v = os.getenv(key, "").lower()
    return v in ("1", "true", "yes") if v else default


class Settings:
    """Partner Portal settings."""

    # Supabase
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SECRET_KEY") or get_env("SUPABASE_SERVICE_KEY") or ""

    # Service
    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")
    omnichannel_broker_url: str = (
        get_env("OMNICHANNEL_BROKER_URL") or "http://localhost:8004"
    ).rstrip("/")

    # Security
    require_api_key: bool = get_env_bool("REQUIRE_API_KEY", False)
    cors_origins: str = get_env("CORS_ORIGINS", "*")
    secure_headers: bool = get_env_bool("SECURE_HEADERS", True)

    # Auth (Clerk)
    clerk_secret_key: str = get_env("CLERK_SECRET_KEY") or ""
    clerk_publishable_key: str = get_env("CLERK_PUBLISHABLE_KEY") or ""
    auth_required: bool = get_env_bool("AUTH_REQUIRED", False)

    # UI (optional defaults; client localStorage overrides)
    default_theme: str = get_env("DEFAULT_THEME", "light")  # light | dark | ocean | forest | slate
    default_layout: str = get_env("DEFAULT_LAYOUT", "centered")  # centered | sidebar | top-nav | compact

    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_key)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"


settings = Settings()
