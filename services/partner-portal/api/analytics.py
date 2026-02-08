"""Analytics API - sales, peak hours, popular items."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from auth import require_partner_admin
from config import settings
from db import get_partner_by_id, list_commission_breaks, list_partner_orders

router = APIRouter(prefix="/api/v1", tags=["Analytics"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


@router.get("/partners/{partner_id}/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, partner_id: str):
    """Analytics dashboard page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    orders = await list_partner_orders(partner_id, statuses=["pending", "accepted", "preparing", "ready", "fulfilled"], limit=100)
    commissions = await list_commission_breaks(partner_id, limit=100)
    total_sales = sum(c.get("gross_cents", 0) for c in commissions)
    return templates.TemplateResponse(
        "analytics.html",
        _base_context(
            request=request,
            partner=partner,
            orders=orders,
            commissions=commissions,
            total_sales_cents=total_sales,
        ),
    )


@router.get("/partners/{partner_id}/analytics/summary")
async def get_analytics(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Analytics summary (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    commissions = await list_commission_breaks(partner_id, limit=500)
    total_sales = sum(c.get("gross_cents", 0) for c in commissions)
    return {"total_sales_cents": total_sales, "order_count": len(commissions)}


@router.get("/partners/{partner_id}/analytics/export")
async def export_analytics(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """CSV export (placeholder)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    commissions = await list_commission_breaks(partner_id, limit=1000)
    lines = ["order_id,gross_cents,commission_cents,net_cents"]
    for c in commissions:
        lines.append(f"{c.get('order_id','')},{c.get('gross_cents',0)},{c.get('commission_cents',0)},{c.get('net_cents',0)}")
    return {"csv": "\n".join(lines), "message": "Use /analytics/export.csv for download"}
