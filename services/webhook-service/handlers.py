"""Platform-specific webhook push handlers. No stubs: 503 when not configured."""

import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from config import settings

logger = logging.getLogger(__name__)


def _require_chatgpt_configured() -> None:
    if not settings.chatgpt_webhook_url:
        raise HTTPException(
            status_code=503,
            detail="ChatGPT webhook not configured. Set CHATGPT_WEBHOOK_URL for push to ChatGPT threads.",
        )


def _require_gemini_configured() -> None:
    if not settings.gemini_webhook_url:
        raise HTTPException(
            status_code=503,
            detail="Gemini webhook not configured. Set GEMINI_WEBHOOK_URL for push to Gemini threads.",
        )


def _require_twilio_configured() -> None:
    if not settings.twilio_configured:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp push not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.",
        )


async def send_chatgpt_webhook(thread_id: str, update_data: Dict[str, Any]) -> bool:
    """Push update to ChatGPT thread. Raises 503 if CHATGPT_WEBHOOK_URL not set."""
    _require_chatgpt_configured()
    url = settings.chatgpt_webhook_url.rstrip("/") + f"/{thread_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=update_data)
        r.raise_for_status()
    return True


async def send_gemini_webhook(thread_id: str, update_data: Dict[str, Any]) -> bool:
    """Push update to Gemini thread. Raises 503 if GEMINI_WEBHOOK_URL not set."""
    _require_gemini_configured()
    url = settings.gemini_webhook_url.rstrip("/") + f"/{thread_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=update_data)
        r.raise_for_status()
    return True


async def send_whatsapp_webhook(phone_number: str, update_data: Dict[str, Any]) -> bool:
    """Push update to WhatsApp via Twilio. Raises 503 if Twilio not configured."""
    _require_twilio_configured()
    try:
        from twilio.rest import Client as TwilioClient
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail="Twilio SDK not installed. pip install twilio for WhatsApp push.",
        ) from e
    client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    message_body = update_data.get("narrative", update_data.get("text", str(update_data)))
    from_num = settings.twilio_whatsapp_number or "+14155238886"
    if not from_num.startswith("whatsapp:"):
        from_num = f"whatsapp:{from_num}"
    client.messages.create(
        body=message_body[:1600],
        from_=from_num,
        to=f"whatsapp:{phone_number}",
    )
    return True
