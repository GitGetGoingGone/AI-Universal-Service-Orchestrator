"""Partner onboarding and settings API."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from db import create_partner, get_partner_by_id, list_partners, set_partner_webhook, get_partner_webhook

router = APIRouter(prefix="/api/v1", tags=["Partners"])
_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class OnboardBody(BaseModel):
    """Partner onboarding request."""

    business_name: str
    contact_email: str
    business_type: Optional[str] = None
    contact_phone: Optional[str] = None


class WebhookBody(BaseModel):
    """Webhook URL configuration."""

    webhook_url: str


@router.get("/onboard", response_class=HTMLResponse)
async def onboard_page(request: Request):
    """Partner onboarding form page."""
    return templates.TemplateResponse("onboard.html", {"request": request})


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
    """Webhook settings page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    webhook_url = await get_partner_webhook(partner_id)
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "partner": partner, "webhook_url": webhook_url or ""},
    )


@router.post("/partners/{partner_id}/webhook")
async def update_webhook(partner_id: str, body: WebhookBody):
    """Set partner webhook URL for change requests."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    result = await set_partner_webhook(partner_id, body.webhook_url.strip())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save webhook URL")
    return {"message": "Webhook URL saved", "webhook_url": body.webhook_url}
