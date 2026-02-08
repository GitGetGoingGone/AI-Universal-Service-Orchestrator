"""Operations API - venues, service areas, pause/capacity."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import get_partner_by_id, list_partner_venues

router = APIRouter(prefix="/api/v1", tags=["Operations"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class StatusBody(BaseModel):
    is_accepting_orders: Optional[bool] = None
    capacity_limit: Optional[int] = None


@router.get("/partners/{partner_id}/venues", response_class=HTMLResponse)
async def venues_page(request: Request, partner_id: str):
    """Venues and service areas page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    venues = await list_partner_venues(partner_id)
    return templates.TemplateResponse(
        "venues.html",
        _base_context(request=request, partner=partner, venues=venues),
    )


@router.get("/partners/{partner_id}/venues/list")
async def get_venues(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List venues (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    venues = await list_partner_venues(partner_id)
    return {"venues": venues}


@router.patch("/partners/{partner_id}/status")
async def update_status(
    partner_id: str,
    body: StatusBody,
    _: str = Depends(require_partner_admin),
):
    """Update pause orders, capacity limit."""
    from db import update_partner

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No updates"}
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    result = await update_partner(partner_id, **updates)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update")
    return {"message": "Status updated"}


@router.get("/partners/{partner_id}/service-areas")
async def get_service_areas(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List service areas (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"service_areas": []}
