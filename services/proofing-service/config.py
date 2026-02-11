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
    # DALL-E 3: OpenAI or Azure
    openai_api_key: str = get_env("OPENAI_API_KEY") or ""
    azure_openai_endpoint: str = get_env("AZURE_OPENAI_ENDPOINT") or ""
    azure_openai_api_key: str = get_env("AZURE_OPENAI_API_KEY") or ""
    azure_openai_deployment: str = get_env("DALLE_DEPLOYMENT") or get_env("AZURE_OPENAI_DALLE_DEPLOYMENT") or "dall-e-3"
    environment: str = get_env("ENVIRONMENT", "development")

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def dalle_configured(self) -> bool:
        return bool(self.openai_api_key or (self.azure_openai_endpoint and self.azure_openai_api_key))


settings = Settings()
