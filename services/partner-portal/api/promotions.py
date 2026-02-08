"""Promotions API."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    add_partner_promotion,
    delete_partner_promotion,
    get_partner_by_id,
    list_partner_promotions,
    update_partner_promotion,
)

router = APIRouter(prefix="/api/v1", tags=["Promotions"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class PromotionBody(BaseModel):
    name: str
    promo_type: str
    value: Optional[float] = None
    product_ids: Optional[List[str]] = None
    start_at: str
    end_at: str
    is_active: bool = True


@router.get("/partners/{partner_id}/promotions", response_class=HTMLResponse)
async def promotions_page(request: Request, partner_id: str):
    """Promotions page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    promotions = await list_partner_promotions(partner_id)
    return templates.TemplateResponse(
        "promotions.html",
        _base_context(request=request, partner=partner, promotions=promotions),
    )


@router.get("/partners/{partner_id}/promotions/list")
async def get_promotions(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List promotions (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    promotions = await list_partner_promotions(partner_id)
    return {"promotions": promotions}


class PromotionUpdateBody(BaseModel):
    name: Optional[str] = None
    promo_type: Optional[str] = None
    value: Optional[float] = None
    product_ids: Optional[List[str]] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("/partners/{partner_id}/promotions")
async def create_promotion(
    partner_id: str,
    body: PromotionBody,
    _: str = Depends(require_partner_admin),
):
    """Create promotion."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    promo = await add_partner_promotion(
        partner_id=partner_id,
        name=body.name,
        promo_type=body.promo_type,
        start_at=body.start_at,
        end_at=body.end_at,
        value=body.value,
        product_ids=body.product_ids,
        is_active=body.is_active,
    )
    if not promo:
        raise HTTPException(status_code=500, detail="Failed to create promotion")
    return {"promo_id": str(promo["id"]), "message": "Promotion created"}


@router.patch("/partners/{partner_id}/promotions/{promo_id}")
async def update_promotion(
    partner_id: str,
    promo_id: str,
    body: PromotionUpdateBody,
    _: str = Depends(require_partner_admin),
):
    """Update promotion."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No updates", "promo_id": promo_id}
    result = await update_partner_promotion(promo_id, partner_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"message": "Promotion updated"}


@router.delete("/partners/{partner_id}/promotions/{promo_id}")
async def delete_promotion(
    partner_id: str,
    promo_id: str,
    _: str = Depends(require_partner_admin),
):
    """Delete promotion."""
    ok = await delete_partner_promotion(promo_id, partner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"message": "Promotion deleted"}
