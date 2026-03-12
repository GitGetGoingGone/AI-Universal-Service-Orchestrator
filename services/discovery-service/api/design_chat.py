"""Design Chat Proxy - forward messages to partner design endpoint with headless context."""

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import (
    get_experience_session_by_thread,
    get_experience_session_legs,
    get_partner_design_chat_url,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Design Chat"])


@router.get("/design-chat/active")
async def design_chat_active(thread_id: str) -> Dict[str, Any]:
    """Check if thread has legs in in_customization (design chat active). Includes customization_partner choice when multiple partners."""
    session = await get_experience_session_by_thread(thread_id)
    if not session:
        return {"active": False}

    legs = await get_experience_session_legs(str(session["id"]))
    design_legs = [l for l in legs if l.get("status") == "in_customization"]
    if not design_legs:
        return {"active": False}

    leg = design_legs[0]
    partner_id = str(leg.get("customization_partner_id") or leg.get("partner_id", ""))
    design_url = await get_partner_design_chat_url(partner_id) if partner_id else None

    partners_in_legs = list({str(l.get("partner_id", "")) for l in design_legs if l.get("partner_id")})
    customization_choice = None
    if len(partners_in_legs) > 1 and not session.get("customization_partner_id"):
        customization_choice = {
            "message": "Choose who will handle your customization:",
            "partners": [{"partner_id": p} for p in partners_in_legs],
        }

    return {
        "active": True,
        "design_chat_url": design_url,
        "leg_id": leg.get("id"),
        "partner_id": partner_id,
        "customization_choice": customization_choice,
    }


class DesignChatProxyBody(BaseModel):
    """Request for design chat proxy."""

    thread_id: str = Field(..., description="Thread ID")
    user_message: str = Field(..., description="User's message to forward")
    order_id: Optional[str] = Field(None, description="USO order ID for context")


@router.post("/design-chat/proxy")
async def design_chat_proxy(body: DesignChatProxyBody) -> Dict[str, Any]:
    """
    Forward user message to partner's design_chat_url with headless context.
    Used when experience_session has legs in in_customization.
    Returns partner response or error.
    """
    session = await get_experience_session_by_thread(body.thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Experience session not found")

    legs = await get_experience_session_legs(str(session["id"]))
    design_legs = [l for l in legs if l.get("status") == "in_customization"]
    if not design_legs:
        raise HTTPException(
            status_code=400,
            detail="No legs in customization; design chat not active",
        )

    leg = design_legs[0]
    partner_id = str(leg.get("customization_partner_id") or leg.get("partner_id", ""))
    if not partner_id:
        raise HTTPException(status_code=400, detail="No partner for design leg")

    design_url = await get_partner_design_chat_url(partner_id)
    if not design_url:
        raise HTTPException(
            status_code=503,
            detail="Partner design chat endpoint not configured",
        )

    intent_summary = session.get("intent_summary") or "Experience order"
    payload = {
        "order_id": body.order_id,
        "external_order_id": leg.get("external_order_id"),
        "vendor_type": leg.get("vendor_type", "local"),
        "intent_summary": intent_summary,
        "user_message": body.user_message,
        "thread_id": body.thread_id,
        "leg_id": leg.get("id"),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(design_url.rstrip("/"), json=payload)
            r.raise_for_status()
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text}
            return {
                "response": data.get("response") or data.get("text") or data.get("message", str(data)),
                "partner_id": partner_id,
            }
    except httpx.HTTPStatusError as e:
        logger.warning("Design chat proxy HTTP error %s: %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(status_code=502, detail=f"Partner design chat error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Design chat proxy failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
