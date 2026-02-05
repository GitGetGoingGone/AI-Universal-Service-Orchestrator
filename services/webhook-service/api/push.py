"""Webhook push API - receive push requests and route to platform handlers."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from handlers import send_chatgpt_webhook, send_gemini_webhook, send_whatsapp_webhook
from db import log_webhook_delivery, update_webhook_delivery

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

Platform = Literal["chatgpt", "gemini", "whatsapp"]


class PushPayload(BaseModel):
    """Payload for push update."""

    narrative: Optional[str] = None
    adaptive_card: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class PushRequest(BaseModel):
    """Request to push update to a chat thread."""

    platform: Platform = Field(..., description="Target platform")
    thread_id: str = Field(..., description="Platform-specific thread ID or phone number for WhatsApp")
    narrative: Optional[str] = Field(None, description="Human-readable status narrative")
    adaptive_card: Optional[Dict[str, Any]] = Field(None, description="Adaptive Card JSON")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


@router.post("/chat/{platform}/{thread_id}")
async def push_to_chat(
    request: Request,
    platform: Platform,
    thread_id: str,
    body: Optional[PushPayload] = Body(default=None),
):
    """
    Push update to a chat thread (ChatGPT, Gemini, or WhatsApp).

    Called by Durable Functions Status Narrator or other services.
    Logs delivery to webhook_deliveries table.
    """
    payload = body.model_dump() if body else {"narrative": "", "adaptive_card": None, "metadata": {}}

    # Build update data
    update_data = {
        "narrative": payload.get("narrative", ""),
        "adaptive_card": payload.get("adaptive_card"),
        "metadata": payload.get("metadata", {}),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Log delivery attempt
    delivery = log_webhook_delivery(platform, thread_id, update_data, status="pending")

    try:
        if platform == "chatgpt":
            await send_chatgpt_webhook(thread_id, update_data)
        elif platform == "gemini":
            await send_gemini_webhook(thread_id, update_data)
        elif platform == "whatsapp":
            await send_whatsapp_webhook(thread_id, update_data)  # thread_id = phone number
        else:
            raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

        if delivery and delivery.get("id"):
            update_webhook_delivery(delivery["id"], "delivered")

        return {
            "status": "delivered",
            "platform": platform,
            "thread_id": thread_id,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            },
        }
    except Exception as e:
        logger.exception("Webhook push failed: %s", e)
        if delivery and delivery.get("id"):
            update_webhook_delivery(delivery["id"], "failed", failure_reason=str(e))
        raise HTTPException(status_code=502, detail=f"Webhook delivery failed: {e}")


@router.post("/push")
async def push(
    request: Request,
    body: PushRequest,
):
    """
    Push update to chat (alternative endpoint with JSON body).
    """
    return await push_to_chat(
        request,
        body.platform,
        body.thread_id,
        body={
            "narrative": body.narrative,
            "adaptive_card": body.adaptive_card,
            "metadata": body.metadata,
        },
    )
