"""Configuration for intent service (Module 4)."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.getenv(key, default)


class Settings:
    """Intent service settings."""

    # Supabase
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SECRET_KEY") or get_env("SUPABASE_SERVICE_KEY") or ""

    # Azure OpenAI
    azure_openai_endpoint: str = get_env("AZURE_OPENAI_ENDPOINT") or ""
    azure_openai_api_key: str = get_env("AZURE_OPENAI_API_KEY") or ""
    azure_openai_deployment: str = get_env("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4o"

    # Service
    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def azure_openai_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


settings = Settings()
