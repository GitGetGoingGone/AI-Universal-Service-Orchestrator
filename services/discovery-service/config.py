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

    # Service
    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")
    # Public base URL for UCP well-known and catalog (e.g. https://uso-discovery.onrender.com)
    discovery_public_url: str = get_env("DISCOVERY_PUBLIC_URL") or get_env("PUBLIC_URL") or ""
    # Platform/orchestrator base URL for manifest action endpoints (e.g. https://uso-orchestrator.onrender.com)
    platform_public_url: str = get_env("PLATFORM_PUBLIC_URL") or get_env("ORCHESTRATOR_PUBLIC_URL") or discovery_public_url or ""
    # Task Queue service URL (for Order → Task Queue integration)
    task_queue_service_url: str = get_env("TASK_QUEUE_SERVICE_URL") or ""
    # Webhook service URL (for inventory webhook push to chat threads)
    webhook_service_url: str = (get_env("WEBHOOK_SERVICE_URL") or "http://localhost:8003").rstrip("/")
    # Portal/public URL for UCP continue_url (e.g. https://your-portal.vercel.app)
    portal_public_url: str = get_env("PORTAL_PUBLIC_URL") or get_env("DISCOVERY_PUBLIC_URL") or ""

    # Exclusive Gateway: mask product ids returned to clients (uso_*); mapping stored for checkout
    id_masking_enabled: bool = (get_env("ID_MASKING_ENABLED") or "false").strip().lower() == "true"

    # Exclusive Gateway: require X-Gateway-Signature on /api/* when True (shared secret with Orchestrator)
    gateway_signature_required: bool = (get_env("GATEWAY_SIGNATURE_REQUIRED") or "false").strip().lower() == "true"
    gateway_internal_secret: str = get_env("GATEWAY_INTERNAL_SECRET") or ""

    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_key)


settings = Settings()
