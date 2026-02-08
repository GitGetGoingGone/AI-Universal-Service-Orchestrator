"""Availability integrations API - webhook, API poll, OAuth sync."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    add_availability_integration,
    get_partner_by_id,
    list_availability_integrations,
)

router = APIRouter(prefix="/api/v1", tags=["Availability Integrations"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class IntegrationBody(BaseModel):
    integration_type: str
    provider: Optional[str] = None
    product_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/partners/{partner_id}/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request, partner_id: str):
    """Availability integrations page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    integrations = await list_availability_integrations(partner_id)
    return templates.TemplateResponse(
        "integrations.html",
        _base_context(request=request, partner=partner, integrations=integrations),
    )


@router.get("/partners/{partner_id}/availability-integrations")
async def list_integrations(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List availability integrations (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    integrations = await list_availability_integrations(partner_id)
    return {"integrations": integrations}


@router.post("/partners/{partner_id}/availability-integrations")
async def add_integration(
    partner_id: str,
    body: IntegrationBody,
    _: str = Depends(require_partner_admin),
):
    """Add availability integration."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    integration = await add_availability_integration(
        partner_id=partner_id,
        integration_type=body.integration_type,
        provider=body.provider,
        product_id=body.product_id,
        config=body.config or {},
    )
    if not integration:
        raise HTTPException(status_code=500, detail="Failed to add integration")
    return {"integration_id": str(integration["id"]), "message": "Integration added"}
