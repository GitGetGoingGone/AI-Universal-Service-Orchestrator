"""Product registration API."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from db import create_product, list_products, get_partner_by_id

router = APIRouter(prefix="/api/v1", tags=["Products"])
_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class ProductBody(BaseModel):
    """Product registration request."""

    name: str
    price: float
    description: Optional[str] = None
    currency: str = "USD"
    capabilities: Optional[List[str]] = None


@router.get("/partners/{partner_id}/products", response_class=HTMLResponse)
async def products_page(request: Request, partner_id: str):
    """Product registration page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    products = await list_products(partner_id)
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "partner": partner, "products": products},
    )


@router.get("/partners/{partner_id}/products/list")
async def get_partner_products(partner_id: str):
    """List products for a partner (JSON API)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    products = await list_products(partner_id)
    return {"products": products}


@router.post("/partners/{partner_id}/products")
async def add_product(partner_id: str, body: ProductBody):
    """Register a new product for a partner."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    product = await create_product(
        partner_id=partner_id,
        name=body.name,
        price=body.price,
        description=body.description,
        currency=body.currency,
        capabilities=body.capabilities,
    )
    if not product:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return {"product_id": str(product["id"]), "message": "Product created successfully"}
