"""Ratings and reviews API."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    get_partner_by_id,
    get_partner_rating,
    list_partner_reviews,
    update_order_review_response,
)

router = APIRouter(prefix="/api/v1", tags=["Ratings"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class RespondBody(BaseModel):
    partner_response: str


@router.get("/partners/{partner_id}/ratings", response_class=HTMLResponse)
async def ratings_page(request: Request, partner_id: str):
    """Ratings dashboard page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    rating = await get_partner_rating(partner_id)
    reviews = await list_partner_reviews(partner_id)
    return templates.TemplateResponse(
        "ratings.html",
        _base_context(request=request, partner=partner, rating=rating, reviews=reviews),
    )


@router.get("/partners/{partner_id}/ratings/summary")
async def get_ratings(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Rating summary (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    rating = await get_partner_rating(partner_id)
    return {"rating": rating}


@router.get("/partners/{partner_id}/reviews")
async def get_reviews(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List reviews (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    reviews = await list_partner_reviews(partner_id)
    return {"reviews": reviews}


@router.post("/partners/{partner_id}/reviews/{review_id}/respond")
async def respond_to_review(
    partner_id: str,
    review_id: str,
    body: RespondBody,
    _: str = Depends(require_partner_admin),
):
    """Respond to review."""
    result = await update_order_review_response(
        review_id, partner_id, body.partner_response
    )
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Response added"}
