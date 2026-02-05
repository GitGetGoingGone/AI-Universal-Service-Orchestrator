"""Configuration for webhook push notification bridge."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


class Settings:
    """Webhook service settings."""

    # Supabase (for chat_thread_mappings, webhook_deliveries)
    supabase_url: str = get_env("SUPABASE_URL") or ""
    supabase_key: str = get_env("SUPABASE_SECRET_KEY") or get_env("SUPABASE_SERVICE_KEY") or ""

    # Platform webhook URLs (optional - for outbound push)
    # ChatGPT: OpenAI Assistants API or custom webhook
    # Gemini: Gemini API
    # WhatsApp: Twilio API
    chatgpt_webhook_url: str = get_env("CHATGPT_WEBHOOK_URL") or ""
    gemini_webhook_url: str = get_env("GEMINI_WEBHOOK_URL") or ""
    twilio_account_sid: str = get_env("TWILIO_ACCOUNT_SID") or ""
    twilio_auth_token: str = get_env("TWILIO_AUTH_TOKEN") or ""
    twilio_whatsapp_number: str = get_env("TWILIO_WHATSAPP_NUMBER") or ""

    environment: str = get_env("ENVIRONMENT", "development")
    log_level: str = get_env("LOG_LEVEL", "INFO")

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)


settings = Settings()
