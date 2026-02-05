"""Platform-specific webhook push handlers."""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def send_chatgpt_webhook(thread_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Push update to ChatGPT thread.
    Uses CHATGPT_WEBHOOK_URL if configured; otherwise logs (placeholder).
    """
    if not settings.chatgpt_webhook_url:
        logger.info("ChatGPT webhook not configured (CHATGPT_WEBHOOK_URL). Would push: thread=%s", thread_id)
        return True  # Consider success for stub

    url = settings.chatgpt_webhook_url.rstrip("/") + f"/{thread_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=update_data)
            r.raise_for_status()
            return True
    except Exception as e:
        logger.warning("ChatGPT webhook failed: %s", e)
        raise


async def send_gemini_webhook(thread_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Push update to Gemini thread.
    Uses GEMINI_WEBHOOK_URL if configured; otherwise logs (placeholder).
    """
    if not settings.gemini_webhook_url:
        logger.info("Gemini webhook not configured (GEMINI_WEBHOOK_URL). Would push: thread=%s", thread_id)
        return True  # Consider success for stub

    url = settings.gemini_webhook_url.rstrip("/") + f"/{thread_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=update_data)
            r.raise_for_status()
            return True
    except Exception as e:
        logger.warning("Gemini webhook failed: %s", e)
        raise


async def send_whatsapp_webhook(phone_number: str, update_data: Dict[str, Any]) -> bool:
    """
    Push update to WhatsApp via Twilio.
    Uses TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.
    """
    if not settings.twilio_configured:
        logger.info("Twilio not configured. Would push to WhatsApp: %s", phone_number)
        return True  # Consider success for stub

    try:
        try:
            from twilio.rest import Client as TwilioClient
        except ImportError:
            logger.warning("twilio not installed. pip install twilio for WhatsApp push.")
            return True

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
    except Exception as e:
        logger.warning("WhatsApp webhook failed: %s", e)
        raise
