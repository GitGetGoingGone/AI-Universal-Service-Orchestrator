"""Earnings and payouts API."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from auth import require_partner_admin
from config import settings
from db import (
    get_earnings_summary,
    get_partner_by_id,
    list_commission_breaks,
    list_payouts,
)

router = APIRouter(prefix="/api/v1", tags=["Earnings"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


@router.get("/partners/{partner_id}/earnings", response_class=HTMLResponse)
async def earnings_page(request: Request, partner_id: str):
    """Earnings dashboard page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    summary = await get_earnings_summary(partner_id)
    payouts = await list_payouts(partner_id)
    commissions = await list_commission_breaks(partner_id, limit=20)
    return templates.TemplateResponse(
        "earnings.html",
        _base_context(
            request=request,
            partner=partner,
            summary=summary,
            payouts=payouts,
            commissions=commissions,
        ),
    )


@router.get("/partners/{partner_id}/earnings/summary")
async def get_earnings(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Earnings summary (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    summary = await get_earnings_summary(partner_id)
    return {"summary": summary}


@router.get("/partners/{partner_id}/payouts")
async def get_payouts(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Payout history (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    payouts = await list_payouts(partner_id)
    return {"payouts": payouts}


@router.get("/partners/{partner_id}/payouts/{payout_id}/invoice")
async def get_payout_invoice(
    partner_id: str,
    payout_id: str,
    _: str = Depends(require_partner_admin),
):
    """Download payout invoice (placeholder - returns JSON for now)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    payouts = await list_payouts(partner_id)
    payout = next((p for p in payouts if str(p.get("id")) == payout_id), None)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return {"payout": payout, "message": "PDF invoice generation not yet implemented"}
