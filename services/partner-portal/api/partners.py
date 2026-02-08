"""Partner onboarding and settings API."""

from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, HttpUrl

from config import settings
from db import create_partner, get_partner_by_id, list_partners, set_partner_webhook, get_partner_webhook, set_partner_channel, get_partner_channel, get_pending_negotiations

router = APIRouter(prefix="/api/v1", tags=["Partners"])
_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class OnboardBody(BaseModel):
    """Partner onboarding request."""

    business_name: str
    contact_email: EmailStr
    business_type: Optional[str] = None
    contact_phone: Optional[str] = None


class WebhookBody(BaseModel):
    """Webhook URL configuration (legacy)."""

    webhook_url: str


class ChannelBody(BaseModel):
    """Communication channel configuration."""

    channel: str  # api | demo_chat | whatsapp
    channel_identifier: str = ""  # webhook URL, phone, or empty for demo_chat


class RespondBody(BaseModel):
    """Partner response to change request (for demo chat)."""

    negotiation_id: str
    response: str  # accept | reject
    rejection_reason: Optional[str] = None


def _base_context(**kwargs):
    """Base context for all templates (theme, layout)."""
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


@router.get("/onboard", response_class=HTMLResponse)
async def onboard_page(request: Request):
    """Partner onboarding form page."""
    return templates.TemplateResponse("onboard.html", _base_context(request=request))


@router.post("/onboard")
async def onboard_submit(body: OnboardBody):
    """Create new partner."""
    partner = await create_partner(
        business_name=body.business_name,
        contact_email=body.contact_email,
        business_type=body.business_type,
        contact_phone=body.contact_phone,
    )
    if not partner:
        raise HTTPException(status_code=500, detail="Failed to create partner")
    return {"partner_id": str(partner["id"]), "message": "Partner created successfully"}


@router.get("/partners/{partner_id}/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, partner_id: str):
    """Partner dashboard overview."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return templates.TemplateResponse(
        "dashboard.html",
        _base_context(request=request, partner=partner),
    )


@router.get("/partners")
async def get_partners():
    """List all partners."""
    partners = await list_partners()
    return {"partners": partners}


@router.get("/partners/{partner_id}")
async def get_partner(partner_id: str):
    """Get partner by ID."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


@router.get("/partners/{partner_id}/settings", response_class=HTMLResponse)
async def settings_page(request: Request, partner_id: str):
    """Communication channel settings page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    prefs = await get_partner_channel(partner_id)
    channel = prefs.get("channel", "api") if prefs else "api"
    channel_identifier = prefs.get("channel_identifier", "") if prefs else ""
    return templates.TemplateResponse(
        "settings.html",
        _base_context(
            request=request,
            partner=partner,
            channel=channel,
            channel_identifier=channel_identifier,
        ),
    )


@router.post("/partners/{partner_id}/webhook")
async def update_webhook(partner_id: str, body: WebhookBody):
    """Legacy: Set partner webhook URL (channel=api)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    result = await set_partner_webhook(partner_id, str(body.webhook_url).strip())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save webhook URL")
    return {"message": "Webhook URL saved", "webhook_url": body.webhook_url}


@router.post("/partners/{partner_id}/channel")
async def update_channel(partner_id: str, body: ChannelBody):
    """Set partner communication channel (api, demo_chat, whatsapp)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    if body.channel not in ("api", "demo_chat", "whatsapp", "chatgpt", "gemini"):
        raise HTTPException(status_code=400, detail="Invalid channel")
    if body.channel == "api" and not body.channel_identifier.strip():
        raise HTTPException(status_code=400, detail="Webhook URL required for API channel")
    if body.channel == "whatsapp" and not body.channel_identifier.strip():
        raise HTTPException(status_code=400, detail="Phone number required for WhatsApp")
    result = await set_partner_channel(
        partner_id, body.channel, body.channel_identifier.strip()
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save channel")
    return {"message": "Channel saved", "channel": body.channel}


@router.get("/partners/{partner_id}/demo-chat", response_class=HTMLResponse)
async def demo_chat_page(request: Request, partner_id: str):
    """Demo chat: view pending change requests and respond Accept/Reject."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    negotiations = await get_pending_negotiations(partner_id)
    return templates.TemplateResponse(
        "demo_chat.html",
        _base_context(
            request=request,
            partner=partner,
            negotiations=negotiations,
            broker_url=settings.omnichannel_broker_url,
        ),
    )


@router.get("/partners/{partner_id}/pending-negotiations")
async def pending_negotiations(partner_id: str):
    """API: list pending negotiations for partner (for demo chat polling)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    items = await get_pending_negotiations(partner_id)
    return {"negotiations": items}


@router.post("/partners/{partner_id}/respond")
async def respond_to_negotiation(partner_id: str, body: RespondBody):
    """Proxy partner response to Omnichannel Broker (for demo chat)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    url = f"{settings.omnichannel_broker_url}/webhooks/partner"
    payload: Dict[str, Any] = {
        "negotiation_id": body.negotiation_id,
        "response": body.response,
    }
    if body.rejection_reason:
        payload["rejection_reason"] = body.rejection_reason
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
