"""Configuration for orchestrator service."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


class Settings:
    """Orchestrator service settings."""

    intent_service_url: str = (
        get_env("INTENT_SERVICE_URL") or "http://localhost:8001"
    ).rstrip("/")
    discovery_service_url: str = (
        get_env("DISCOVERY_SERVICE_URL") or get_env("API_BASE_URL", "http://localhost:8000")
    ).rstrip("/")

    # Durable Orchestrator (Azure Functions)
    durable_orchestrator_url: str = (
        get_env("DURABLE_ORCHESTRATOR_URL") or "http://localhost:7071"
    ).rstrip("/")

    # Webhook service (for thread mapping, push updates)
    webhook_service_url: str = (
        get_env("WEBHOOK_SERVICE_URL") or "http://localhost:8003"
    ).rstrip("/")

    # Supabase (for Link Account: users, account_links)
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SERVICE_KEY") or get_env("SUPABASE_SECRET_KEY") or ""

    # Payment service (Module 15)
    payment_service_url: str = (
        get_env("PAYMENT_SERVICE_URL") or "http://localhost:8006"
    ).rstrip("/")

    # Hybrid Response (Module 13) - classify-support
    hybrid_response_service_url: str = (
        get_env("HYBRID_RESPONSE_SERVICE_URL") or "http://localhost:8010"
    ).rstrip("/")

    # Reverse Logistics (Module 17) - returns
    reverse_logistics_service_url: str = (
        get_env("REVERSE_LOGISTICS_SERVICE_URL") or "http://localhost:8011"
    ).rstrip("/")

    # Omnichannel Broker (Module 24)
    omnichannel_broker_url: str = (
        get_env("OMNICHANNEL_BROKER_URL") or "http://localhost:8004"
    ).rstrip("/")

    # Self-URL for internal API calls (e.g. standing intent from chat)
    orchestrator_base_url: str = (
        get_env("ORCHESTRATOR_SERVICE_URL") or "http://localhost:8002"
    ).rstrip("/")

    # Exclusive Gateway: public base URL for /.well-known/ucp (single USO manifest)
    gateway_public_url: str = (
        get_env("GATEWAY_PUBLIC_URL") or get_env("ORCHESTRATOR_PUBLIC_URL") or orchestrator_base_url
    ).rstrip("/")

    # Shared secret with Discovery for X-Gateway-Signature (when Discovery has GATEWAY_SIGNATURE_REQUIRED=true)
    gateway_internal_secret: str = get_env("GATEWAY_INTERNAL_SECRET") or ""

    # Agentic handoff (Clerk SSO 2.0 - optional)
    clerk_publishable_key: str = get_env("CLERK_PUBLISHABLE_KEY") or ""
    clerk_secret_key: str = get_env("CLERK_SECRET_KEY") or ""

    # Link Account - Google OAuth (verify id_token)
    google_oauth_client_id: str = get_env("GOOGLE_OAUTH_CLIENT_ID") or ""

    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")

    @property
    def agentic_handoff_configured(self) -> bool:
        return bool(self.clerk_publishable_key and self.clerk_secret_key)


settings = Settings()
