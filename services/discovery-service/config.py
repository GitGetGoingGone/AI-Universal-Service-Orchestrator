"""Configuration from environment variables."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (parent of services/discovery-service)
_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.getenv(key, default)


class Settings:
    """Discovery service settings."""

    # Supabase
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SECRET_KEY") or get_env("SUPABASE_SERVICE_KEY") or ""

    # Azure OpenAI (for embeddings - semantic search)
    azure_openai_endpoint: str = get_env("AZURE_OPENAI_ENDPOINT") or ""
    azure_openai_api_key: str = get_env("AZURE_OPENAI_API_KEY") or ""
    embedding_deployment: str = get_env("EMBEDDING_DEPLOYMENT") or get_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or "text-embedding-ada-002"

    # Service
    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")
    # Public base URL for UCP well-known and catalog (e.g. https://uso-discovery.onrender.com)
    discovery_public_url: str = get_env("DISCOVERY_PUBLIC_URL") or get_env("PUBLIC_URL") or ""
    # Platform/orchestrator base URL for manifest action endpoints (e.g. https://uso-orchestrator.onrender.com)
    platform_public_url: str = get_env("PLATFORM_PUBLIC_URL") or get_env("ORCHESTRATOR_PUBLIC_URL") or discovery_public_url or ""
    # Task Queue service URL (for Order → Task Queue integration)
    task_queue_service_url: str = get_env("TASK_QUEUE_SERVICE_URL") or ""
    # Portal/public URL for UCP continue_url (e.g. https://your-portal.vercel.app)
    portal_public_url: str = get_env("PORTAL_PUBLIC_URL") or get_env("DISCOVERY_PUBLIC_URL") or ""

    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_key)

    @property
    def embedding_configured(self) -> bool:
        """Check if embeddings (Azure OpenAI) are configured for semantic search."""
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


settings = Settings()
